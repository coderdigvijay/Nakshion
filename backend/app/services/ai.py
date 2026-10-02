"""Adapter over the LLM/RAG pipeline (``app.llm``, owned by ai-genai-specialist).

This is the ONLY module in services/ that imports ``app.llm``. No vendor SDK is imported here.
Error mapping:
- an exception with ``code == "INPUT_REJECTED"`` -> 422 INPUT_REJECTED (safety pre-filter)
- anything else from chat -> 503 AI_UNAVAILABLE (nothing persisted, no quota consumed)
- daily_sign / compat narrative never fail: they fall back to deterministic templates
  (llm-integration.md 7.3), marked ``generated_by="template"``.
"""
from __future__ import annotations

import asyncio
import importlib
import logging
import re
from collections.abc import AsyncIterator
from datetime import date
from types import ModuleType
from typing import Any

from app.core.errors import AIUnavailable, ValidationFailed

log = logging.getLogger("app.ai")


class LLMMissing(RuntimeError):
    pass


def _module() -> ModuleType:
    try:
        return importlib.import_module("app.llm")
    except ImportError as exc:
        raise LLMMissing(str(exc)) from exc


def _fn(name: str) -> Any:
    fn = getattr(_module(), name, None)
    if fn is None:
        raise LLMMissing(f"app.llm.{name} not available")
    return fn


def _map_chat_error(exc: BaseException) -> Exception:
    if type(exc).__name__ == "LLMBudgetUnavailable":
        return AIUnavailable("Nakshion is resting; try again later.")
    code = getattr(exc, "code", None)
    if code == "INPUT_REJECTED":
        detail = getattr(exc, "detail", None) or str(exc) or "Let's keep our conversation to questions about your chart."
        return ValidationFailed(detail, code="INPUT_REJECTED")
    return AIUnavailable()


# ------------------------------------------------------------------ chat
async def chat_reply(
    *,
    chart_data: dict[str, Any],
    question: str,
    history: list[dict[str, str]],
    language: str,
    user_id_hash: str,
    astrology_system: str,
    display_name: str,
    user_id: str,
    tier: str,
    deadline_s: float,
) -> dict[str, Any]:
    """Returns {answer, citations:[{factor_id,label}], tokens_used, metadata}."""
    try:
        fn = _fn("generate_chat_reply")
    except LLMMissing as exc:
        log.error("llm_missing", extra={"err": str(exc)})
        raise AIUnavailable() from exc
    try:
        result = await asyncio.wait_for(
            fn(
                chart_data=chart_data,
                question=question,
                history=history,
                language=language,
                user_id_hash=user_id_hash,
                astrology_system=astrology_system,
                display_name=display_name,
                user_id=user_id,
                tier=tier,
            ),
            timeout=deadline_s,
        )
    except (ValidationFailed, AIUnavailable):
        raise
    except asyncio.TimeoutError as exc:
        log.warning("chat_deadline_exceeded")
        raise AIUnavailable() from exc
    except Exception as exc:  # noqa: BLE001 - pipeline boundary
        mapped = _map_chat_error(exc)
        if isinstance(mapped, AIUnavailable):
            log.warning("chat_llm_failed", extra={"exc_type": type(exc).__name__})
        raise mapped from exc
    return _normalise_chat(result)


def clean_sources(raw: Any, limit: int = 8) -> list[dict[str, Any]]:
    """Reference sources for citation chips: ONLY {source_id, title, section, tier}, de-duplicated.
    Anything else the pipeline attached (chunk text, file names, aliases) is dropped here, so long
    verbatim passages can never reach the client (llm-integration.md section 6)."""
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in raw or []:
        if not isinstance(item, dict) or not item.get("source_id") or not item.get("title"):
            continue
        sid, title = str(item["source_id"])[:32], str(item["title"]).strip()[:120]
        tier_hint = item.get("tier")
        if title.lower().endswith(".md"):
            # A chunk indexed without provenance metadata falls back to its file name: never show that.
            try:
                from app.rag.sources import source_info

                info = source_info(title[:-3])
                title, tier_hint = info.display_title(), item.get("tier") or info.tier
            except Exception:  # noqa: BLE001
                title = title[:-3].replace("_", " ").title()
        section = str(item.get("section") or "").strip()[:80]
        key = (sid, section.lower())
        if key in seen or (title.lower(), section.lower()) in {(o["title"].lower(), o["section"].lower()) for o in out}:
            continue
        seen.add(key)
        tier = tier_hint
        out.append({"source_id": sid, "title": title, "section": section,
                    "tier": tier if isinstance(tier, int) and not isinstance(tier, bool) else None})
        if len(out) >= limit:
            break
    return out


def _normalise_chat(result: Any) -> dict[str, Any]:
    if not isinstance(result, dict):
        result = dict(getattr(result, "__dict__", {}))
    answer = str(result.get("answer") or "").strip()
    if not answer:
        raise AIUnavailable()
    cites = []
    for c in result.get("citations") or []:
        if isinstance(c, dict) and c.get("factor_id"):
            cites.append({"factor_id": str(c["factor_id"]), "label": str(c.get("label") or c["factor_id"])})
        elif isinstance(c, str):
            cites.append({"factor_id": c, "label": c})
    tokens = result.get("tokens_used")
    return {
        "answer": answer,
        "citations": cites,
        "sources": clean_sources(result.get("sources")),
        "tokens_used": int(tokens) if isinstance(tokens, (int, float)) else None,
        "metadata": dict(result.get("metadata") or {}),
        "topic": result.get("topic"),
    }


async def chat_stream(**kwargs: Any) -> AsyncIterator[tuple[str, Any]]:
    """Yields ("delta", str) | ("replace", str) | ("done", normalised_result_dict).

    Falls back to a single non-streamed reply when the pipeline has no streaming function."""
    deadline_s = kwargs.pop("deadline_s")
    try:
        fn = _fn("stream_chat_reply")
    except LLMMissing:
        result = await chat_reply(deadline_s=deadline_s, **kwargs)
        yield ("delta", result["answer"])
        yield ("done", result)
        return
    loop = asyncio.get_running_loop()
    end = loop.time() + deadline_s
    agen = fn(**kwargs)
    try:
        while True:
            remaining = end - loop.time()
            if remaining <= 0:
                raise AIUnavailable()
            try:
                kind, payload = await asyncio.wait_for(agen.__anext__(), timeout=remaining)
            except StopAsyncIteration:
                raise AIUnavailable() from None  # stream ended without "done"
            except asyncio.TimeoutError as exc:
                raise AIUnavailable() from exc
            if kind == "done":
                yield ("done", _normalise_chat(payload))
                return
            yield (kind, str(payload))
    except (AIUnavailable, ValidationFailed):
        raise
    except Exception as exc:  # noqa: BLE001
        raise _map_chat_error(exc) from exc
    finally:
        aclose = getattr(agen, "aclose", None)
        if aclose is not None:
            try:
                await aclose()
            except Exception:  # noqa: BLE001
                pass


# ------------------------------------------------------------------ daily sign horoscope
def _daily_template(sign: str, on: date, transit_data: dict[str, Any]) -> dict[str, str]:
    moon = transit_data.get("moon") or {}
    focus = transit_data.get("solar_house_focus") or {}
    moon_house = focus.get("moon_house")
    aspects = transit_data.get("aspects_today") or []
    lead = f"With the Moon in {moon.get('sign', 'motion')}"
    if moon_house:
        lead += f" moving through your {_ordinal(int(moon_house))} solar house"
    general = (
        f"{lead}, today favours steady attention to what is already in front of you, {sign.title()}. "
        "Take things one step at a time and leave room for rest."
    )
    if aspects:
        a = aspects[0]
        general += f" {a.get('planet1')} forms a {a.get('type')} with {a.get('planet2')}, a theme worth noticing as the day unfolds."
    return {
        "general": general,
        "love": "Keep conversations kind and simple; small gestures carry more weight than big statements today.",
        "career": "Focus on one priority and finish it before picking up the next.",
        "wellness": "A short walk and an early night will serve you well.",
    }


def _ordinal(n: int) -> str:
    return f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"


async def daily_sign(sign: str, on: date, transit_data: dict[str, Any], system: str) -> tuple[dict[str, str], str]:
    """Returns (readings{general,love,career,wellness}, generated_by)."""
    try:
        fn = _fn("generate_daily_sign")
        zodiac = "tropical" if system == "western" else "sidereal"
        out = await asyncio.wait_for(fn(sign, on, transit_data, system=zodiac), timeout=20)
        if isinstance(out, dict) and out.get("general"):
            by = "template" if out.get("generated_by") == "template" else "llm"
            return {k: str(out.get(k) or "") for k in ("general", "love", "career", "wellness")}, by
    except Exception as exc:  # noqa: BLE001 - never 5xx a reading when templating is possible
        log.warning("daily_sign_llm_failed", extra={"exc_type": type(exc).__name__})
    tmpl = getattr(_safe_module(), "template_daily_sign", None)
    if tmpl is not None:
        try:
            return tmpl(sign=sign, date=on, transit_data=transit_data, system=system), "template"
        except Exception:  # noqa: BLE001
            pass
    return _daily_template(sign, on, transit_data), "template"


def _safe_module() -> ModuleType | None:
    try:
        return _module()
    except LLMMissing:
        return None


# ------------------------------------------------------------------ personal daily reading (R3)
_ISO_RANGE = re.compile(r"\s*\(?\s*\d{4}-\d{2}-\d{2}(?:\s*(?:to|-|–|—)\s*\d{4}-\d{2}-\d{2})?\s*\)?")
_ISO_DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_FLAG_WORDS = {"PRESENT": "present", "ABSENT": "absent", "CANCELLED": "cancelled", "PARTIAL": "partial",
               "TRUE": "yes", "FALSE": "no", "NONE": "none"}
_SNAKE = re.compile(r"\b[a-z]{2,}(?:_[a-z]{2,})+\b")
_FLAG = re.compile(r"\b(" + "|".join(_FLAG_WORDS) + r")\b")


def humanize(text: str) -> str:
    """Make machine tokens fit for prose: below_average -> "below average", PRESENT -> "present".
    Applied to every generated narrative string that leaves the adapter (LLM or template)."""
    text = _SNAKE.sub(lambda m: m.group(0).replace("_", " "), text)
    return _FLAG.sub(lambda m: _FLAG_WORDS[m.group(1)], text)


def _headline_subject(label: str) -> str:
    """"Mercury Mahadasha (2025-07-03 to 2042-07-03)" -> "Mercury period"; never shows raw dates."""
    t = _ISO_RANGE.sub("", label)
    t = re.sub(r"\b(Maha|Antar|Pratyantar)dasha\b", "period", t, flags=re.I)
    t = re.sub(r"\b(Maha|Antar|Pratyantar)\s*dasha\b", "period", t, flags=re.I)
    return humanize(re.sub(r"\s{2,}", " ", t).strip(" ,;:-"))[:60]


_HEADLINES = {
    "english": ("{x} — steady focus today", "A day for steady, mindful progress"),
    "hinglish": ("{x} — aaj sthir dhyaan", "Aaj ka din sthir aur sachet pragati ka hai"),
    "hindi": ("{x} — आज स्थिर ध्यान", "आज का दिन स्थिर और सजग प्रगति का है"),
}
_AFFIRMATIONS = {
    "english": "I move through today with patience and clarity.",
    "hinglish": "Main aaj dhairya aur spashtata ke saath aage badhta/badhti hoon.",
    "hindi": "मैं आज धैर्य और स्पष्टता के साथ आगे बढ़ता/बढ़ती हूँ।",
}


def _personal_template(facts: dict[str, Any], language: str = "english") -> dict[str, Any]:
    factors = facts.get("key_factors") or []
    top = factors[0].get("label") if factors and isinstance(factors[0], dict) else None
    subject = _headline_subject(str(top)) if top else ""
    with_subject, plain = _HEADLINES.get(language, _HEADLINES["english"])
    texts = {
        "love": "Gentle, honest conversations go further than grand gestures today.",
        "career": "Pick one priority and give it your best focus.",
        "wellness": "Keep a steady routine and protect your rest.",
        "money": "A good day to review rather than to make big commitments.",
    }
    return {
        "headline": (with_subject.format(x=subject) if subject else plain)[:90],
        "overview": "Your reading today is based on the current planetary movements relative to your chart. "
                    "Take things one step at a time and notice where your energy flows most easily.",
        "areas": {k: {"text": v} for k, v in texts.items()},
        "affirmation": _AFFIRMATIONS.get(language, _AFFIRMATIONS["english"]),
    }


def _clean_strings(obj: Any) -> Any:
    """humanize() every string inside a narrative structure."""
    if isinstance(obj, str):
        return humanize(obj)
    if isinstance(obj, list):
        return [_clean_strings(x) for x in obj]
    if isinstance(obj, dict):
        return {k: _clean_strings(v) for k, v in obj.items()}
    return obj


def template_daily_personal(facts: dict[str, Any], language: str = "english") -> dict[str, Any]:
    """Deterministic reading text built from the engine facts (no LLM). Prefers the AI layer's template
    (v2, area-aware); falls back to the adapter's own if that is unavailable."""
    mod = _safe_module()
    fn = getattr(mod, "template_daily_personal", None) if mod is not None else None
    if fn is not None:
        try:
            out = fn(facts, language)
            if isinstance(out, dict) and out.get("overview"):
                return _clean_strings(out)
        except Exception:  # noqa: BLE001
            log.warning("template_daily_personal_failed")
    return _personal_template(facts, language)


def daily_budget_s() -> float:
    mod = _safe_module()
    return float(getattr(mod, "DAILY_BUDGET_S", 32.0)) if mod is not None else 32.0


async def daily_personal_llm(
    facts: dict[str, Any], *, language: str, system: str, user_id_hash: str
) -> dict[str, Any] | None:
    """LLM narrative or None. The outer timeout is the AI layer's budget + 3 s, as its contract requires."""
    try:
        fn = _fn("generate_daily_personal")
        budget = daily_budget_s()
        out = await asyncio.wait_for(
            fn(facts, language=language, system=system, user_id_hash=user_id_hash, budget_s=budget),
            timeout=budget + 3,
        )
    except Exception as exc:  # noqa: BLE001 - the caller serves the template
        log.warning("daily_personal_llm_failed", extra={"exc_type": type(exc).__name__})
        return None
    if isinstance(out, dict) and out.get("overview") and out.get("generated_by") != "template":
        return _clean_strings(out)
    return None


async def daily_personal(
    facts: dict[str, Any], *, language: str, system: str, user_id_hash: str
) -> tuple[dict[str, Any], str]:
    """Returns (narrative{headline, overview, areas{k:{text}}, affirmation}, generated_by)."""
    out = await daily_personal_llm(facts, language=language, system=system, user_id_hash=user_id_hash)
    if out is not None:
        return out, "llm"
    return template_daily_personal(facts, language), "template"


# ------------------------------------------------------------------ compatibility narrative
_CATEGORY_TEXT = {
    "emotional": ("You tend to understand each other's moods easily.", "Emotional rhythms differ, so patience helps."),
    "communication": ("Conversation flows naturally between you.", "You may need to slow down and check you heard each other."),
    "romance": ("There is natural warmth and affection here.", "Affection is expressed differently; naming what you need helps."),
    "passion": ("You energise and motivate each other.", "Drive can turn into friction; channel it into shared goals."),
    "long-term": ("There is a solid base for building something lasting.", "Long-term plans benefit from clear, shared commitments."),
}


def _pair_phrase(p: Any) -> str:
    if isinstance(p, dict):
        return f"{p.get('planet1')} {p.get('aspect') or p.get('type')} {p.get('planet2')}"
    return str(p)


def aspect_key(a: dict[str, Any]) -> str:
    return f"{a.get('planet1', '?')}-{a.get('aspect') or a.get('type') or '?'}-{a.get('planet2', '?')}".lower().replace(" ", "_")


def _compat_template(report: dict[str, Any]) -> dict[str, Any]:
    cats = report.get("categories") or {}
    out_cats = {}
    for key, (pos, neg) in _CATEGORY_TEXT.items():
        score = float((cats.get(key) or {}).get("score", 5))
        out_cats[key] = {"summary": pos if score >= 5 else neg}
    interps = [
        f"{_pair_phrase(a)}: "
        + ("a supportive link between you." if float(a.get("contribution", 0) or 0) >= 0 else "an area that asks for patience and understanding.")
        for a in report.get("synastry_aspects") or []
    ]
    strengths = [f"{_pair_phrase(p)} supports this connection" for p in (report.get("strengths_seeds") or [])][:3]
    challenges = [f"{_pair_phrase(p)} asks for patience" for p in (report.get("challenges_seeds") or [])][:3]
    while len(strengths) < 3:
        strengths.append("Shared willingness to understand each other")
    while len(challenges) < 3:
        challenges.append("Different pacing in daily life")
    return {
        "summary": "This reading is based on how your two charts interact. Scores describe tendencies, not destiny.",
        "categories": out_cats,
        "aspect_interpretations": interps,
        "strengths": strengths,
        "challenges": challenges,
    }


def _llm_report_view(report: dict[str, Any]) -> dict[str, Any]:
    """Engine report -> the facts shape app.llm.generate_compat_narrative reads."""
    aspects = [
        {"key": aspect_key(a), "planet1": a.get("planet1"), "planet2": a.get("planet2"),
         "type": a.get("aspect"), "orb": a.get("orb")}
        for a in report.get("synastry_aspects") or []
    ]
    ak = report.get("ashtakoota") or {}
    return {
        "overall_score": report.get("overall_score"),
        "categories": {k: {"score": (v or {}).get("score")} for k, v in (report.get("categories") or {}).items()},
        "aspects": aspects,
        "kootas": ak.get("kootas") or [],
        # The FULL ashtakoota (kootas, nadi/bhakoot/gana doshas, totals, verification flags): the narrative's
        # dosha handling reads it. Dropping it silently disabled dosha checks (BUG-017).
        "ashtakoota": report.get("ashtakoota"),
        "manglik": report.get("manglik"),
        "approximate": bool(report.get("approximate")),
        "score_breakdown": report.get("score_breakdown"),
        "overall_band": report.get("overall_band"),  # forwarded when the engine adds it
        "relationship_type": report.get("relationship_type"),
    }


def _align_interpretations(report: dict[str, Any], interps: Any) -> list[str]:
    """LLM returns [{aspect_key, text}]; align to the engine's synastry_aspects order."""
    by_key: dict[str, str] = {}
    for item in interps or []:
        if isinstance(item, dict) and item.get("aspect_key"):
            by_key[str(item["aspect_key"])] = str(item.get("text") or "")
    return [by_key.get(aspect_key(a), "") for a in report.get("synastry_aspects") or []]


async def compat_narrative(report: dict[str, Any], relationship_type: str) -> tuple[dict[str, Any], str]:
    """Returns (narrative, generated_by). narrative.aspect_interpretations is a list of strings
    aligned with report['synastry_aspects']; missing LLM pieces are filled from the template."""
    template = _compat_template(report)
    try:
        fn = _fn("generate_compat_narrative")
        out = await asyncio.wait_for(fn(_llm_report_view(report), relationship_type), timeout=20)
        if isinstance(out, dict) and out.get("categories"):
            cats = {k: {"summary": str(((out.get("categories") or {}).get(k) or {}).get("summary") or template["categories"][k]["summary"])}
                    for k in _CATEGORY_TEXT}
            interps = _align_interpretations(report, out.get("aspect_interpretations"))
            interps = [t or template["aspect_interpretations"][i] for i, t in enumerate(interps)]
            return _clean_strings({
                "summary": str(out.get("summary") or template["summary"]),
                "categories": cats,
                "aspect_interpretations": interps,
                "strengths": [str(x) for x in (out.get("strengths") or template["strengths"])][:3],
                "challenges": [str(x) for x in (out.get("challenges") or template["challenges"])][:3],
            }), "llm"
    except Exception as exc:  # noqa: BLE001 - the report is always returned
        log.warning("compat_llm_failed", extra={"exc_type": type(exc).__name__})
    return _clean_strings(template), "template"


# ------------------------------------------------------------------ wiring (startup)
class DbUsageSink:
    """Persists every LLM attempt to llm_usage (architecture.md 4.3). Never fails the request."""

    async def record(self, rec: Any) -> None:
        import uuid as _uuid

        from app.db.session import SessionLocal
        from app.models import LLMUsage

        try:
            uid = _uuid.UUID(str(rec.user_id)) if getattr(rec, "user_id", None) else None
        except ValueError:
            uid = None
        try:
            async with SessionLocal() as s:
                s.add(LLMUsage(
                    user_id=uid, task=str(rec.task)[:30], provider=str(rec.provider)[:20], model=str(rec.model)[:60],
                    prompt_version=str(rec.prompt_version)[:20], input_tokens=int(rec.input_tokens),
                    cached_input_tokens=int(rec.cached_input_tokens), output_tokens=int(rec.output_tokens),
                    cost_usd=float(rec.cost_usd), latency_ms=int(rec.latency_ms), outcome=str(rec.outcome)[:12],
                    error=(str(getattr(rec, "error", "") or "")[:500] or None),
                ))
                await s.commit()
        except Exception:  # noqa: BLE001
            log.warning("llm_usage_write_failed")


def configure_pipeline() -> bool:
    """Wire app.llm with Redis (budget counters), pgvector retrieval and the DB usage sink.
    LLMSettings reads GEMINI_API_KEY or GEMINI_API_KEY1..5 from the env (config.py loads .env)."""
    try:
        mod = _module()
        from app.db.session import engine as db_engine
        from app.llm.config import LLMSettings
        from app.services import cache

        llm_settings = LLMSettings()
        retriever = None
        try:
            from app.rag import build_retriever

            retriever = build_retriever(llm_settings, db_engine, redis=cache.get_client())
        except Exception:  # noqa: BLE001 - chart-only answers still work
            log.warning("rag_retriever_unavailable")
        from app.core.config import settings as app_settings

        counters = cache.get_client() if app_settings.LLM_BUDGET_COUNTERS == "redis" else None
        mod.configure(llm_settings, retriever=retriever, usage_sink=DbUsageSink(), redis=counters)
        return True
    except Exception:  # noqa: BLE001
        log.exception("llm_pipeline_configure_failed")
        return False


# ------------------------------------------------------------------ RAG startup self-check (informational)
_rag_status: dict[str, Any] = {"checked": False}


async def rag_startup_check() -> dict[str, Any]:
    """Run the retriever's self-check once at startup. Never raises and never blocks boot for long:
    a failing index only degrades chat to chart-facts-only (logged as WARNING). /health/ready reports the
    cached result; /health/live never touches it."""
    global _rag_status
    try:
        retriever = _module().get_service().retriever
    except Exception:  # noqa: BLE001
        retriever = None
    if retriever is None:
        _rag_status = {"checked": True, "ok": False, "mode": "off", "problems": ["no retriever configured"]}
        log.warning("rag_unavailable", extra={"reason": "no retriever configured"})
        return _rag_status
    try:
        res = await asyncio.wait_for(retriever.self_check(), timeout=15)
        _rag_status = {
            "checked": True,
            "ok": bool(res.get("ok")),
            "problems": list(res.get("problems") or []),
            "chunks": res.get("chunks"),
            "active_version": res.get("active_version"),
        }
    except Exception as exc:  # noqa: BLE001
        _rag_status = {"checked": True, "ok": False, "problems": [f"self_check failed: {type(exc).__name__}"]}
    if not _rag_status["ok"]:
        log.warning("rag_self_check_failed", extra={"problems": "; ".join(_rag_status["problems"])[:300]})
    else:
        log.info("rag_self_check_ok", extra={"chunks": _rag_status.get("chunks"), "version": _rag_status.get("active_version")})
    return _rag_status


def rag_status() -> dict[str, Any]:
    return dict(_rag_status)
