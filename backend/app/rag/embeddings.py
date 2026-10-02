"""Local embeddings (llm-integration.md §6.3). No embedding API calls, ever.

- FastEmbedEmbedder: BAAI/bge-small-en-v1.5 via fastembed (ONNX Runtime, no PyTorch), 384-d,
  lazy-loaded on first use, query LRU (512) plus an optional Redis cache `emb:q:{sha1}` (7 d).
- HashEmbedder: deterministic bag-of-words hashing, for tests and EMBEDDINGS_RUNTIME=off dev.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import math
import re
import threading
import time
from collections import OrderedDict
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Protocol

log = logging.getLogger("nakshion.rag.embeddings")

DIM = 384

# Set to True (in the caller's task context) when the last embed_queries() call degraded because the local model
# was still loading, failed to load, or exceeded its time budget. The retriever then runs keys + full-text only.
EMBED_DEGRADED: ContextVar[bool] = ContextVar("embed_degraded", default=False)


class Embedder(Protocol):
    model_name: str
    dim: int

    async def embed_documents(self, texts: list[str]) -> list[list[float]]: ...
    async def embed_query(self, text: str) -> list[float]: ...
    async def embed_queries(self, texts: list[str]) -> list[list[float]]: ...


class _LRU:
    def __init__(self, size: int = 512) -> None:
        self.size = size
        self.d: OrderedDict[str, list[float]] = OrderedDict()

    def get(self, k: str) -> list[float] | None:
        v = self.d.get(k)
        if v is not None:
            self.d.move_to_end(k)
        return v

    def put(self, k: str, v: list[float]) -> None:
        self.d[k] = v
        self.d.move_to_end(k)
        while len(self.d) > self.size:
            self.d.popitem(last=False)


@dataclass(frozen=True)
class EmbedderSpec:
    name: str                      # recorded in kb_chunks.embedding_model (identifies model AND prefix scheme)
    hf: str                        # fastembed built-in id, or HF repo for a custom ONNX model
    dim: int = 384
    doc_prefix: str = ""
    query_prefix: str = ""
    custom_file: str | None = None  # set => registered as a custom fastembed model (mean pooling)
    pooling: str = "MEAN"
    multilingual: bool = False


SPECS: dict[str, EmbedderSpec] = {
    "bge-small": EmbedderSpec("BAAI/bge-small-en-v1.5", "BAAI/bge-small-en-v1.5"),
    "bge-small-q": EmbedderSpec("BAAI/bge-small-en-v1.5+qi", "BAAI/bge-small-en-v1.5",
                                query_prefix="Represent this sentence for searching relevant passages: "),
    "minilm-ml": EmbedderSpec("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                              "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", multilingual=True),
    "e5-small": EmbedderSpec("intfloat/multilingual-e5-small@int8", "Xenova/multilingual-e5-small",
                             doc_prefix="passage: ", query_prefix="query: ",
                             custom_file="onnx/model_quantized.onnx", multilingual=True),
    # 384-d candidates measured for the 512 MB question (docs/rag-runbook.md section 2c)
    "bge-small-fp32": EmbedderSpec("BAAI/bge-small-en-v1.5@fp32", "Xenova/bge-small-en-v1.5",
                                   custom_file="onnx/model.onnx", pooling="CLS"),
    "arctic-xs": EmbedderSpec("snowflake/snowflake-arctic-embed-xs", "snowflake/snowflake-arctic-embed-xs"),
    "minilm-l6": EmbedderSpec("sentence-transformers/all-MiniLM-L6-v2", "sentence-transformers/all-MiniLM-L6-v2"),
    "minilm-l6-q": EmbedderSpec("sentence-transformers/all-MiniLM-L6-v2@int8", "Xenova/all-MiniLM-L6-v2",
                                custom_file="onnx/model_quantized.onnx"),
    "e5-small-fp32": EmbedderSpec("intfloat/multilingual-e5-small", "intfloat/multilingual-e5-small",
                                  doc_prefix="passage: ", query_prefix="query: ",
                                  custom_file="onnx/model.onnx", multilingual=True),
}


class FastEmbedEmbedder:
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", *, cache_dir: str | None = None,
                 redis: Any = None, threads: int | None = 1, spec: EmbedderSpec | None = None,
                 arena: bool = False, timeout_s: float | None = None) -> None:
        # EMBEDDING_MODEL may be a SPECS key ("minilm-l6-q") or the full recorded model name
        self.spec = spec or SPECS.get(model_name) or next((s for s in SPECS.values() if s.name == model_name),
                                                           EmbedderSpec(model_name, model_name))
        self.model_name = self.spec.name
        self.dim = self.spec.dim
        self._cache_dir = cache_dir
        self._threads = threads
        self._arena = arena        # ONNX CPU memory arena: off (it keeps freed buffers; see runbook 2c)
        self._model = None
        self._lock = threading.Lock()
        self._lru = _LRU(512)
        self._redis = redis
        self._timeout_s = timeout_s            # None -> settings.embed_query_timeout_s (0.4 s); 0 -> no limit
        self._load_task: asyncio.Future | None = None
        self._cooldown_until = 0.0             # monotonic; while in the future the model is skipped
        self._consecutive_timeouts = 0
        self._sem = asyncio.Semaphore(2)       # at most two inferences queued behind the one ONNX thread
        self.stats = {"calls": 0, "degraded": 0, "timeouts": 0, "load_failures": 0, "load_s": None}

    def _load(self):
        with self._lock:
            if self._model is None:
                from fastembed import TextEmbedding

                sp = self.spec
                log.info("loading embedding model %s", sp.name)
                if sp.custom_file:
                    from fastembed.common.model_description import ModelSource, PoolingType

                    try:
                        TextEmbedding.add_custom_model(
                            sp.hf, pooling=PoolingType[sp.pooling], normalization=True,
                            sources=ModelSource(hf=sp.hf), dim=sp.dim, model_file=sp.custom_file)
                    except ValueError:
                        pass  # already registered in this process
                self._model = TextEmbedding(sp.hf, cache_dir=self._cache_dir, threads=self._threads,
                                          enable_cpu_mem_arena=self._arena)
        return self._model

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        pre = self.spec.doc_prefix

        def run():
            return [v.tolist() for v in self._load().embed([pre + t for t in texts], batch_size=32)]

        return await asyncio.to_thread(run)

    async def embed_query(self, text: str) -> list[float]:
        out = await self.embed_queries([text])
        if not out:
            raise RuntimeError("embedding unavailable (degraded: loading, failed or over budget)")
        return out[0]

    def _budget(self) -> float | None:
        t = self._timeout_s
        if t is None:
            try:
                from app.llm.config import LLMSettings

                t = LLMSettings().embed_query_timeout_s
            except Exception:  # noqa: BLE001 - settings must never break retrieval
                t = 0.4
        return t or None

    @property
    def loaded(self) -> bool:
        return self._model is not None

    def disable(self, reason: str, seconds: float = 3600.0) -> None:
        """Skip the model for a while (for example the index was built with another model)."""
        log.warning("embedding model disabled: %s", reason)
        self._cooldown_until = time.monotonic() + seconds

    def _timed_load(self) -> None:
        t0 = time.perf_counter()
        self._load()
        self.stats["load_s"] = round(time.perf_counter() - t0, 2)

    async def _ready(self, budget: float | None) -> bool:
        """True when the model is loaded. The load runs once in a worker thread and is never awaited past the
        budget, so a cold start (seconds on 0.1 vCPU) degrades the first requests instead of stalling them."""
        if self._model is not None:
            return True
        if self._load_task is None:
            self._load_task = asyncio.ensure_future(asyncio.to_thread(self._timed_load))
        try:
            await asyncio.wait_for(asyncio.shield(self._load_task), budget)
            return True
        except asyncio.TimeoutError:
            return False
        except Exception as exc:  # noqa: BLE001 - missing file, corrupt model, out of memory
            self.stats["load_failures"] += 1
            self._load_task = None
            self._cooldown_until = time.monotonic() + 300.0
            log.error("embedding model failed to load (%s); retrieval runs on keys + full-text for 5 min",
                      type(exc).__name__)
            return False

    async def _infer(self, texts: list[str]) -> list[list[float]] | None:
        """Embed within the time budget. None means 'degrade this request'; the caller never sees an exception."""
        if time.monotonic() < self._cooldown_until:
            return None
        budget = self._budget()
        t0 = time.monotonic()
        if not await self._ready(budget):
            return None
        left = None if budget is None else max(0.05, budget - (time.monotonic() - t0))
        pre = self.spec.query_prefix

        def run():
            return [v.tolist() for v in self._load().embed([pre + t for t in texts])]

        async def guarded():
            async with self._sem:
                return await asyncio.to_thread(run)

        try:
            vecs = await asyncio.wait_for(guarded(), left)
            self._consecutive_timeouts = 0
            return vecs
        except asyncio.TimeoutError:
            self.stats["timeouts"] += 1
            self._consecutive_timeouts += 1
            if self._consecutive_timeouts >= 3:       # CPU starved: stop queueing work for a short while
                self._cooldown_until = time.monotonic() + 30.0
                self._consecutive_timeouts = 0
            return None
        except Exception as exc:  # noqa: BLE001
            log.warning("embedding inference failed (%s)", type(exc).__name__)
            self._cooldown_until = time.monotonic() + 30.0
            return None

    async def embed_queries(self, texts: list[str]) -> list[list[float]]:
        """Batch of queries in one model call (cache-aware). Order preserved.

        Fallback contract: when the model is still loading, failed to load, or misses its per-call budget
        (EMBED_QUERY_TIMEOUT_S, default 0.4 s) this returns [] and sets EMBED_DEGRADED instead of raising. The
        retriever zips the result against its plan, so the request proceeds on pre-embedded keys + full-text.
        A fully cached batch is always served."""
        self.stats["calls"] += 1
        EMBED_DEGRADED.set(False)
        keys = [hashlib.sha1(f"{self.model_name}\x00{t}".encode()).hexdigest() for t in texts]
        out: list[list[float] | None] = [self._lru.get(k) for k in keys]
        miss = [i for i, v in enumerate(out) if v is None]
        if miss and self._redis is not None:
            try:
                raws = await self._redis.mget([f"emb:q:{keys[i]}" for i in miss])
                for i, raw in zip(miss, raws):
                    if raw:
                        out[i] = json.loads(raw)
                        self._lru.put(keys[i], out[i])
            except Exception:  # noqa: BLE001 - cache is best effort
                log.warning("embedding cache read failed")
            miss = [i for i, v in enumerate(out) if v is None]
        if miss:
            vecs = await self._infer([texts[i] for i in miss])
            if vecs is None:
                self.stats["degraded"] += 1
                EMBED_DEGRADED.set(True)
                return []
            for i, vec in zip(miss, vecs):
                out[i] = vec
                self._lru.put(keys[i], vec)
                if self._redis is not None:
                    try:
                        await self._redis.set(f"emb:q:{keys[i]}", json.dumps(vec), ex=7 * 86400)
                    except Exception:  # noqa: BLE001
                        log.warning("embedding cache write failed")
        return out  # type: ignore[return-value]


def make_embedder(name: str, **kw) -> "Embedder":
    """Offline factory (ingest, evals): no per-query time limit, because a degraded [] would silently drop vectors.
    The web process builds FastEmbedEmbedder directly (retriever.build_default) and gets the 0.4 s budget."""
    if name == "hash":
        return HashEmbedder()
    kw.setdefault("timeout_s", 0)
    return FastEmbedEmbedder(spec=SPECS[name], **kw)


_WORD = re.compile(r"[a-z0-9]+")


class HashEmbedder:
    """Deterministic, dependency-free. Similarity = shared (stemmed-ish) words. Tests only."""

    dim = DIM

    def __init__(self, model_name: str = "hash-bow-384") -> None:
        self.model_name = model_name

    def _vec(self, text: str) -> list[float]:
        v = [0.0] * self.dim
        for w in _WORD.findall(text.lower()):
            w = w[:6]
            h = int(hashlib.md5(w.encode()).hexdigest(), 16)
            v[h % self.dim] += 1.0
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v]

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    async def embed_query(self, text: str) -> list[float]:
        return self._vec(text)

    async def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)
