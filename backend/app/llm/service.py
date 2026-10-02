"""Facade consumed by app/services/ai.py (backend-elite).

    configure(settings=None, *, providers=None, retriever=None, usage_sink=None, redis=None)
    await generate_chat_reply(*, chart_data, question, history, language, user_id_hash, astrology_system, **opt)
    async for ev in stream_chat_reply(...same...):  ("delta", str) | ("replace", str) | ("done", dict)
    await generate_daily_sign(sign, date, transit_data, **opt)
    await generate_compat_narrative(report, relationship_type, **opt)

`configure()` is optional: the first call lazily builds everything from the environment
(LLMSettings). Tests call `configure(providers={"fake": FakeProvider(...)}, settings=...)`.
Failures raise LLMUnavailable (class name contains "Unavailable") -> HTTP 503 AI_UNAVAILABLE.
Per-user chat quotas: `get_service().quota.reserve/release` (call before / on failure).
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from datetime import date as Date
from typing import Any, AsyncIterator

from app.llm.budget import BudgetGuard, MemoryCounter, RedisCounter, UserQuota
from app.llm.builder import render_fact_lines, render_notes
from app.llm.config import LLMSettings, provider_for_model
from app.llm.errors import LLMError, LLMUnavailable
from app.llm.facts import ChartFacts, ChartIndex, FactorView
from app.llm.lexicon import canon_planet, canon_sign
from app.llm.prompts import LANGUAGE_INSTRUCTIONS, get_registry
from app.llm.providers import build_providers
from app.llm.providers.base import LLMProvider
from app.llm.responder import ChatInput, ChatResponder, Retriever
from app.llm.router import LLMRouter
from app.llm.safety import scan_output
from app.llm.schemas import CompatNarrative, DailySign, PersonalReadingText, provider_schema
from app.llm.types import LLMRequest
from app.llm.usage import LoggingUsageSink, UsageSink
from app.llm.validators import check_claims

log = logging.getLogger("nakshion.llm.service")


@dataclass
class AIService:
    settings: LLMSettings
    router: LLMRouter
    responder: ChatResponder
    budget: BudgetGuard
    quota: UserQuota
    retriever: Retriever | None


_service: AIService | None = None


def configure(
    settings: LLMSettings | None = None,
    *,
    providers: dict[str, LLMProvider] | None = None,
    retriever: Retriever | None = None,
    usage_sink: UsageSink | None = None,
    redis: Any = None,
) -> AIService:
    global _service
    s = settings or LLMSettings()
    counter = RedisCounter(redis) if redis is not None else MemoryCounter()
    budget = BudgetGuard(s, counter)
    provs = providers if providers is not None else build_providers(s)
    if not provs:
        log.error("llm_no_provider_configured: set GEMINI_API_KEY (or GEMINI_API_KEY1..5) and/or ANTHROPIC_API_KEY; "
                  "every AI call will raise LLMUnavailable")
    else:
        missing = sorted({m for t in ("chat", "daily_sign", "premium_report") for m in s.chain_for(t)
                          if provider_for_model(m) not in provs})
        if missing:
            log.warning("llm_models_without_provider_skipped", extra={"models": missing})
    router = LLMRouter(s, provs, usage_sink=usage_sink or LoggingUsageSink(), budget=budget)
    if retriever is None:
        log.info("no retriever configured: answers use chart facts only")
    _service = AIService(s, router, ChatResponder(router, retriever=retriever, budget=budget),
                         budget, UserQuota(s, counter), retriever)
    return _service


def get_service() -> AIService:
    return _service or configure()


def reset() -> None:
    global _service
    _service = None


# ----------------------------------------------------------------------------- chat


def _chat_input(chart_data, question, history, language, user_id_hash, astrology_system, opt) -> ChatInput:
    return ChatInput(chart_data=chart_data, question=question, history=list(history or []),
                     language=language or "english", astrology_system=astrology_system or "both",
                     user_id_hash=user_id_hash, **opt)


async def generate_chat_reply(*, chart_data: dict, question: str, history: list[dict], language: str = "english",
                              user_id_hash: str | None = None, astrology_system: str = "both", **opt) -> dict:
    """-> {answer, citations: [{factor_id, label}], tokens_used, metadata}.
    Optional: user_id, tier, factors (engine select_factors output), display_name, is_minor, today, request_id."""
    svc = get_service()
    return await svc.responder.answer(_chat_input(chart_data, question, history, language, user_id_hash,
                                                  astrology_system, opt))


async def stream_chat_reply(*, chart_data: dict, question: str, history: list[dict], language: str = "english",
                            user_id_hash: str | None = None, astrology_system: str = "both",
                            **opt) -> AsyncIterator[tuple[str, Any]]:
    svc = get_service()
    async for ev in svc.responder.stream(_chat_input(chart_data, question, history, language, user_id_hash,
                                                     astrology_system, opt)):
        yield ev


# ----------------------------------------------------------------------------- shared helpers


async def _notes(svc: AIService, keys: list[str], system: str, topic: str) -> list[Any]:
    if svc.retriever is None:
        return []
    try:
        return await svc.retriever.retrieve(kb_keys=keys, question="", system=system, topic=topic, language="english")
    except Exception:  # noqa: BLE001
        log.exception("retrieval failed; continuing without notes")
        return []


def _sky_items(transit_data: dict) -> list[FactorView]:
    """Engine daily-sky data -> fact lines. Prefers engine Factors; else formats planets."""
    if transit_data.get("factors"):
        return [FactorView.coerce(f) for f in transit_data["factors"]]
    out = []
    for p in transit_data.get("planets", []) or []:
        name = p.get("name") or p.get("planet")
        sign = p.get("sign")
        if not (name and sign):
            continue
        extra = ", retrograde" if p.get("retrograde") else ""
        if p.get("house"):
            extra += f", solar house {p['house']}"
        out.append(FactorView(id=f"S.{name.upper().replace(' ', '_')}.SIGN.{sign.upper()}", kind="transit",
                              label=f"{name} in {sign}{extra}", kb_keys=(f"{name.lower()} transit",)))
    if transit_data.get("moon_phase"):
        out.append(FactorView(id="S.MOON.PHASE", kind="transit", label=f"Moon phase: {transit_data['moon_phase']}"))
    return out


def _template_daily(sign: str, items: list[FactorView]) -> dict:
    top = "; ".join(f.label for f in items[:3]) or "a quiet sky"
    return {
        "general": f"Today's sky for {sign}: {top}. A good day to move steadily and notice what feels supportive.",
        "love": "Gentle, honest conversations tend to go further than grand gestures today.",
        "career": "Focus on one clear priority and give it your full attention.",
        "wellness": "Keep a steady routine: rest, water, and a short walk can help.",
        "citations": [f.id for f in items[:3]],
    }


async def _structured(svc: AIService, req: LLMRequest, schema, check, *, deadline_s: float | None = None,
                      normalize=None, salvage=None) -> tuple[Any, Any]:
    """generate -> content check -> one repair -> raise. `check(obj) -> list[str]` problems.

    deadline_s   overall wall-clock budget for the first call plus the repair (default: twice the attempt timeout).
                 The repair is skipped when too little is left.
    normalize    obj -> obj, applied before checking (soft fields: citations are metadata and are repaired in code)
    salvage      (obj, problems) -> obj | None, tried when the repair fails: drop only what is wrong instead of
                 discarding the whole answer. Must return a fully valid object or None."""
    from app.llm.builder import repair_messages

    start = time.monotonic()
    total = deadline_s if deadline_s else max(req.timeout_s * 2, 20)
    res = await svc.router.generate(req, schema=schema, deadline_s=total)
    obj = schema.model_validate(res.parsed)
    if normalize:
        obj = normalize(obj)
    problems = check(obj)
    if not problems:
        return obj, res
    left = total - (time.monotonic() - start)
    if left > 4.0:
        try:
            res2 = await svc.router.generate(repair_messages(req, res.text, problems), schema=schema,
                                             models=[res.model], deadline_s=left)
        except LLMError:
            if salvage is None:
                raise
            res2 = None
        if res2 is not None:
            obj2 = schema.model_validate(res2.parsed)
            if normalize:
                obj2 = normalize(obj2)
            problems2 = check(obj2)
            if not problems2:
                return obj2, res2
            obj, res, problems = obj2, res2, problems2
    if salvage is not None:
        fixed = salvage(obj, problems)
        if fixed is not None and not check(fixed):
            return fixed, res
    raise LLMUnavailable("structured output failed content checks after repair")


# ----------------------------------------------------------------------------- daily sign


async def generate_daily_sign(sign: str, date: Date | str, transit_data: dict, *, system: str = "tropical",
                              language: str = "english") -> dict:
    """-> {general, love, career, wellness, citations, generated_by, metadata}. Falls back to a
    template (generated_by="template") when the LLM is unavailable or the budget guard engages."""
    svc = get_service()
    canon = canon_sign(sign) or sign
    items = _sky_items(transit_data)
    try:
        await svc.budget.admit("daily_sign", "free")
        reg = get_registry()
        sys_p = reg.render("daily_sign", system_label="tropical zodiac" if system == "tropical" else "sidereal zodiac",
                           language_instruction=LANGUAGE_INSTRUCTIONS.get(language, "English."))
        lim = reg.reg["limits"]["daily_sign"]
        keys = ["daily guidance"] + [k for f in items[:4] for k in f.kb_keys]
        notes = await _notes(svc, keys, "western" if system == "tropical" else "vedic", "timing")
        ctx = [render_fact_lines(f"SKY FACTS for {canon} on {date} (authoritative; computed by the engine)",
                                 [(f.id, f.label) for f in items])]
        if notes:
            ctx.append(render_notes(notes)[0])
        req = LLMRequest(task="daily_sign", system=sys_p.text, context_blocks=tuple(ctx),
                         messages=({"role": "user", "content": f"Write today's horoscope for {canon}."},),
                         max_output_tokens=lim["max_output_tokens"], response_schema=provider_schema(DailySign),
                         temperature=lim["temperature"], timeout_s=lim["timeout_s"], prompt_id=sys_p.prompt_id)
        ids = {f.id for f in items}
        idx = ChartIndex(approximate_time=False)
        for f in items:
            parts = f.label.split(" in ")
            if len(parts) == 2 and canon_planet(parts[0]):
                idx.western[canon_planet(parts[0])] = (canon_sign(parts[1].split(",")[0]), None, "retrograde" in f.label)
        facts = ChartFacts("", "western", False, "solar", "", "", str(date), (), tuple(items))

        def check(o: DailySign) -> list[str]:
            text = " ".join([o.general, o.love, o.career, o.wellness])
            probs = [f"unknown fact id {c}" for c in o.citations if c not in ids]
            probs += [f"safety:{h.cls}" for h in scan_output(text)]
            probs += [f"{v.kind}: {v.detail}" for v in check_claims(text, idx, facts, transit_exempt=False) if v.kind == "claim"]
            return probs

        obj, res = await _structured(svc, req, DailySign, check)
        out = obj.model_dump()
        out["generated_by"] = "llm"
        out["metadata"] = {"prompt_version": sys_p.prompt_id, "provider": res.provider, "model": res.model,
                           "kb_chunk_ids": [n.chunk_id for n in notes], "tokens_used": res.input_tokens + res.output_tokens}
        return out
    except LLMError as exc:
        log.warning("daily_sign falling back to template", extra={"reason": type(exc).__name__})
        out = _template_daily(canon, items)
        out["generated_by"] = "template"
        out["metadata"] = {"prompt_version": "template@v1"}
        return out


# ----------------------------------------------------------------------------- compatibility


def _aspect_key(a: dict) -> str:
    kind = a.get("type") or a.get("aspect") or "?"
    return a.get("key") or f"{a.get('planet1', '?')}-{kind}-{a.get('planet2', '?')}".lower().replace(" ", "_")


def compat_fact_lines(report: dict) -> tuple[list[tuple[str, str]], list[dict]]:
    """REPORT FACTS from the engine's compute_compatibility() shape. Scores, band, Ashtakoota verdict and dosha
    flags are authoritative and listed first so the narrative's tone can be held to them."""
    from app.llm.compat_checks import BAND_TEXT, band, flagged_doshas, normalize_report

    report = normalize_report(report)
    lines: list[tuple[str, str]] = []
    overall = report.get("overall_score")
    if overall is not None:
        lines.append(("SCORE.OVERALL", f"Overall {overall}/10 (engine-computed). Band: {BAND_TEXT[band(overall)]}"))
    bd = report.get("score_breakdown") or {}
    if bd.get("western_overall") is not None:
        lines.append(("SCORE.WESTERN", f"Western synastry {bd['western_overall']}/10"))
    ak = report.get("ashtakoota") or {}
    if ak:
        lines.append(("ASHTAKOOTA", f"Ashtakoota (Guna Milan) {ak.get('total')}/36, verdict: {str(ak.get('verdict')).replace('_', ' ')}"
                      + (" (approximate: birth time unknown)" if ak.get("approximate") else "")))
        for d in flagged_doshas(report):
            lines.append((f"DOSHA.{d.upper()}", f"{d.title()} dosha is present (traditionally linked with friction in this "
                                                 f"area; traditional cancellations exist)"))
        for kt in ak.get("kootas", []) or []:
            lines.append((f"KOOTA.{kt.get('name')}", f"{kt.get('name')}: {kt.get('score')}/{kt.get('max')}"))
    mg = report.get("manglik") or {}
    p1, p2 = (mg.get("person1") or {}).get("present"), (mg.get("person2") or {}).get("present")
    if p1 is not None and p1 != p2:
        lines.append(("MANGLIK", "Manglik status differs between the two charts (traditional cancellations exist)"))
    for k, v in (report.get("categories") or {}).items():
        score = v.get("score") if isinstance(v, dict) else v
        lines.append((f"CAT.{k}", f"category key '{k}': score {score}/10"))
    aspects = (report.get("synastry_aspects") or report.get("aspects") or report.get("top_aspects") or [])[:15]
    for a in aspects:
        orb = f", orb {a['orb']}" if a.get("orb") is not None else ""
        lines.append((f"ASP.{_aspect_key(a)}", f"aspect_key '{_aspect_key(a)}': {a.get('planet1')} "
                                               f"{a.get('type') or a.get('aspect')} {a.get('planet2')}{orb}"))
    for tag, seeds in (("STRENGTH", report.get("strengths_seeds")), ("CHALLENGE", report.get("challenges_seeds"))):
        for a in (seeds or [])[:3]:
            lines.append((f"SEED.{tag}.{_aspect_key(a)}", f"{tag.lower()} seed: {a.get('planet1')} "
                                                           f"{a.get('type') or a.get('aspect')} {a.get('planet2')}"))
    return lines, aspects


async def generate_compat_narrative(report: dict, relationship_type: str, *, language: str = "english") -> dict:
    """-> {summary, categories {key: {summary}}, aspect_interpretations [{aspect_key, text}],
    strengths[3], challenges[3], generated_by, metadata}. Input: the engine's compute_compatibility() dict
    (overall_score, score_breakdown, categories, synastry_aspects, strengths/challenges_seeds, ashtakoota, manglik).
    Scores stay in the engine's report; the narrative's tone is validated against the score band, the
    Ashtakoota verdict and the dosha flags. Raises LLMUnavailable when generation fails (caller persists the
    report without narrative or uses its template)."""
    from app.llm.compat_checks import consistency_problems, normalize_report

    report = normalize_report(report)
    svc = get_service()
    await svc.budget.admit("compat", "free")
    reg = get_registry()
    sys_p = reg.render("compat", relationship_type=relationship_type,
                       language_instruction=LANGUAGE_INSTRUCTIONS.get(language, "English."))
    lim = reg.reg["limits"]["compat"]
    cats: dict = report.get("categories") or {}
    lines, aspects = compat_fact_lines(report)
    notes = await _notes(svc, ["synastry", "compatibility"] + [f"{a.get('planet1')} {a.get('type') or a.get('aspect')} "
                                                               f"{a.get('planet2')}".lower() for a in aspects[:4]],
                         "both", "compatibility")
    ctx = [render_fact_lines("REPORT FACTS (authoritative; computed by the engine)", lines)]
    if notes:
        ctx.append(render_notes(notes)[0])
    req = LLMRequest(task="compat", system=sys_p.text, context_blocks=tuple(ctx),
                     messages=({"role": "user", "content": "Write the compatibility narrative."},),
                     max_output_tokens=lim["max_output_tokens"], response_schema=provider_schema(CompatNarrative),
                     temperature=lim["temperature"], timeout_s=lim["timeout_s"], prompt_id=sys_p.prompt_id)
    cat_keys, asp_keys = set(cats), {_aspect_key(a) for a in aspects}

    def check(o: CompatNarrative) -> list[str]:
        lists = " ".join([*o.strengths, *o.challenges, *[a.text for a in o.aspect_interpretations],
                          *[c.summary for c in o.categories]])
        probs = [f"safety:{h.cls}" for h in scan_output(" ".join([o.summary, lists]))]
        probs += [f"unknown category key {c.key}" for c in o.categories if c.key not in cat_keys]
        probs += [f"unknown aspect_key {a.aspect_key}" for a in o.aspect_interpretations if a.aspect_key not in asp_keys]
        probs += consistency_problems(o.summary, lists, report, challenges_text=" ".join(o.challenges))
        return probs

    obj, res = await _structured(svc, req, CompatNarrative, check)
    from app.llm.compat_checks import plain_words as pw

    return {
        "summary": pw(obj.summary),
        "categories": {c.key: {"summary": pw(c.summary)} for c in obj.categories},
        "aspect_interpretations": [{**a.model_dump(), "text": pw(a.text)} for a in obj.aspect_interpretations],
        "strengths": [pw(x) for x in obj.strengths],
        "challenges": [pw(x) for x in obj.challenges],
        "generated_by": "llm",
        "metadata": {"prompt_version": sys_p.prompt_id, "provider": res.provider, "model": res.model,
                     "kb_chunk_ids": [n.chunk_id for n in notes], "tokens_used": res.input_tokens + res.output_tokens},
    }


# ----------------------------------------------------------------------------- personal daily (R3)

PERSONAL_AREAS = ("love", "career", "wellness", "money")

# Time budget (BUG-025). On the free Render CPU the whole path (retrieval + model + one repair) used to run under a
# 20 s outer timeout with a 10 s retrieval timeout inside it, so a slow embed left the model almost no time and the
# card fell back to the template. Now: retrieval is capped at 2.5 s and skipped on timeout, each model attempt gets
# 12 s, and the whole call stops at DAILY_BUDGET_S (callers wrap it in a timeout of at least budget + 3 s).
DAILY_BUDGET_S = 32.0
DAILY_RAG_CAP_S = 2.5


async def _notes_capped(svc: AIService, keys: list[str], system: str, topic: str, cap_s: float) -> list[Any]:
    try:
        return await asyncio.wait_for(_notes(svc, keys, system, topic), cap_s)
    except (TimeoutError, asyncio.TimeoutError):
        log.warning("daily retrieval exceeded its cap; continuing without notes", extra={"cap_s": cap_s})
        return []


def _kf(f: Any) -> tuple[str, str, float]:
    get = f.get if isinstance(f, dict) else (lambda k, d=None: getattr(f, k, d))
    return str(get("factor_id") or get("id") or ""), str(get("label") or ""), float(get("weight") or 0.0)


async def generate_daily_personal(facts: dict, *, language: str = "english", system: str | None = None,
                                  user_id_hash: str | None = None, budget_s: float | None = None) -> dict:
    """R3 narrative text. `facts` is the engine's `personal_day` output:

        {areas: {love|career|wellness|money: {score 1..5}}, key_factors: [{factor_id, label, weight}],
         timing?, dasha_context?: {maha, antar, note}, system?, date?, approximate_time?}

    Returns {headline, overview, areas: {k: {text}}, affirmation, citations, generated_by: "llm", metadata}.
    Scores, key_factors, timing, lucky and dasha_context are NOT produced here: the caller merges
    them from `facts` (see personal_reading_service.assemble). The caller caches for 24 h.
    `budget_s` bounds the whole call (default DAILY_BUDGET_S). Raises LLMUnavailable (or another LLMError) when no valid
    reading can be produced in time; the caller falls back to `template_daily_personal(facts, language)`.

    Soft fields never fail a reading: unknown or missing citation ids are repaired in code, and a sentence that
    states an unsupported placement is dropped (or that one area gets its template line) instead of discarding the
    whole reading. Safety hits and an empty reading still fail."""
    t0 = time.monotonic()
    budget = budget_s or DAILY_BUDGET_S
    svc = get_service()
    await svc.budget.admit("daily_personal", "free")
    kfs = [_kf(f) for f in (facts.get("key_factors") or [])][:8]
    kfs = [k for k in kfs if k[0] and k[1]]
    system = system or facts.get("system") or "vedic"
    # D3: one zodiac system per reading. The engine emits tropical transit aspects (T.<planet>.<aspect>.N.<point>,
    # incl. outer planets and natal ASC). Since BUG-018 the engine no longer sends them for vedic; kept as defence in depth.
    from app.llm.facts import SYSTEM_TAG, factor_system, system_allows

    kfs = [k for k in kfs if system_allows(k[0], system)]
    if not kfs:
        raise LLMUnavailable("no key_factors to ground a personal reading")
    on = str(facts.get("date") or Date.today())
    reg = get_registry()
    sys_p = reg.render("daily_personal", system_label="sidereal zodiac" if system == "vedic" else "tropical zodiac",
                       language_instruction=LANGUAGE_INSTRUCTIONS.get(language, "English."))
    lim = reg.reg["limits"]["daily_personal"]

    def _tag(i: str) -> str:
        fs = system if i.startswith("T.MOON.H") else factor_system(i)
        return f" ({SYSTEM_TAG[fs]})" if fs in SYSTEM_TAG else ""

    lines = [(i, f"{label}{_tag(i)} (weight {w:.2f})") for i, label, w in kfs]
    rule = ("Use ONLY the Vedic (sidereal) system; do not mention other zodiac systems." if system == "vedic"
            else "Use ONLY the Western (tropical) system; do not mention nakshatra or dasha.")
    block = [render_fact_lines(f"TODAY'S FACTS for the user's chart on {on} (authoritative; computed by the engine). "
                               f"Chart system: {system}. {rule}", lines)]
    scores = {k: (facts.get("areas") or {}).get(k, {}).get("score") for k in PERSONAL_AREAS}
    block.append("AREA SCORES (engine-computed, 1 = gentle, 5 = easy flow): " +
                 ", ".join(f"{k} {v}" for k, v in scores.items() if v is not None))
    dc = facts.get("dasha_context") or {}
    if dc:
        block.append(f"DASHA CONTEXT: {dc.get('maha', '?')} Mahadasha / {dc.get('antar', '?')} Antardasha. {dc.get('note', '')}"[:300])
    if facts.get("approximate_time"):
        block.append("Birth time is NOT known: do not mention the Ascendant, Lagna, house numbers or exact dasha dates.")
    keys = [k for kf in (facts.get("key_factors") or [])[:4]
            for k in (kf.get("kb_keys", []) if isinstance(kf, dict) else [])] or ["daily guidance"]
    notes = await _notes_capped(svc, ["daily guidance"] + keys, "vedic" if system == "vedic" else "western", "timing",
                                min(DAILY_RAG_CAP_S, max(0.5, budget / 4)))
    if notes:
        block.append(render_notes(notes[:3])[0])      # three notes are plenty for a 250-word reading
    req = LLMRequest(task="daily_personal", system=sys_p.text, context_blocks=tuple(block),
                     messages=({"role": "user", "content": "Write today's personal reading."},),
                     max_output_tokens=lim["max_output_tokens"], response_schema=provider_schema(PersonalReadingText),
                     temperature=lim["temperature"], timeout_s=lim["timeout_s"], prompt_id=sys_p.prompt_id,
                     metadata={"user_id_hash": user_id_hash})
    ids = [i for i, _, _ in kfs]
    idset = set(ids)
    cf = ChartFacts("", system, bool(facts.get("approximate_time")), "", "", "", on, (),
                    tuple(FactorView(id=i, kind="transit", label=label, weight=w) for i, label, w in kfs))
    idx = ChartIndex(approximate_time=bool(facts.get("approximate_time")))
    # The engine's dasha context is authoritative too: "Mercury Antardasha" must not be flagged as an invented dasha.
    idx.maha, idx.antar = canon_planet(str(dc.get("maha") or "")), canon_planet(str(dc.get("antar") or ""))

    def fields(o: PersonalReadingText) -> dict[str, str]:
        return {"headline": o.headline, "overview": o.overview, "affirmation": o.affirmation,
                **{f"areas.{k}": getattr(getattr(o.areas, k), "text") for k in PERSONAL_AREAS}}

    def field_problems(text: str) -> list[str]:
        out = [f"safety:{h.cls}" for h in scan_output(text)]
        out += [f"{v.kind}: {v.detail}" for v in check_claims(text, idx, cf, transit_exempt=False)
                if v.kind in ("claim", "time_unknown")]
        return out

    def normalize(o: PersonalReadingText) -> PersonalReadingText:
        good = [c for c in dict.fromkeys(o.citations) if c in idset]
        return o.model_copy(update={"citations": good or ids[:2]})      # citations are metadata: repaired in code

    def check(o: PersonalReadingText) -> list[str]:
        return [p for text in fields(o).values() for p in field_problems(text)]

    def salvage(o: PersonalReadingText, problems: list[str]) -> PersonalReadingText | None:
        """Drop only the sentences that state an unsupported placement; a field left too short gets the template line."""
        from app.llm.daily_template import template_daily_personal
        from app.llm.validators import strip_violating_sentences

        if any(p.startswith("safety:") for p in problems):
            return None
        tpl = template_daily_personal(facts, language)
        floor = {"headline": 3, "overview": 40, "affirmation": 3}
        new: dict[str, str] = {}
        for name, text in fields(o).items():
            viol = [v for v in check_claims(text, idx, cf, transit_exempt=False) if v.kind in ("claim", "time_unknown")]
            if not viol:
                new[name] = text
                continue
            kept, _ = strip_violating_sentences(text, viol)
            if len(kept) >= floor.get(name, 10):
                new[name] = kept
            elif name.startswith("areas."):
                new[name] = tpl["areas"][name.split(".", 1)[1]]["text"]
            else:
                new[name] = tpl[name]
        try:
            return PersonalReadingText.model_validate({
                "headline": new["headline"], "overview": new["overview"], "affirmation": new["affirmation"],
                "areas": {k: {"text": new[f"areas.{k}"]} for k in PERSONAL_AREAS}, "citations": o.citations})
        except Exception:  # noqa: BLE001
            return None

    obj, res = await _structured(svc, req, PersonalReadingText, check, deadline_s=max(2.0, budget - (time.monotonic() - t0)),
                                 normalize=normalize, salvage=salvage)
    d = obj.model_dump()
    d["areas"] = {k: {"text": d["areas"][k]["text"]} for k in PERSONAL_AREAS}
    d["generated_by"] = "llm"
    d["metadata"] = {"prompt_version": sys_p.prompt_id, "provider": res.provider, "model": res.model,
                     "kb_chunk_ids": [n.chunk_id for n in notes[:3]], "tokens_used": res.input_tokens + res.output_tokens,
                     "factor_ids_provided": sorted(idset), "elapsed_s": round(time.monotonic() - t0, 1)}
    return d
