from __future__ import annotations

import asyncio
import json
import logging

import pytest

from app.rag.chunking import chunk_markdown
from app.rag.embeddings import HashEmbedder
from app.rag.ingest import run_ingest
from app.rag.retriever import RedisJsonCache, Retriever, RetrievalConfig, RetrievedChunk, systems_for
from app.rag.store import MemoryStore, SearchSpec, tsquery_text


def corpus():
    vedic = chunk_markdown("## Sade Sati\n\nSade sati is the seven and a half year Saturn transit over the Moon in vedic astrology.",
                           "vedic_astrology.md")
    west = chunk_markdown("## Saturn Return\n\nThe Saturn return at age 29 brings maturity and structure to the natal chart.",
                          "timing_transits.md")
    both = chunk_markdown("## Venus\n\nVenus in Libra loves harmony and partnership in love relationships.", "planets.md")
    excl = chunk_markdown("## Elections\n\nMundane Saturn and national elections in world events.", "mundane_astrology.md")
    t3 = chunk_markdown("## Saturn Teacher\n\nSaturn teaches limits, patience and structure through the psychology of the chart.",
                        "books_greene_saturn.md")
    return vedic + west + both + excl + t3


async def make(cfg=None, *, keys=None, embedder=True, **kw):
    store, emb = MemoryStore(), HashEmbedder()
    await run_ingest(store, emb, corpus(), kb_keys=keys or ["saturn transit", "venus in libra"], smoke=False)
    return store, emb, Retriever(store, emb if embedder else None, config=cfg or RetrievalConfig(), **kw)


async def test_system_filter_and_excluded_only_on_explicit_topic():
    _, _, r = await make()
    v = await r.retrieve(kb_keys=[], question="What is sade sati and saturn?", system="vedic")
    assert v and {c.system for c in v} <= {"vedic", "both"}
    w = await r.retrieve(kb_keys=[], question="Tell me about saturn", system="western")
    assert {c.system for c in w} <= {"western", "both"}
    m = await r.retrieve(kb_keys=[], question="saturn in national elections, mundane world events", system="both")
    assert any(c.system == "excluded" for c in m)
    assert systems_for("vedic") == ["vedic", "both"]


async def test_tier_three_is_down_weighted_and_licence_exclusion_works():
    store, emb, r = await make()
    out = await r.retrieve(kb_keys=[], question="saturn patience structure", system="western")
    assert out[0].meta["tier"] <= 2 or len(out) == 1
    r2 = Retriever(store, emb, config=RetrievalConfig(exclude_licences=("modern_author_paraphrase",)))
    out2 = await r2.retrieve(kb_keys=[], question="saturn patience structure", system="western")
    assert all(c.meta["licence"] != "modern_author_paraphrase" for c in out2)


async def test_unrelated_factor_keys_do_not_drown_the_question():
    """Regression for the legacy design (hit@5 0.21): six unrelated top-factor keys must not outvote the question."""
    _, _, r = await make(keys=["venus in libra", "saturn transit", "sun in cancer", "moon in taurus"])
    res = await r.retrieve_ex(kb_keys=["venus in libra", "sun in cancer", "moon in taurus"],
                              question="What is sade sati?", system="vedic")
    assert "sade" in res.chunks[0].heading_path.lower()
    assert res.stats["keys_used"] == 0 and res.stats["keys_dropped"] == 3


async def test_diversity_dedup_and_token_cap():
    store, emb, _ = await make()
    r = Retriever(store, emb, config=RetrievalConfig(token_cap=40, top_k=5))
    out = await r.retrieve(kb_keys=[], question="saturn venus love structure", system="both")
    assert sum(len(c.content.split()) for c in out) <= 80 and len({c.heading_path for c in out}) == len(out)


async def test_hindi_question_uses_gloss_and_english_only_model_never_sees_devanagari():
    seen: list[str] = []

    class Spy(HashEmbedder):
        async def embed_queries(self, texts):
            seen.extend(texts)
            return await super().embed_queries(texts)

    store = MemoryStore()
    await run_ingest(store, Spy(), corpus(), smoke=False)
    r = Retriever(store, Spy(), config=RetrievalConfig())
    out = await r.retrieve(kb_keys=[], question="साढ़ेसाती क्या है", system="vedic", language="hindi")
    assert out and "sade" in out[0].heading_path.lower()
    assert seen and all(not any("ऀ" <= ch <= "ॿ" for ch in t) for t in seen)


async def test_runtime_off_uses_preembedded_keys_and_fts():
    _, _, r = await make(embedder=False)
    out = await r.retrieve(kb_keys=["venus in libra"], question="harmony in love", system="both")
    assert out and "Venus" in out[0].heading_path


# ----------------------------------------------------------------------------- degradation


class BrokenStore(MemoryStore):
    async def hybrid_search(self, spec):
        raise ConnectionError("db down")


async def test_failure_returns_empty_degraded_and_never_raises():
    store = BrokenStore()
    await run_ingest(store, HashEmbedder(), corpus(), smoke=False)
    r = Retriever(store, HashEmbedder())
    res = await r.retrieve_ex(kb_keys=[], question="saturn", system="both")
    assert res.chunks == [] and res.degraded and res.reason == "error"
    assert await r.retrieve(kb_keys=[], question="saturn") == []
    assert r.metrics.errors == 2


async def test_no_index_is_degraded_not_error():
    r = Retriever(MemoryStore(), HashEmbedder())
    res = await r.retrieve_ex(kb_keys=[], question="saturn")
    assert res.degraded and res.reason == "no_index"


async def test_timeout_and_circuit_breaker():
    class Slow(MemoryStore):
        async def hybrid_search(self, spec):
            await asyncio.sleep(1)
            return []

    store = Slow()
    await run_ingest(store, HashEmbedder(), corpus(), smoke=False)
    r = Retriever(store, HashEmbedder(), config=RetrievalConfig(timeout_s=0.05))
    for _ in range(5):
        assert (await r.retrieve_ex(kb_keys=[], question="saturn")).reason == "timeout"
    res = await r.retrieve_ex(kb_keys=[], question="saturn")      # breaker open: instant, no store call
    assert res.degraded and res.reason == "breaker_open"
    assert r.metrics.timeouts == 5


async def test_self_check_reports_problems():
    _, _, r = await make()
    ok = await r.self_check()
    assert ok["ok"] and ok["chunks"] > 0 and ok["active_version"] == 1
    empty = await Retriever(MemoryStore(), HashEmbedder()).self_check()
    assert not empty["ok"] and "no active index" in empty["problems"][0]
    store, _, _ = await make()
    mismatch = await Retriever(store, HashEmbedder("other-model")).self_check()
    assert any("embedding model mismatch" in p for p in mismatch["problems"])


# ----------------------------------------------------------------------------- cache


class DictRedis:
    def __init__(self):
        self.d = {}
        self.sets = 0

    async def get(self, k):
        return self.d.get(k)

    async def set(self, k, v, ex=None):
        self.sets += 1
        self.d[k] = v


async def test_result_cache_hit_and_invalidated_by_reindex():
    redis = DictRedis()
    store, emb = MemoryStore(), HashEmbedder()
    await run_ingest(store, emb, corpus(), smoke=False)
    calls = {"n": 0}
    real = store.hybrid_search

    async def counted(spec):
        calls["n"] += 1
        return await real(spec)

    store.hybrid_search = counted
    r = Retriever(store, emb, cache=RedisJsonCache(redis))
    a = await r.retrieve(kb_keys=[], question="saturn sade sati", system="vedic")
    b = await r.retrieve(kb_keys=[], question="saturn sade sati", system="vedic")
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b] and calls["n"] == 1 and r.metrics.cache_hits == 1
    json.dumps(list(redis.d.values()))                                    # cache payload is plain JSON
    await run_ingest(store, emb, corpus()[:-1], smoke=False)             # reindex => new version => new cache keys
    await r.retrieve(kb_keys=[], question="saturn sade sati", system="vedic")
    assert calls["n"] == 2


async def test_cache_failure_is_ignored():
    class BadCache:
        async def get(self, k):
            raise ConnectionError("redis down")

        async def set(self, k, v, ttl):
            raise ConnectionError("redis down")

    _, _, r = await make(cache=BadCache())
    assert await r.retrieve(kb_keys=[], question="saturn sade sati", system="vedic")


# ----------------------------------------------------------------------------- privacy


async def test_logs_contain_counts_not_question_text_or_chunk_text(caplog):
    _, _, r = await make()
    secret = "my birth was on 21 July 1994 in Delhi what about saturn"
    with caplog.at_level(logging.INFO, logger="nakshion.rag.retriever"):
        await r.retrieve(kb_keys=["saturn transit"], question=secret, system="both")
    text = " ".join(f"{rec.getMessage()} {getattr(rec, 'rag', '')}" for rec in caplog.records)
    assert "rag_retrieve" in text and "latency_ms" in text
    assert "1994" not in text and "Delhi" not in text and "Venus in Libra loves" not in text


def test_tsquery_text_cannot_inject_syntax():
    q = tsquery_text(["saturn & !moon", "a'; DROP TABLE kb_chunks; --", "7th house"])
    assert set(q) <= set("abcdefghijklmnopqrstuvwxyz0123456789 |")
