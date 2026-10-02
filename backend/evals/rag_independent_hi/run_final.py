"""Final-exam run on the fresh Hindi/Hinglish blind set: off vs local vs GATED, one pass each, nothing tuned.

GATED = keys+FTS first; query embeddings only when the query is non-English (Devanagari or Roman-Hindi marker words)
or the keys+FTS result is low_confidence (the shipped threshold, not tuned). Latency of a gated query = off pass +
(local pass if the gate opened). Scratch DB only:
    RAG_EVAL_DATABASE_URL=.../astroai_rag_scratch_q python -m evals.rag_independent_hi.run_final --embedder minilm-l6-q
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1]))
from evals.rag import run as R  # noqa: E402
from evals.rag.metrics import aggregate, percentile, resolve_gold, score_query  # noqa: E402

DEVA = re.compile(r"[ऀ-ॿ]")
ROMAN_HI = set("hai hain ki ka ke ko kya kab kaise kitne kitna kaun mera meri mere hota hoti hote mein me se par aur "
               "nahi nahin kyun kyu hoga hogi toh bhi tha thi kare karu karen rehti rehta wala wali kundli shani "
               "mahadasa dasha rashi graha shaadi vivah".split())


def non_english(text: str) -> bool:
    if DEVA.search(text):
        return True
    return len(set(re.findall(r"[a-z]+", text.lower())) & ROMAN_HI) >= 2


async def main_async(a) -> int:
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.rag.chunking import chunk_corpus
    from evals.rag.configs import build_config

    qs = [json.loads(l) for l in (HERE / "queries.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    qs = [q for q in qs if q["topic"] != "no_answer"]
    engine = create_async_engine(R.scratch_url(), pool_size=4)
    try:
        emb = R.make_embedder(a.embedder)
        chunks = chunk_corpus(R.KB)
        cfg = build_config("A6-phonetic")
        store, rep, _ = await R.build_index(engine, emb, chunks, kb_keys=cfg.preembed_keys(chunks))
        charts = R.load_charts()
        r_off, key_fn = cfg.make(store, None)
        r_loc, _ = cfg.make(store, emb)
        await r_loc.retrieve(kb_keys=[], question="warm up saturn", system="vedic")   # model load is not query latency
        rows: dict[str, list] = {"off": [], "local": [], "gated": []}
        lat = {"off": [], "local": [], "gated": []}
        opened = det_ok = 0
        for q in qs:
            rel = resolve_gold(q["gold"], chunks)
            keys = key_fn(charts["delhi_1994"], q)
            kw = dict(kb_keys=keys, question=q["text"], system=q["system"], topic=q["topic"], language=R.LANG_NAME[q["lang"]])
            t = time.perf_counter(); o = await r_off.retrieve_ex(**kw); to = (time.perf_counter() - t) * 1000
            t = time.perf_counter(); l = await r_loc.retrieve_ex(**kw); tl = (time.perf_counter() - t) * 1000
            gate = non_english(q["text"]) or o.low_confidence
            det_ok += non_english(q["text"])
            opened += gate
            g = l if gate else o
            for name, res, ms in (("off", o, to), ("local", l, tl), ("gated", g, to + (tl if gate else 0))):
                rows[name].append((q, score_query([c.chunk_id for c in res.chunks], rel)))
                lat[name].append(ms)
        out = {"embedder": emb.model_name, "n": len(qs), "gate_opened": opened, "non_english_detected": det_ok}
        for name in rows:
            m = {"all": aggregate([s for _, s in rows[name]]), "p50": round(percentile(lat[name], .5), 1),
                 "p95": round(percentile(lat[name], .95), 1)}
            for dim in ("lang", "topic"):
                grp = defaultdict(list)
                for q, s in rows[name]:
                    grp[q[dim]].append(s)
                m[dim] = {k: aggregate(v) for k, v in sorted(grp.items())}
            out[name] = m
            lg = m["lang"]
            print(f"{emb.model_name[:38]:38} {name:6} hit@5 {m['all']['hit@5']:.3f} hit@10 {m['all']['hit@10']:.3f} "
                  f"MRR {m['all']['mrr']:.3f} nDCG {m['all']['ndcg@10']:.3f} | hi {lg['hi']['hit@5']:.2f} hg {lg['hg']['hit@5']:.2f} "
                  f"| p50 {m['p50']} p95 {m['p95']}")
        print("gate opened", opened, "/", len(qs), "(non-English detector fired on", det_ok, ")")
        (HERE / f"final_{a.label}.json").write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    finally:
        await engine.dispose()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--embedder", required=True)
    ap.add_argument("--label", default=None)
    a = ap.parse_args()
    a.label = a.label or a.embedder
    return asyncio.run(main_async(a))


if __name__ == "__main__":
    raise SystemExit(main())
