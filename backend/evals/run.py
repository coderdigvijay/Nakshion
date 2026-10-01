"""Eval harness skeleton (docs/llm-integration.md §9).

    python -m evals.run --task chat --prompt v1 --model gemini-3.8-flash [--judge] [--limit N]
    python -m evals.run --task chat --offline          # FakeProvider: plumbing check, no network, no cost

Runs every case in evals/cases.jsonl against synthetic charts (evals/fixtures/charts.json),
computes the automated metrics, optionally scores with the LLM judge, evaluates the gates in
evals/rubric.yaml and writes evals/reports/<date>-<task>-<prompt>-<model>.json.
Live runs need GEMINI_API_KEY / ANTHROPIC_API_KEY. Eval data is synthetic only (§9.1).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import statistics
import sys
from datetime import date
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))  # backend/ on the path for `app.*`

from app.llm.config import LLMSettings  # noqa: E402
from app.llm.errors import LLMError  # noqa: E402
from app.llm.facts import ChartIndex, build_chart_facts  # noqa: E402
from app.llm.prompts import get_registry  # noqa: E402
from app.llm.providers import build_providers  # noqa: E402
from app.llm.providers.fake import FakeProvider  # noqa: E402
from app.llm.responder import ChatInput, ChatResponder  # noqa: E402
from app.llm.router import LLMRouter  # noqa: E402
from app.llm.safety import scan_output  # noqa: E402
from app.llm.schemas import JudgeVerdict, provider_schema  # noqa: E402
from app.llm.types import LLMRequest  # noqa: E402
from app.llm.usage import MemoryUsageSink  # noqa: E402
from app.llm.validators import check_claims, check_language  # noqa: E402

_FACT_LINE = re.compile(r"^\[([A-Z][A-Z0-9_.]+)\] (.+?) \(weight", re.M)


def offline_answer(req: LLMRequest, model: str) -> str:
    """Deterministic grounded answer for --offline: cites the first two factors."""
    facts = [(i, lbl) for i, lbl in _FACT_LINE.findall(req.context_blocks[0]) if not i.startswith("META")][:2]
    hindi = "Devanagari" in req.system
    if hindi:
        body = "आपकी कुंडली के अनुसार यह समय धैर्य और संतुलन का है। " * 12
    else:
        labels = " and ".join(lbl for _, lbl in facts) or "your chart"
        body = (f"Looking at {labels.lower()}, this period tends to favour steady effort and honest reflection. "
                + "Notice what feels supportive, keep a simple routine, and give important choices a little time. " * 9)
    return json.dumps({"answer": body.strip(), "citations": [i for i, _ in facts], "topic": "general",
                       "follow_ups": ["What supports me this month?"], "confidence": "medium",
                       "needs_birth_time": False})


def load_cases(limit: int | None) -> tuple[list[dict], dict]:
    cases = [json.loads(line) for line in (HERE / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    charts = json.loads((HERE / "fixtures" / "charts.json").read_text(encoding="utf-8"))
    return cases[:limit] if limit else cases, charts


def score_case(case: dict, res: dict, chart: dict, rubric: dict) -> dict:
    md = res.get("metadata", {})
    answer = res.get("answer", "")
    exp = case.get("expect", {})
    facts = build_chart_facts(chart, system=case.get("system", "both"))
    final_v = [] if md.get("generated_by") != "llm" else check_claims(answer, ChartIndex.from_chart(chart), facts)
    words = len(answer.split())
    lw = rubric["length_words"]
    row = {
        "id": case["id"], "archetype": case["archetype"], "generated_by": md.get("generated_by"),
        "outcome": md.get("outcome"), "first_draft_grounding_violation":
            any(f in ("claim", "time_unknown") for f in md.get("first_draft_flags", [])),
        "final_grounding_violations": [v.detail for v in final_v],
        "citations_valid": all(c["factor_id"] in facts.factor_ids for c in res.get("citations", [])),
        "language_ok": not check_language(answer, case["language"]) if md.get("generated_by") == "llm" else True,
        "length_ok": md.get("generated_by") != "llm" or (lw["min"] <= words <= lw["max"] and "<" not in answer),
        "latency_ms": md.get("latency_ms"), "words": words,
    }
    handled = True
    if "static" in exp:
        handled = md.get("safety") == exp["static"]
    for cls in exp.get("forbidden", []):
        if any(h.cls == cls for h in scan_output(answer)):
            handled = False
    if exp.get("no_time_unknown_violations"):
        handled = handled and not any(v.kind == "time_unknown" for v in final_v)
    if exp.get("must_mention_any"):
        handled = handled and any(w.lower() in answer.lower() for w in exp["must_mention_any"])
    row["handled"] = handled
    if exp.get("corrects_premise"):
        row["premise_corrected"] = handled
    return row


async def judge(router: LLMRouter, case: dict, res: dict, chart: dict) -> dict | None:
    reg = get_registry()
    p = reg.render("judge")
    facts = build_chart_facts(chart, system=case.get("system", "both"))
    req = LLMRequest(task="judge", system=p.text, context_blocks=(facts.render(),),
                     messages=({"role": "user", "content": f"QUESTION:\n{case['question']}\n\nANSWER:\n{res['answer']}"},),
                     max_output_tokens=800, response_schema=provider_schema(JudgeVerdict), temperature=0.0,
                     timeout_s=60, prompt_id=p.prompt_id)
    try:
        r = await router.generate(req, schema=JudgeVerdict, deadline_s=120)
        return r.parsed
    except LLMError as exc:
        return {"error": type(exc).__name__}


def gates(rows: list[dict], judged: list[dict], rubric: dict, usage) -> dict:
    g = rubric["gates"]
    n = len(rows) or 1
    llm_rows = [r for r in rows if r["generated_by"] == "llm"] or rows
    adv = [r for r in rows if r["archetype"].startswith("adversarial")]
    prem = [r for r in rows if "premise_corrected" in r]
    lat = sorted(r["latency_ms"] or 0 for r in rows)
    m = {
        "first_draft_grounding": sum(r["first_draft_grounding_violation"] for r in rows) / n,
        "final_grounding": sum(bool(r["final_grounding_violations"]) for r in rows) / n,
        "citation_validity": sum(r["citations_valid"] for r in rows) / n,
        "premise_correction": (sum(r["premise_corrected"] for r in prem) / len(prem)) if prem else 1.0,
        "adversarial_handled": (sum(r["handled"] for r in adv) / len(adv)) if adv else 1.0,
        "all_handled": sum(r["handled"] for r in rows) / n,
        "language_compliance": sum(r["language_ok"] for r in llm_rows) / len(llm_rows),
        "length_format": sum(r["length_ok"] for r in llm_rows) / len(llm_rows),
        "p95_latency_s": (lat[int(0.95 * (len(lat) - 1))] / 1000) if lat else 0.0,
        "cost_usd_total": round(sum(u.cost_usd for u in usage.records), 6),
    }
    checks = {
        "first_draft_grounding": m["first_draft_grounding"] <= g["first_draft_grounding_max"],
        "final_grounding": m["final_grounding"] <= g["final_grounding_max"],
        "citation_validity": m["citation_validity"] >= g["citation_validity_min"],
        "premise_correction": m["premise_correction"] >= g["premise_correction_min"],
        "adversarial_handled": m["adversarial_handled"] >= g["adversarial_handled_min"],
        "language_compliance": m["language_compliance"] >= g["language_compliance_min"],
        "length_format": m["length_format"] >= g["length_format_min"],
        "latency": m["p95_latency_s"] <= g["chat_p95_latency_s_max"],
    }
    if judged:
        for crit in rubric["criteria"]:
            scores = [s["score"] for j in judged if "scores" in j for s in j["scores"] if s["criterion"] == crit]
            if scores:
                m[f"judge_{crit}_mean"] = statistics.mean(scores)
                low = sum(1 for s in scores if s <= 2) / len(scores)
                checks[f"judge_{crit}"] = m[f"judge_{crit}_mean"] >= g["judge_mean_min"] and low <= g["judge_low_share_max"]
    return {"metrics": m, "gates": checks, "passed": all(checks.values())}


async def main_async(args) -> int:
    rubric = yaml.safe_load((HERE / "rubric.yaml").read_text(encoding="utf-8"))
    reg = get_registry()
    args.prompt = args.prompt or reg.active_version(args.task)
    if args.prompt != reg.active_version(args.task):
        print(f"registry active {args.task}@{reg.active_version(args.task)} != --prompt {args.prompt}; "
              "bump registry.yaml active before evaluating a new version", file=sys.stderr)
        return 2
    usage = MemoryUsageSink()
    if args.offline:
        settings = LLMSettings(_env_file=None, LLM_MODEL_CHAT="fake-chat", LLM_FALLBACK_CHAT="")
        providers = {"fake": FakeProvider(default=offline_answer)}
    else:
        settings = LLMSettings(**({"LLM_MODEL_CHAT": args.model, "LLM_FALLBACK_CHAT": ""} if args.model else {}))
        providers = build_providers(settings)
    router = LLMRouter(settings, providers, usage_sink=usage)
    responder = ChatResponder(router)
    cases, charts = load_cases(args.limit)
    rows, judged = [], []
    for case in cases:
        chart = charts[case["chart"]]
        inp = ChatInput(chart_data=chart, question=case["question"], history=[], language=case["language"],
                        astrology_system=case.get("system", "both"), display_name="Test User")
        try:
            res = await responder.answer(inp)
        except LLMError as exc:
            res = {"answer": "", "citations": [], "metadata": {"generated_by": "error", "outcome": type(exc).__name__}}
        row = score_case(case, res, chart, rubric)
        rows.append(row)
        if args.judge and res["metadata"].get("generated_by") == "llm":
            j = await judge(router, case, res, chart)
            if j:
                judged.append(j)
                row["judge"] = j
        print(f"{row['id']:<28} handled={row['handled']} outcome={row['outcome']}")
    summary = gates(rows, judged, rubric, usage)
    out = HERE / "reports" / f"{date.today().isoformat()}-{args.task}-{args.prompt}-{'offline' if args.offline else (args.model or settings.model_chat)}.json"
    out.write_text(json.dumps({"task": args.task, "prompt": args.prompt, "model": args.model, "offline": args.offline,
                               "summary": summary, "cases": rows}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    print(f"report: {out}")
    return 0 if summary["passed"] else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="chat", choices=["chat"])
    ap.add_argument("--prompt", default=None)
    ap.add_argument("--model", default=None)
    ap.add_argument("--offline", action="store_true")
    ap.add_argument("--judge", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    return asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
