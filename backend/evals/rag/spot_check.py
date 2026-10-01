"""10-answer live spot check on questions the researched files cover (dev index, read-only).

    python -m evals.rag.spot_check [--label x]

Per answer: outcome, validator flags, KB notes cited (with confidence), whether a hedge was required and present,
claim-checker violations in the FINAL text, leaked raw tokens, and a short excerpt. Needs a Gemini key."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

QUESTIONS = [
    ("What does Mars mahadasha with Venus antardasha mean for me?", "english"),
    ("Is my Bhakoot dosha cancelled?", "english"),
    ("What is today's tithi and is it good for starting something new?", "english"),
    ("What is the result of the Moon in the 7th house?", "english"),
    ("What is Yogini dasha and should I follow it?", "english"),
    ("How is Rahu Kaal calculated and should I avoid it?", "english"),
    ("मेरी साढ़ेसाती कैसी रहेगी और क्या सावधानी रखूं?", "hindi"),
    ("Moon se Saturn ka gochar kab shubh mana jata hai?", "hinglish"),
    ("What happens when the 7th lord sits in the 12th house?", "english"),
    ("Which remedies are traditionally suggested for a weak Saturn?", "english"),
]
HEDGE = re.compile(r"some (?:sources|traditions|schools|astrologers)|traditions? (?:differ|vary)|schools? (?:differ|vary)|"
                   r"sources? (?:differ|disagree)|according to (?:some|one)|varies|कुछ (?:स्रोत|परंपरा)|मतभेद", re.I)


async def main_async(label: str) -> int:
    from dotenv import dotenv_values
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.llm.compat_checks import leaked_tokens
    from app.llm.config import LLMSettings
    from app.llm.errors import LLMError
    from app.llm.facts import ChartIndex, build_chart_facts
    from app.llm.providers import build_providers
    from app.llm.responder import ChatInput, ChatResponder
    from app.llm.router import LLMRouter
    from app.llm.safety import scan_output
    from app.llm.usage import MemoryUsageSink
    from app.llm.validators import check_claims
    from app.rag import PgVectorStore, Retriever
    from app.rag.embeddings import make_embedder

    s = LLMSettings()
    provs = build_providers(s)
    if not provs:
        print("no provider keys; skipping")
        return 0
    chart = json.loads((Path(__file__).resolve().parents[1] / "fixtures" / "real_charts.json").read_text())["delhi_1994"]
    engine = create_async_engine(dotenv_values(Path(__file__).resolve().parents[2] / ".env")["DATABASE_URL"], pool_size=2)
    retriever = Retriever(PgVectorStore(engine), make_embedder("bge-small", threads=1))
    sink = MemoryUsageSink()
    resp = ChatResponder(LLMRouter(s, provs, usage_sink=sink), retriever=retriever)
    rows = []
    for q, lang in QUESTIONS:
        try:
            res = await resp.answer(ChatInput(chart_data=chart, question=q, history=[], language=lang,
                                              astrology_system="vedic", display_name="Test"))
        except LLMError as exc:
            rows.append({"q": q, "error": type(exc).__name__})
            print("ERROR", q[:50], type(exc).__name__)
            continue
        md, ans = res["metadata"], res["answer"]
        facts = build_chart_facts(chart, system="vedic")
        viol = [v.detail for v in check_claims(ans, ChartIndex.from_chart(chart), facts) if v.kind in ("claim", "time_unknown")]
        cited = md.get("kb_cited", [])
        needs_hedge = any(x in cited for x in md.get("kb_hedge_cited", []))
        row = {"q": q, "lang": lang, "outcome": md["outcome"], "model": md["model"], "first_draft_flags": md.get("first_draft_flags"),
               "kb_cited": len(cited), "kb_provided": len(md.get("kb_chunk_ids", [])), "factor_cites": len(res["citations"]),
               "grounded": not viol, "citation_valid": "citation" not in (md.get("first_draft_flags") or []),
               "hedge_flag_in_context": bool(md.get("kb_hedge_provided")), "hedge_present": bool(HEDGE.search(ans)),
               "safety_hits": [h.cls for h in scan_output(ans)], "leaked_tokens": leaked_tokens(ans),
               "mentions_unverified": "unverified" in ans.lower(), "excerpt": ans[:200].replace("\n", " ")}
        rows.append(row)
        print(f"{q[:52]:<52} {row['outcome']:<9} kb {row['kb_cited']}/{row['kb_provided']} grounded={row['grounded']} "
              f"hedge={row['hedge_present']} flags={row['first_draft_flags']}")
    ok = [r for r in rows if "error" not in r]
    summary = {"n": len(rows), "errors": len(rows) - len(ok), "grounded": f"{sum(r['grounded'] for r in ok)}/{len(ok)}",
               "citation_valid": f"{sum(r['citation_valid'] for r in ok)}/{len(ok)}",
               "cited_a_kb_note": f"{sum(r['kb_cited'] > 0 for r in ok)}/{len(ok)}",
               "safety_hits": sum(bool(r["safety_hits"]) for r in ok), "leaked_tokens": sum(bool(r["leaked_tokens"]) for r in ok),
               "states_unverified_marker": sum(r["mentions_unverified"] for r in ok),
               "cost_usd": round(sum(u.cost_usd for u in sink.records), 4)}
    (Path(__file__).resolve().parent / "reports" / f"spot-{label}.json").write_text(
        json.dumps({"summary": summary, "answers": rows}, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    await engine.dispose()
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="run")
    return asyncio.run(main_async(ap.parse_args().label))


if __name__ == "__main__":
    raise SystemExit(main())
