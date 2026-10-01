"""Database-free retrieval evaluation (CI gate). Same queries, gold, metrics and Retriever as the
Postgres run; the in-memory store implements the same hybrid_search contract in Python."""

from __future__ import annotations

from pathlib import Path

from app.rag.chunking import chunk_corpus
from app.rag.keys import generate_keys
from app.rag.retriever import Retriever, RetrievalConfig
from app.rag.store import MemoryStore
from evals.rag.run import KB, evaluate, legacy_keys, load_charts, load_queries


async def build_memory_index(embedder, *, with_keys: bool = True):
    from app.rag.ingest import run_ingest

    store = MemoryStore()
    chunks = chunk_corpus(KB)
    await run_ingest(store, embedder, chunks, kb_keys=generate_keys() if with_keys else [], force=True, smoke=False)
    return store, chunks


async def evaluate_memory(embedder, cfg: RetrievalConfig | None = None, *, limit: int | None = None,
                          runtime_embedder=True) -> dict:
    from dataclasses import replace

    store, chunks = await build_memory_index(embedder)
    cfg = replace(cfg or RetrievalConfig(), token_cap=10**9, top_k=10, timeout_s=60.0)
    r = Retriever(store, embedder if runtime_embedder else None, config=cfg)
    return await evaluate(r, load_queries(limit), load_charts(), chunks, lambda chart, q: legacy_keys(chart, q["system"]))
