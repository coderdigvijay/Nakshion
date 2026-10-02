"""Retrieval evaluation against a real Postgres+pgvector SCRATCH database.

    python -m evals.rag.run --label baseline --config legacy
    python -m evals.rag.run --label e5 --config v2 --embedder e5-small

Safety: refuses any database whose name does not contain "scratch" (it TRUNCATEs the kb_* tables).
Default DB: the dev server's `astroai_rag_scratch` (derived from backend/.env, never printed).
Reports go to evals/rag/reports/<label>.json. Metrics: hit@5/10, capped recall@5/10, MRR, nDCG@10
over graded gold (see evals/rag/build_queries.py), split by language and by source, plus p50/p95
retrieval latency (query embedding included).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
# Eval harness only: the production embed-query timeout (0.4 s) degrades a cold model to keys+FTS. Measurements need the
# model to answer, so lift the limit here; production settings are untouched.
os.environ.setdefault("EMBED_QUERY_TIMEOUT_S", "0")
BACKEND = HERE.parents[1]
sys.path.insert(0, str(BACKEND))

from evals.rag.metrics import aggregate, percentile, resolve_gold, score_query  # noqa: E402

KB = BACKEND / "knowledge_base"
LANG_NAME = {"en": "english", "hi": "hindi", "hg": "hinglish"}


def scratch_url() -> str:
    url = os.environ.get("RAG_EVAL_DATABASE_URL")
    if not url:
        from dotenv import dotenv_values

        base = dotenv_values(BACKEND / ".env")["DATABASE_URL"]
        url = base.rsplit("/", 1)[0] + "/astroai_rag_scratch"
    name = url.rsplit("/", 1)[1].split("?")[0]
    if "scratch" not in name:
        raise SystemExit(f"refusing to run on database {name!r}: name must contain 'scratch'")
    return url


def load_queries(limit: int | None = None) -> list[dict]:
    qs = [json.loads(l) for l in (HERE / "queries.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    return qs[:limit] if limit else qs


def load_charts() -> dict:
    return json.loads((BACKEND / "evals" / "fixtures" / "real_charts.json").read_text(encoding="utf-8"))


class CachedEmbedder:
    """Eval-only: persists document embeddings on disk (keyed by model + text hash) so repeated
    ablations do not re-embed the corpus. Query embedding passes through (it is what we time)."""

    def __init__(self, inner) -> None:
        import hashlib

        self.inner = inner
        self.model_name, self.dim = inner.model_name, inner.dim
        self._h = hashlib.sha1
        safe = inner.model_name.replace("/", "_").replace("@", "_").replace("+", "_")
        self.path = HERE / ".cache" / f"{safe}.json"
        self.path.parent.mkdir(exist_ok=True)
        self.cache: dict[str, list[float]] = json.loads(self.path.read_text()) if self.path.exists() else {}

    async def embed_documents(self, texts):
        keys = [self._h(t.encode()).hexdigest() for t in texts]
        miss = [i for i, k in enumerate(keys) if k not in self.cache]
        if miss:
            vecs = await self.inner.embed_documents([texts[i] for i in miss])
            for i, v in zip(miss, vecs):
                self.cache[keys[i]] = [round(x, 6) for x in v]
            self.path.write_text(json.dumps(self.cache))
        return [self.cache[k] for k in keys]

    async def embed_query(self, text):
        return await self.inner.embed_query(text)

    async def embed_queries(self, texts):
        # factor keys are embedded as queries at ingest; cache them under a distinct key
        keys = ["q:" + self._h(t.encode()).hexdigest() for t in texts]
        if len(texts) > 40:   # bulk (ingest of kb_keys): cache. Single query-time embeddings pass through (timed).
            miss = [i for i, k in enumerate(keys) if k not in self.cache]
            if miss:
                vecs = await self.inner.embed_queries([texts[i] for i in miss])
                for i, v in zip(miss, vecs):
                    self.cache[keys[i]] = [round(x, 6) for x in v]
                self.path.write_text(json.dumps(self.cache))
            return [self.cache[k] for k in keys]
        return await self.inner.embed_queries(texts)


def make_embedder(name: str):
    from app.rag.embeddings import make_embedder as mk

    inner = mk(name, threads=None) if name != "hash" else mk(name)
    return CachedEmbedder(inner)


async def build_index(engine, embedder, chunks, kb_keys: list[str] | None = None, reset: bool = True):
    from sqlalchemy import text

    from app.rag.ingest import run_ingest
    from app.rag.store import PgVectorStore

    store = PgVectorStore(engine)
    if reset:
        async with engine.begin() as c:
            await c.execute(text("TRUNCATE kb_chunks, kb_key_embeddings, kb_meta"))
    t0 = time.perf_counter()
    rep = await run_ingest(store, embedder, chunks, kb_keys=kb_keys, force=True)
    return store, rep, time.perf_counter() - t0


def legacy_keys(chart: dict | None, system: str) -> list[str]:
    from app.llm.facts import build_chart_facts

    if chart is None:
        return []
    facts = build_chart_facts(chart, system=system)
    return [k for f in facts.factors[:6] for k in f.kb_keys]


async def evaluate(retriever, queries, charts, chunks, key_fn, *, warm: bool = True) -> dict:
    rows, lat, per_q, strict_rows = [], [], [], []
    default_chart = charts["delhi_1994"]
    for q in queries:
        rel = resolve_gold(q["gold"], chunks)
        chart = charts[q["chart"]] if q["chart"] else default_chart  # free-form: user's own chart supplies factor keys
        keys = key_fn(chart, q)
        t0 = time.perf_counter()
        got = await retriever.retrieve(kb_keys=keys, question=q["text"], system=q["system"], topic=q["topic"],
                                       language=LANG_NAME[q["lang"]])
        dt = (time.perf_counter() - t0) * 1000
        ids = [c.chunk_id for c in got]
        s = score_query(ids, rel)
        if "gold_strict" in q:                       # original (pre-new-corpus) gold, for the regression comparison
            s_strict = score_query(ids, resolve_gold(q["gold_strict"], chunks))
            strict_rows.append(s_strict)
        elif q["split"] not in ("holdout3", "holdout4"):
            strict_rows.append(s)
        rows.append((q, s))
        lat.append(dt)
        per_q.append({"id": q["id"], "lang": q["lang"], "ms": round(dt, 1), "top": ids[:5], **s})
    out = {"all": aggregate([s for _, s in rows])}
    out["strict_old_gold"] = aggregate(strict_rows)
    out["strict_old_gold"]["n"] = len(strict_rows)
    for dim in ("lang", "source", "split", "topic"):
        groups = defaultdict(list)
        for q, s in rows:
            groups[q[dim]].append(s)
        out[dim] = {k: aggregate(v) for k, v in sorted(groups.items())}
    out["latency_ms"] = {"p50": round(percentile(lat, 0.5), 1), "p95": round(percentile(lat, 0.95), 1),
                         "mean": round(sum(lat) / len(lat), 1)}
    out["n"] = len(rows)
    out["per_query"] = per_q
    return out


def fmt(label: str, m: dict) -> str:
    a = m["all"]
    lang = m["lang"]
    sp = m.get("split", {})
    hold = ""
    for k in ("dev", "holdout", "holdout2", "holdout3", "holdout4"):
        if k in sp:
            hold += f" | {k} hit@5 {sp[k]['hit@5']:.3f} R@5 {sp[k]['recall@5']:.3f} nDCG {sp[k]['ndcg@10']:.3f}"
    st = m.get("strict_old_gold", {})
    hold += f" | STRICT-old-gold hit@5 {st.get('hit@5', 0):.3f} nDCG {st.get('ndcg@10', 0):.3f} (n={st.get('n', 0)})"
    return (f"{label:<28} hit@5 {a['hit@5']:.3f}  hit@10 {a['hit@10']:.3f}  R@5 {a['recall@5']:.3f}  "
            f"R@10 {a['recall@10']:.3f}  MRR {a['mrr']:.3f}  nDCG@10 {a['ndcg@10']:.3f} | hit@5 en {lang['en']['hit@5']:.2f} "
            f"hi {lang['hi']['hit@5']:.2f} hg {lang['hg']['hit@5']:.2f} | p50 {m['latency_ms']['p50']}ms "
            f"p95 {m['latency_ms']['p95']}ms" + hold)


async def main_async(args) -> int:
    from sqlalchemy.ext.asyncio import create_async_engine

    from evals.rag.configs import build_config

    engine = create_async_engine(scratch_url(), pool_size=4)
    try:
        embedder = make_embedder(args.embedder)
        from app.rag.chunking import chunk_corpus

        chunks = chunk_corpus(KB)
        cfg = build_config(args.config)
        store, rep, secs = await build_index(engine, embedder, chunks, kb_keys=cfg.preembed_keys(chunks))
        print(f"indexed {rep.chunks} chunks (+{rep.keys} keys) with {embedder.model_name} in {secs:.1f}s")
        retriever, key_fn = cfg.make(store, None if args.runtime == "off" else embedder)
        qs, charts = load_queries(args.limit), load_charts()
        if args.warmup:
            await evaluate(retriever, qs[:6], charts, chunks, key_fn)
        m = await evaluate(retriever, qs, charts, chunks, key_fn)
        m.update(label=args.label, config=args.config, embedder=embedder.model_name, chunks=len(chunks))
        (HERE / "reports").mkdir(exist_ok=True)
        (HERE / "reports" / f"{args.label}.json").write_text(json.dumps(m, indent=1, ensure_ascii=False), encoding="utf-8")
        print(fmt(args.label, m))
        if args.worst:
            for p in sorted(m["per_query"], key=lambda r: r["ndcg@10"])[: args.worst]:
                print("  worst", p["id"], p["ndcg@10"], p["top"][:3])
    finally:
        await engine.dispose()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", required=True)
    ap.add_argument("--config", default="legacy")
    ap.add_argument("--embedder", default="bge-small")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--runtime", default="local", choices=["local", "off"], help="off = EMBEDDINGS_RUNTIME=off (keys + FTS only)")
    ap.add_argument("--worst", type=int, default=0)
    ap.add_argument("--warmup", action="store_true", default=True)
    return asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
