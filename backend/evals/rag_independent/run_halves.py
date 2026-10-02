"""Embedder comparison on the independent blind set, split by id parity (even = tuning half, odd = blind half),
plus the older 204-query set for regression. One index build per embedder; the keys+FTS baseline (runtime off)
is measured on the SAME index and code snapshot so deltas are paired.

    RAG_EVAL_DATABASE_URL=postgresql+asyncpg://.../astroai_rag_scratch_q \
    python -m evals.rag_independent.run_halves --embedder minilm-l6-q --label q_minilm --config A6-phonetic

Scratch DB only (the runner refuses names without 'scratch'). The vector column is vector(384): a model with
another dimension needs the migration in docs/rag-runbook.md section 2c first.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
BACKEND = HERE.parents[1]
sys.path.insert(0, str(BACKEND))

from evals.rag import run as R  # noqa: E402
from evals.rag.metrics import aggregate, resolve_gold, score_query  # noqa: E402


def load_indep() -> list[dict]:
    qs = [json.loads(l) for l in (HERE / "queries.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return [q for q in qs if q["topic"] != "no_answer"]


def parity(q: dict) -> str:
    return "even" if int(q["id"].split(":")[2]) % 2 == 0 else "odd"


async def run_set(retriever, key_fn, queries, charts, chunks) -> dict:
    out = await R.evaluate(retriever, queries, charts, chunks, key_fn)
    out.pop("per_query", None)
    return out


async def main_async(a) -> int:
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.rag.chunking import chunk_corpus
    from evals.rag.configs import build_config

    engine = create_async_engine(R.scratch_url(), pool_size=4)
    try:
        embedder = R.make_embedder(a.embedder)
        chunks = chunk_corpus(R.KB)
        cfg = build_config(a.config)
        t0 = time.perf_counter()
        store, rep, secs = await R.build_index(engine, embedder, chunks, kb_keys=cfg.preembed_keys(chunks))
        print(f"indexed {rep.chunks} chunks (+{rep.keys} keys) with {embedder.model_name} (dim {embedder.dim}) in {secs:.0f}s")
        charts = R.load_charts()
        indep, old = load_indep(), R.load_queries()
        sets = {"even": [q for q in indep if parity(q) == "even"], "odd": [q for q in indep if parity(q) == "odd"],
                "old204": old}
        res: dict = {"embedder": embedder.model_name, "dim": embedder.dim, "config": a.config, "chunks": len(chunks),
                     "keys": rep.keys}
        for runtime in ("local", "off"):
            retriever, key_fn = cfg.make(store, None if runtime == "off" else embedder)
            await R.evaluate(retriever, sets["even"][:6], charts, chunks, key_fn)     # warm-up
            res[runtime] = {name: await run_set(retriever, key_fn, qs, charts, chunks) for name, qs in sets.items()}
            for name in sets:
                m = res[runtime][name]
                print(f"{runtime:5} {name:7} n={m['n']:3} hit@5 {m['all']['hit@5']:.3f} hit@10 {m['all']['hit@10']:.3f} "
                      f"MRR {m['all']['mrr']:.3f} nDCG@10 {m['all']['ndcg@10']:.3f} p50 {m['latency_ms']['p50']}ms")
        (HERE / "reports").mkdir(exist_ok=True)
        (HERE / "reports" / f"{a.label}.json").write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    finally:
        await engine.dispose()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--embedder", required=True)
    ap.add_argument("--label", required=True)
    ap.add_argument("--config", default="A6-phonetic")
    return asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
