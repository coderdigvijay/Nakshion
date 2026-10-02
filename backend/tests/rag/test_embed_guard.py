"""Local query-embedding guard: a model that is slow to load, fails to load, or is slow to answer must degrade the
request to keys + full-text (empty vector list + EMBED_DEGRADED), never raise. Fake ONNX model, no network."""

from __future__ import annotations

import asyncio
import time

import numpy as np

from app.rag.chunking import chunk_markdown
from app.rag.embeddings import EMBED_DEGRADED, SPECS, FastEmbedEmbedder, HashEmbedder, make_embedder
from app.rag.ingest import run_ingest
from app.rag.retriever import Retriever
from app.rag.store import MemoryStore


class FakeModel:
    def __init__(self, delay: float = 0.0):
        self.delay = delay

    def embed(self, texts, **_):
        time.sleep(self.delay)
        for t in texts:
            v = np.zeros(384, dtype=np.float32)
            v[len(t) % 384] = 1.0
            yield v


def embedder(*, load_s=0.0, infer_s=0.0, fail=False, timeout_s=0.2) -> FastEmbedEmbedder:
    e = FastEmbedEmbedder(spec=SPECS["minilm-l6-q"], timeout_s=timeout_s)

    def load():
        if e._model is not None:      # the real _load is idempotent
            return e._model
        time.sleep(load_s)
        if fail:
            raise OSError("model file missing")
        e._model = FakeModel(infer_s)
        return e._model

    e._load = load  # type: ignore[method-assign]
    return e


async def test_fast_model_returns_vectors_and_is_not_degraded():
    e = embedder()
    out = await e.embed_queries(["saturn return", "moon sign"])
    assert len(out) == 2 and len(out[0]) == 384 and not EMBED_DEGRADED.get()
    assert e.loaded and e.stats["degraded"] == 0


async def test_cold_load_over_budget_degrades_then_recovers():
    e = embedder(load_s=0.5, timeout_s=0.1)
    assert await e.embed_queries(["when will i marry"]) == [] and EMBED_DEGRADED.get() is True
    await asyncio.sleep(0.6)                         # load finishes in the background; the request never waited for it
    out = await e.embed_queries(["when will i marry"])
    assert len(out) == 1 and EMBED_DEGRADED.get() is False and e.stats["load_s"] >= 0.5


async def test_concurrent_requests_during_load_share_one_load():
    calls = []
    e = embedder(load_s=0.3, timeout_s=0.05)
    orig = e._load
    e._load = lambda: (calls.append(1), orig())[1]  # type: ignore[method-assign]
    await asyncio.gather(*[e.embed_queries([f"q{i}"]) for i in range(8)])
    await asyncio.sleep(0.4)
    assert len(calls) == 1


async def test_load_failure_degrades_without_raising_and_backs_off():
    e = embedder(fail=True)
    assert await e.embed_queries(["x"]) == [] and EMBED_DEGRADED.get() is True
    assert e.stats["load_failures"] == 1
    assert await e.embed_queries(["y"]) == []        # cooldown: no second load attempt
    assert e.stats["load_failures"] == 1


async def test_slow_inference_times_out_and_trips_the_cooldown():
    e = embedder(infer_s=0.4, timeout_s=0.1)
    assert await e.embed_queries(["warm"]) == []
    for i in range(3):
        assert await e.embed_queries([f"slow {i}"]) == []
    assert e.stats["timeouts"] >= 3
    t0 = time.perf_counter()
    assert await e.embed_queries(["after cooldown trip"]) == []
    assert time.perf_counter() - t0 < 0.05           # skipped without touching the model


async def test_cached_queries_are_served_even_when_degraded():
    e = embedder()
    first = await e.embed_queries(["saturn"])
    e.disable("test")
    assert await e.embed_queries(["saturn"]) == first and not EMBED_DEGRADED.get()
    assert await e.embed_queries(["a new question"]) == [] and EMBED_DEGRADED.get()


async def test_zero_timeout_means_unlimited():
    e = embedder(load_s=0.15, infer_s=0.15, timeout_s=0)
    out = await e.embed_queries(["no limit"])
    assert len(out) == 1 and not EMBED_DEGRADED.get()


async def test_retriever_serves_keys_and_fulltext_when_embedder_degrades():
    chunks = chunk_markdown("## Sade Sati\n\nSade sati is the seven and a half year Saturn transit over the Moon "
                            "in vedic astrology.", "vedic_astrology.md")
    store = MemoryStore()
    await run_ingest(store, HashEmbedder(), chunks, kb_keys=["saturn transit"], smoke=False)
    broken = embedder(fail=True)
    r = Retriever(store, broken)
    got = await r.retrieve(kb_keys=[], question="what is sade sati and saturn", system="vedic")
    assert got and "sade sati" in got[0].heading_path.lower()
    assert broken.stats["degraded"] == 1   # the ContextVar does not cross the retriever's wait_for task; use the counter


def test_specs_have_unique_names_and_the_serving_candidates_are_384d():
    names = [s.name for s in SPECS.values()]
    assert len(names) == len(set(names))
    for k in ("bge-small", "minilm-l6-q", "arctic-xs", "minilm-l6", "e5-small"):
        assert SPECS[k].dim == 384
    assert isinstance(make_embedder("hash"), HashEmbedder)


async def test_ingest_refuses_to_index_a_partial_key_set():
    class Degraded(HashEmbedder):
        async def embed_queries(self, texts):
            return []

    chunks = chunk_markdown("## Sade Sati\n\nSaturn transit over the Moon.", "vedic_astrology.md")
    try:
        await run_ingest(MemoryStore(), Degraded(), chunks, kb_keys=["saturn transit"], smoke=False)
    except RuntimeError as exc:
        assert "keys" in str(exc)
    else:
        raise AssertionError("ingest must fail loudly when key embedding degrades")


def test_offline_factory_has_no_time_limit_and_spec_keys_resolve():
    e = make_embedder("minilm-l6-q")
    assert e._budget() is None and e.model_name.endswith("@int8")
    assert FastEmbedEmbedder("minilm-l6-q").spec is SPECS["minilm-l6-q"]                      # EMBEDDING_MODEL = spec key
    assert FastEmbedEmbedder("sentence-transformers/all-MiniLM-L6-v2@int8").spec is SPECS["minilm-l6-q"]   # or full name
