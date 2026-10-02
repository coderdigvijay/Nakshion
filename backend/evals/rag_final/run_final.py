"""FINAL EXAM: off vs local on evals/rag_final/queries.jsonl. One pass per configuration, nothing tuned.
    RAG_EVAL_DATABASE_URL=.../astroai_rag_scratch_q python -m evals.rag_final.run_final --embedder minilm-l6-q
Reports: evals/rag_final/final_<embedder>.json (metrics, traps, per-query rows incl. top-5 headings for the worst misses)."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from evals.rag import run as R  # noqa: E402
from evals.rag.metrics import aggregate, percentile, resolve_gold, score_query  # noqa: E402


async def main_async(a) -> int:
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.rag.chunking import chunk_corpus
    from evals.rag.configs import build_config

    allq = [json.loads(l) for l in (HERE / "queries.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    qs = [q for q in allq if q["topic"] != "no_answer"]
    traps = [q for q in allq if q["topic"] == "no_answer"]
    engine = create_async_engine(R.scratch_url(), pool_size=4)
    try:
        emb = R.make_embedder(a.embedder)
        chunks = chunk_corpus(R.KB)
        by_id = {c.id: c for c in chunks}
        cfg = build_config("A6-phonetic")
        store, rep, _ = await R.build_index(engine, emb, chunks, kb_keys=cfg.preembed_keys(chunks))
        charts = R.load_charts()
        out = {"embedder": emb.model_name, "n": len(qs), "traps": len(traps)}
        for name, e in (("off", None), ("local", emb)):
            ret, key_fn = cfg.make(store, e)
            if e:
                await ret.retrieve(kb_keys=[], question="warm up saturn", system="vedic")
            rows, lat, per = [], [], []
            for q in qs:
                rel = resolve_gold(q["gold"], chunks)
                kw = dict(kb_keys=key_fn(charts["delhi_1994"], q), question=q["text"], system=q["system"],
                          topic=q["topic"], language=R.LANG_NAME[q["lang"]])
                t = time.perf_counter(); res = await ret.retrieve_ex(**kw); ms = (time.perf_counter() - t) * 1000
                ids = [c.chunk_id for c in res.chunks]
                s = score_query(ids, rel)
                rows.append((q, s)); lat.append(ms)
                per.append({"id": q["id"], "lang": q["lang"], "topic": q["topic"], "text": q["text"], "low_conf": res.low_confidence,
                            "gold": [(g["file"], g["h"], g["g"]) for g in q["gold"]], "ndcg": s["ndcg@10"], "hit5": s["hit@5"],
                            "top5": [c.heading_path[:90] + " | " + c.file for c in res.chunks[:5]]})
            flagged = 0
            for q in traps:
                kw = dict(kb_keys=key_fn(charts["delhi_1994"], q), question=q["text"], system=q["system"], topic="general",
                          language=R.LANG_NAME[q["lang"]])
                flagged += (await ret.retrieve_ex(**kw)).low_confidence
            m = {"all": aggregate([s for _, s in rows]), "p50": round(percentile(lat, .5), 1), "p95": round(percentile(lat, .95), 1),
                 "traps_flagged": f"{flagged}/{len(traps)}", "false_pos_low_conf": f"{sum(p['low_conf'] for p in per)}/{len(per)}"}
            for dim in ("lang", "topic"):
                g = defaultdict(list)
                for q, s in rows:
                    g[q[dim]].append(s)
                m[dim] = {k: {**aggregate(v), "n": len(v)} for k, v in sorted(g.items())}
            m["worst"] = sorted(per, key=lambda p: (p["hit5"], p["ndcg"]))[:10]
            m["per_query"] = per
            out[name] = m
            a_ = m["all"]; lg = m["lang"]
            print(f"{emb.model_name[:34]:34} {name:5} hit@5 {a_['hit@5']:.3f} hit@10 {a_['hit@10']:.3f} MRR {a_['mrr']:.3f} nDCG {a_['ndcg@10']:.3f} | "
                  + " ".join(f"{k} {v['hit@5']:.2f}" for k, v in lg.items()) + f" | traps flagged {m['traps_flagged']} FP {m['false_pos_low_conf']} | p50 {m['p50']} p95 {m['p95']}")
        (HERE / f"final_{a.embedder}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    finally:
        await engine.dispose()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--embedder", required=True)
    return asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
