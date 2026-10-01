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
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Protocol

log = logging.getLogger("nakshion.rag.embeddings")

DIM = 384


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
    "e5-small-fp32": EmbedderSpec("intfloat/multilingual-e5-small", "intfloat/multilingual-e5-small",
                                  doc_prefix="passage: ", query_prefix="query: ",
                                  custom_file="onnx/model.onnx", multilingual=True),
}


class FastEmbedEmbedder:
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5", *, cache_dir: str | None = None,
                 redis: Any = None, threads: int | None = 1, spec: EmbedderSpec | None = None) -> None:
        self.spec = spec or next((s for s in SPECS.values() if s.name == model_name),
                                 EmbedderSpec(model_name, model_name))
        self.model_name = self.spec.name
        self.dim = self.spec.dim
        self._cache_dir = cache_dir
        self._threads = threads
        self._model = None
        self._lock = threading.Lock()
        self._lru = _LRU(512)
        self._redis = redis

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
                self._model = TextEmbedding(sp.hf, cache_dir=self._cache_dir, threads=self._threads)
        return self._model

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        pre = self.spec.doc_prefix

        def run():
            return [v.tolist() for v in self._load().embed([pre + t for t in texts], batch_size=32)]

        return await asyncio.to_thread(run)

    async def embed_query(self, text: str) -> list[float]:
        return (await self.embed_queries([text]))[0]

    async def embed_queries(self, texts: list[str]) -> list[list[float]]:
        """Batch of queries in one model call (cache-aware). Order preserved."""
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
            pre = self.spec.query_prefix

            def run():
                return [v.tolist() for v in self._load().embed([pre + texts[i] for i in miss])]

            vecs = await asyncio.to_thread(run)
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
    if name == "hash":
        return HashEmbedder()
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
