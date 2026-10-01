"""CI retrieval-quality gates (thresholds sit ~3-5 points under the measured values, so they catch regressions in
chunking, query planning, fusion, glossary or boosts without being flaky).

  1. hash embedder + in-memory store   : always runs, no model, no DB   (floor guard: lexical + glossary + keys)
  2. bge-small + in-memory store       : runs when the fastembed model is cached locally (else skipped)
  3. bge-small + real pgvector SCRATCH : runs when RAG_EVAL_DATABASE_URL names a *scratch* database
The LLM-judged answer-level eval (evals/rag/answer_eval.py) is separate and needs provider keys.
Measured over 409 real-chart / free-form queries (EN, HI, Hinglish) on the 773-chunk corpus: docs/rag-runbook.md.
"""

from __future__ import annotations

import os

import pytest

from app.rag.embeddings import HashEmbedder
from evals.rag.inmem import evaluate_memory

from .conftest import scratch_db_url


def check(m: dict, *, hit5, ndcg, recall5, mrr, hi_hit5, holdout2_hit5, p95_ms, holdout4_hit5=0.0) -> None:
    a = m["all"]
    assert a["hit@5"] >= hit5, f"hit@5 {a['hit@5']} < {hit5}"
    assert a["ndcg@10"] >= ndcg, f"nDCG@10 {a['ndcg@10']} < {ndcg}"
    assert a["recall@5"] >= recall5, f"recall@5 {a['recall@5']} < {recall5}"
    assert a["mrr"] >= mrr, f"MRR {a['mrr']} < {mrr}"
    assert m["lang"]["hi"]["hit@5"] >= hi_hit5, f"Hindi hit@5 {m['lang']['hi']['hit@5']} < {hi_hit5}"
    assert m["split"]["holdout2"]["hit@5"] >= holdout2_hit5, f"blind holdout hit@5 {m['split']['holdout2']['hit@5']}"
    assert m["split"]["holdout4"]["hit@5"] >= holdout4_hit5, f"holdout4 hit@5 {m['split']['holdout4']['hit@5']}"
    assert m["latency_ms"]["p95"] <= p95_ms, f"p95 {m['latency_ms']['p95']}ms > {p95_ms}"
    assert m["n"] >= 400


async def test_gate_lexical_floor_with_hash_embedder():
    m = await evaluate_memory(HashEmbedder())
    check(m, hit5=0.78, ndcg=0.50, recall5=0.54, mrr=0.59, hi_hit5=0.68, holdout2_hit5=0.74, p95_ms=700, holdout4_hit5=0.70)


def _bge_cached() -> bool:
    try:
        from fastembed import TextEmbedding

        TextEmbedding("BAAI/bge-small-en-v1.5", local_files_only=True)
        return True
    except Exception:  # noqa: BLE001
        return False


@pytest.mark.skipif(not _bge_cached(), reason="bge-small model not cached locally")
async def test_gate_bge_small_in_memory():
    from evals.rag.run import make_embedder

    m = await evaluate_memory(make_embedder("bge-small"))
    check(m, hit5=0.89, ndcg=0.60, recall5=0.64, mrr=0.71, hi_hit5=0.83, holdout2_hit5=0.82, p95_ms=700, holdout4_hit5=0.84)


@pytest.mark.skipif(not (scratch_db_url() and _bge_cached()), reason="RAG_EVAL_DATABASE_URL (scratch) not set")
async def test_gate_bge_small_on_pgvector_scratch():
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.rag.chunking import chunk_corpus
    from evals.rag.configs import build_config
    from evals.rag.run import KB, build_index, evaluate, load_charts, load_queries, make_embedder

    engine = create_async_engine(scratch_db_url(), pool_size=2)
    try:
        emb, cfg = make_embedder("bge-small"), build_config("v2")
        chunks = chunk_corpus(KB)
        store, rep, _ = await build_index(engine, emb, chunks, kb_keys=cfg.preembed_keys(chunks))
        retriever, key_fn = cfg.make(store, emb)
        m = await evaluate(retriever, load_queries(), load_charts(), chunks, key_fn)
    finally:
        await engine.dispose()
    check(m, hit5=0.85, ndcg=0.58, recall5=0.62, mrr=0.69, hi_hit5=0.79, holdout2_hit5=0.82, p95_ms=250, holdout4_hit5=0.78)


@pytest.mark.skipif(not (scratch_db_url() and _bge_cached()), reason="RAG_EVAL_DATABASE_URL (scratch) not set")
async def test_pgvector_matches_memory_store_for_vector_only_search():
    """The single-round-trip SQL and the Python fusion must rank identically (vector-only: no FTS differences)."""
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.rag.chunking import chunk_corpus
    from app.rag.store import PgVectorStore, SearchSpec
    from evals.rag.inmem import build_memory_index
    from evals.rag.run import KB, build_index, make_embedder

    emb = make_embedder("bge-small")
    mem, chunks = await build_memory_index(emb, with_keys=False)
    engine = create_async_engine(scratch_db_url(), pool_size=2)
    try:
        pg, _, _ = await build_index(engine, emb, chunks)
        for q in ("saturn return and maturity", "moon in ashlesha nakshatra", "seventh house partnership"):
            v = await emb.embed_query(q)
            spec = lambda ver: SearchSpec(version=ver, systems=["vedic", "western", "both"], vectors=[("q1", v, 1.0)],  # noqa: E731
                                          per_query=20, limit=10)
            a = [c.chunk_id for c in await mem.hybrid_search(spec(await mem.active_version()))]
            b = [c.chunk_id for c in await pg.hybrid_search(spec(await pg.active_version()))]
            assert a[:8] == b[:8], (q, a[:4], b[:4])
    finally:
        await engine.dispose()
