"""Live check of the personal daily reading path (BUG-025): the real engine facts, the production retriever (read-only)
and Gemini, wrapped in the same outer wait_for the app adapter uses.

    python -m evals.daily_sweep --label before [--outer 20] [--latency-rag 0] [--runs 1]

Prints per case: outcome (llm | template/exception), wall time, per-attempt usage (model, outcome, ms), and the
validator flags. Synthetic charts only. Keys come from backend/.env and are never printed.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

CASES = [("A", "english", "vedic"), ("A", "hindi", "vedic"), ("A", "hinglish", "vedic"), ("B", "english", "vedic"),
         ("C", "english", "western"), ("A", "english", "vedic"), ("A", "hindi", "vedic")]


async def run(args) -> int:
    from dotenv import dotenv_values
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.astrology.personal import personal_day
    from app.llm import service as svc
    from app.llm.config import LLMSettings
    from app.llm.usage import MemoryUsageSink
    from app.rag import PgVectorStore, Retriever
    from app.rag.embeddings import make_embedder
    from evals.quality_sweep import charts

    cs = charts()
    where = {"A": (28.61, 77.21, "Asia/Kolkata"), "B": (19.07, 72.88, "Asia/Kolkata"), "C": (51.5, -0.12, "Europe/London")}
    s = LLMSettings()
    engine = create_async_engine(dotenv_values(Path(__file__).resolve().parents[1] / ".env")["DATABASE_URL"], pool_size=2)
    base = Retriever(PgVectorStore(engine), make_embedder("bge-small", threads=1))

    class SlowRetriever:
        """Adds artificial latency to retrieval (the free Render CPU embeds slowly)."""

        async def retrieve(self, **kw):
            await asyncio.sleep(args.latency_rag)
            return await base.retrieve(**kw)

    sink = MemoryUsageSink()
    svc.configure(s, retriever=SlowRetriever() if args.latency_rag else base, usage_sink=sink)
    rows = []
    for i, (ck, lang, system) in enumerate(CASES):
        lat, lon, tz = where[ck]
        facts = personal_day(cs[ck], date(2026, 10, 2), system=system, latitude=lat, longitude=lon, timezone=tz)
        n0 = len(sink.records)
        t0 = time.monotonic()
        try:
            kw = {"budget_s": args.budget} if args.budget else {}
            out = await asyncio.wait_for(svc.generate_daily_personal(facts, language=lang, system=system, **kw), timeout=args.outer)
            res, err = "llm", None
        except BaseException as exc:  # noqa: BLE001
            out, res, err = None, "template", type(exc).__name__
        dt = time.monotonic() - t0
        att = [(u.model, u.outcome, u.latency_ms, (u.error or "")[:60]) for u in sink.records[n0:]]
        print(f"[{i}] {ck} {lang:8} {system:7} -> {res:8} {dt:5.1f}s err={err} attempts={att}")
        rows.append({"case": [ck, lang, system], "result": res, "seconds": round(dt, 1), "error": err, "attempts": att,
                     "headline": (out or {}).get("headline"), "overview": (out or {}).get("overview"),
                     "areas": (out or {}).get("areas"), "affirmation": (out or {}).get("affirmation")})
    ok = sum(r["result"] == "llm" for r in rows)
    print(f"LLM readings: {ok}/{len(rows)}; median {sorted(r['seconds'] for r in rows)[len(rows)//2]}s")
    Path(args.out).joinpath(f"daily-{args.label}.json").write_text(json.dumps(rows, indent=1, ensure_ascii=False), encoding="utf-8")
    await engine.dispose()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="run")
    ap.add_argument("--out", default=".")
    ap.add_argument("--outer", type=float, default=20.0)
    ap.add_argument("--latency-rag", type=float, default=0.0)
    ap.add_argument("--budget", type=float, default=0.0)
    return asyncio.run(run(ap.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
