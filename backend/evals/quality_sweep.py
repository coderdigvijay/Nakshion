"""Live answer-quality sweep (BUG-025): 30 diverse questions through the production ChatResponder.

    python -m evals.quality_sweep --label v7 [--only 1,2,3] [--out DIR] [--pause 1.0]

Synthetic charts only (app.astrology.compute_natal_chart). The retriever is the production pgvector Retriever, used
READ-ONLY on the configured index (never ingests). Needs Gemini keys (backend/.env); keys are never printed.

Per answer it records outcome, model, latency, validator first-draft flags, KB notes provided/cited, and the shape
metrics: concept named in the first two sentences, boilerplate opening, chart-reference sentences, words, paragraphs,
language, hedging. The summary compares runs: `python -m evals.quality_sweep --compare before.json after.json`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import sys
import time
from datetime import date, datetime, time as dtime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

NOW = datetime(2026, 10, 2, 6, 0, tzinfo=timezone.utc)
TODAY = date(2026, 10, 2)

# id, question, language, chart key, system
QUESTIONS: list[tuple[int, str, str, str, str]] = [
    (1, "What does Mars mahadasha with Venus antardasha mean?", "english", "A", "vedic"),   # the exact live question
    (2, "What is Gajakesari yoga and how does it form?", "english", "A", "vedic"),
    (3, "What is the result of the Moon in the 7th house?", "english", "A", "vedic"),
    (4, "What is today's tithi and is it good for starting something new?", "english", "A", "vedic"),
    (5, "Which remedies are traditionally suggested for a weak Saturn?", "english", "A", "vedic"),
    (6, "How does Ashtakoota matching work and what is a good score?", "english", "A", "vedic"),
    (7, "What does Saturn Mahadasha usually bring?", "english", "A", "vedic"),
    (8, "What is Sade Sati?", "english", "A", "vedic"),
    (9, "What does Rahu Mahadasha with Jupiter antardasha mean for me?", "english", "A", "vedic"),
    (10, "How is my career looking?", "english", "A", "vedic"),
    (11, "What is my current dasha and what does it mean?", "english", "A", "vedic"),
    (12, "Will I get married soon?", "english", "A", "vedic"),
    (13, "मंगल महादशा में शुक्र की अंतर्दशा का क्या मतलब होता है?", "hindi", "A", "vedic"),
    (14, "शनि की साढ़ेसाती क्या होती है?", "hindi", "A", "vedic"),
    (15, "मेरी कुंडली में अभी कौन सी दशा चल रही है?", "hindi", "A", "vedic"),
    (16, "Mangal mahadasha mein Shukra ki antardasha ka kya matlab hota hai?", "hinglish", "A", "vedic"),
    (17, "Rahu Kaal kya hota hai aur kya isme kaam shuru karna chahiye?", "hinglish", "A", "vedic"),
    (18, "Meri Shani ki sade sati kaisi rahegi?", "hinglish", "B", "vedic"),
    (19, "What is my Lagna and what does the 10th house say about my career?", "english", "B", "vedic"),
    (20, "What does Moon Mahadasha with Rahu Antardasha mean?", "english", "B", "vedic"),
    (21, "Is Manglik dosha a problem in marriage?", "english", "A", "vedic"),
    (22, "Should I wear a blue sapphire for Saturn?", "english", "A", "vedic"),
    (23, "What does Venus in the 5th house mean?", "english", "C", "western"),
    (24, "What does Ketu in the 12th house mean?", "english", "A", "vedic"),
    (25, "Explain Vimshottari dasha in detail", "english", "A", "vedic"),
    (26, "What is the Navamsa chart used for?", "english", "A", "vedic"),
    (27, "Is today good for me to start a business?", "english", "A", "vedic"),
    (28, "How will my Saturn return affect me?", "english", "C", "western"),
    (29, "Bhakoot dosha kya hota hai aur kya yeh cancel ho sakta hai?", "hinglish", "A", "vedic"),
    (30, "Moon Venus ke saath hone ka kya matlab hai? Aur meri Moon kahan hai?", "hinglish", "A", "vedic"),
]


def charts() -> dict[str, dict]:
    from app.astrology import compute_natal_chart

    def mk(d, t, lat, lon, tz):
        return compute_natal_chart(date_of_birth=d, time_of_birth=t, has_exact_time=t is not None, latitude=lat,
                                   longitude=lon, timezone=tz, now_utc=NOW)

    return {
        "A": mk(date(1992, 4, 12), dtime(9, 30), 28.61, 77.21, "Asia/Kolkata"),    # Venus MD / Mercury AD, known time
        "B": mk(date(1988, 8, 3), None, 19.07, 72.88, "Asia/Kolkata"),             # unknown time, Sade Sati active
        "C": mk(date(1985, 11, 20), dtime(14, 10), 51.5, -0.12, "Europe/London"),  # western user
    }


HEDGE = re.compile(r"some (?:sources|traditions|schools|astrologers)|traditions? (?:differ|vary)|schools? (?:differ|vary)|"
                   r"sources? (?:differ|disagree)|according to (?:some|one)|varies|tends? to|traditionally|कुछ (?:स्रोत|परंपरा)|"
                   r"मतभेद|माना जाता|परंपरा|मान्यता|मानते|mana jata|manyata|aam taur", re.I)
MEDICAL_CERTAIN = re.compile(r"\byou will (?:definitely|certainly|surely)\b|100%|guarantee", re.I)


def metrics_for(res: dict, qt, lang: str, chart: dict, facts) -> dict:
    from app.llm.facts import ChartIndex
    from app.llm.validators import (_CHART_REF, check_answer_shape, check_claims, check_language, opens_with_concept,
                                    paragraphs, sentences)

    ans = res["answer"]
    md = res["metadata"]
    sents = sentences(ans)
    shape = check_answer_shape(ans, qt)
    viol = [v.detail for v in check_claims(ans, ChartIndex.from_chart(chart), facts, generic=qt.is_general) if v.kind in ("claim", "time_unknown")]
    return {
        "kind": qt.kind, "subtype": qt.subtype,
        "words": len(ans.split()), "paragraphs": len(paragraphs(ans)),
        "concept_first": opens_with_concept(ans, qt) if qt.kind == "general" else None,
        "chart_ref_sentences": sum(1 for s in sents if _CHART_REF.search(s)),
        "chart_led": bool(sents and _CHART_REF.search(sents[0])),
        "first_sentence": sents[0][:220] if sents else "",
        "shape_flags": [v.detail[:90] for v in shape],
        "grounded": not viol, "claim_viol": viol[:3],
        "language_ok": not check_language(ans, lang),
        "hedged": bool(HEDGE.search(ans)),
        "kb_provided": len(md.get("kb_chunk_ids", [])), "kb_cited": len(md.get("kb_cited", [])),
        "factor_cites": len(res["citations"]), "outcome": md["outcome"], "model": md["model"],
        "first_draft_flags": md.get("first_draft_flags"), "latency_ms": md["latency_ms"],
        "rag": md.get("rag"), "prompt": md.get("prompt_version"),
    }


async def run(args) -> int:
    from dotenv import dotenv_values
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.llm.config import LLMSettings
    from app.llm.errors import LLMError
    from app.llm.facts import build_chart_facts
    from app.llm.providers import build_providers
    from app.llm.qtype import classify_question
    from app.llm.responder import ChatInput, ChatResponder
    from app.llm.router import LLMRouter
    from app.llm.usage import MemoryUsageSink
    from app.rag import PgVectorStore, Retriever
    from app.rag.embeddings import make_embedder

    s = LLMSettings()
    provs = build_providers(s)
    if not provs:
        print("no provider keys; nothing to run")
        return 0
    cs = charts()
    engine = create_async_engine(dotenv_values(Path(__file__).resolve().parents[1] / ".env")["DATABASE_URL"], pool_size=2)
    retriever = Retriever(PgVectorStore(engine), make_embedder("bge-small", threads=1))
    sink = MemoryUsageSink()
    resp = ChatResponder(LLMRouter(s, provs, usage_sink=sink), retriever=retriever)
    only = {int(x) for x in args.only.split(",")} if args.only else None
    rows = []
    for qid, q, lang, ck, system in QUESTIONS:
        if only and qid not in only:
            continue
        chart = cs[ck]
        qt = classify_question(q)
        t0 = time.monotonic()
        try:
            res = await resp.answer(ChatInput(chart_data=chart, question=q, history=[], language=lang,
                                              astrology_system=system, display_name="Test", today=TODAY))
        except LLMError as exc:
            rows.append({"id": qid, "q": q, "lang": lang, "chart": ck, "error": type(exc).__name__,
                         "latency_ms": int((time.monotonic() - t0) * 1000)})
            print(f"[{qid:>2}] ERROR {type(exc).__name__} {q[:60]}")
            await asyncio.sleep(args.pause)
            continue
        facts = build_chart_facts(chart, system=system, today=TODAY)
        m = metrics_for(res, qt, lang, chart, facts)
        rows.append({"id": qid, "q": q, "lang": lang, "chart": ck, "answer": res["answer"], "sources": res.get("sources"), **m})
        print(f"[{qid:>2}] {m['kind']:8} {m['outcome']:9} words={m['words']:>3} first={m['concept_first']!s:5} "
              f"chartrefs={m['chart_ref_sentences']} kb={m['kb_cited']}/{m['kb_provided']} grounded={m['grounded']} "
              f"{m['latency_ms']/1000:.1f}s | {m['first_sentence'][:70]}")
        await asyncio.sleep(args.pause)
    out = Path(args.out) / f"sweep-{args.label}.json"
    out.write_text(json.dumps({"summary": summarise(rows), "rows": rows, "cost_usd": round(sum(u.cost_usd for u in sink.records), 4)},
                              indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summarise(rows), indent=1))
    await engine.dispose()
    return 0


def summarise(rows: list[dict]) -> dict:
    ok = [r for r in rows if "error" not in r]
    gen = [r for r in ok if r["kind"] == "general"]
    lat = sorted(r["latency_ms"] for r in rows)

    def pct(p):
        return lat[min(len(lat) - 1, int(len(lat) * p))] / 1000 if lat else None

    def frac(xs, pred):
        return f"{sum(1 for x in xs if pred(x))}/{len(xs)}"

    return {
        "n": len(rows), "errors": len(rows) - len(ok),
        "general_answer_first": frac(gen, lambda r: r["concept_first"]),
        "general_chart_led": frac(gen, lambda r: r["chart_led"]),
        "boilerplate_openings": sum(1 for r in ok if any("birth chart" in f for f in r["shape_flags"])),
        "general_chart_ref_sentences_mean": round(statistics.mean([r["chart_ref_sentences"] for r in gen]), 2) if gen else None,
        "general_words_mean": round(statistics.mean([r["words"] for r in gen]), 0) if gen else None,
        "words_mean": round(statistics.mean([r["words"] for r in ok]), 0) if ok else None,
        "shape_flagged": frac(ok, lambda r: bool(r["shape_flags"])),
        "grounded": frac(ok, lambda r: r["grounded"]),
        "language_ok": frac(ok, lambda r: r["language_ok"]),
        "kb_cited_any": frac(ok, lambda r: r["kb_cited"] > 0),
        "kb_provided_any": frac(ok, lambda r: r["kb_provided"] > 0),
        "first_draft_flagged": frac(ok, lambda r: bool(r["first_draft_flags"])),
        "outcome_ok": frac(ok, lambda r: r["outcome"] == "ok"),
        "latency_p50_s": round(statistics.median(lat) / 1000, 1) if lat else None, "latency_p95_s": round(pct(0.95), 1) if lat else None,
    }


def compare(a: str, b: str) -> None:
    ja, jb = json.loads(Path(a).read_text()), json.loads(Path(b).read_text())
    for k in ja["summary"]:
        print(f"{k:<34} {str(ja['summary'][k]):>12} -> {str(jb['summary'].get(k)):>12}")
    by = {r["id"]: r for r in jb["rows"]}
    for r in ja["rows"]:
        r2 = by.get(r["id"])
        if not r2 or "answer" not in r or "answer" not in r2:
            continue
        print(f"\n=== [{r['id']}] {r['q']}\n--- BEFORE ({r['words']}w, first={r['concept_first']}):\n{r['answer']}\n--- AFTER ({r2['words']}w, first={r2['concept_first']}):\n{r2['answer']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="run")
    ap.add_argument("--only", default="")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "reports"))
    ap.add_argument("--pause", type=float, default=1.0)
    ap.add_argument("--compare", nargs=2)
    args = ap.parse_args()
    if args.compare:
        compare(*args.compare)
        return 0
    return asyncio.run(run(args))


if __name__ == "__main__":
    raise SystemExit(main())
