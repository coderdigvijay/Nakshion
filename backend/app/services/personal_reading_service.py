"""R3 personal daily reading (api-contract.md 7, R3; llm-integration.md section 4 daily_personal).

Facts and area scores come from the engine (``engine.personal_day``); the LLM writes text only
(``ai.daily_personal``) with a template fallback. Read path: Redis -> personal_readings row
(only if it was generated from the CURRENT primary chart) -> generate. Generated lazily on
first open, never by cron. Cache TTL: until the user's local midnight + 2 h.
"""
from __future__ import annotations

import fnmatch
import logging
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import Conflict, Forbidden, UpstreamUnavailable
from app.core.security import user_id_hash
from app.db.session import SessionLocal
from app.models import PersonalReading, User
from app.services import ai, cache, chart_service, engine, insight_service, quota_service

log = logging.getLogger("app.personal")


def _key(user_id: Any, on: date) -> str:
    return f"daily_personal:{user_id}:{on.isoformat()}"


def _ttl(user: User, on: date) -> int:
    tz = quota_service.user_zone(user)
    expires = datetime.combine(on + timedelta(days=1), time(2, 0), tzinfo=tz)
    return max(60, int((expires - datetime.now(UTC)).total_seconds()))


async def get_today(db: AsyncSession, user: User) -> dict[str, Any]:
    if not user.email_verified:
        raise Forbidden("Please verify your email to see your personal reading.", code="EMAIL_NOT_VERIFIED")
    chart = await chart_service.get_primary(db, user.id)
    if chart is None:
        raise Conflict("Add your birth details first so your reading is about *your* chart.", code="CHART_REQUIRED")
    on = quota_service.local_today(user)
    system = user.astrology_system or "vedic"
    key = _key(user.id, on)
    current_engine = engine.engine_version()

    def fresh(reading: dict[str, Any] | None) -> bool:
        # A reading is only valid for THIS chart, THIS system and the CURRENT engine version.
        return bool(reading) and reading.get("chart_id") == str(chart.id) and reading.get("system") == system \
            and reading.get("engine_version") == current_engine

    hit = await cache.get_json(key)
    if fresh(hit):
        return hit
    row = await db.scalar(
        select(PersonalReading).where(
            PersonalReading.user_id == user.id, PersonalReading.date == on, PersonalReading.system == system
        )
    )
    # The stored row must also be newer than the chart's last edit (belt and braces: edits delete the rows).
    if row is not None and row.chart_id == chart.id and fresh(row.reading) and row.created_at >= chart.updated_at:
        await cache.set_json(key, row.reading, _ttl(user, on))
        return row.reading
    chart_id, chart_data, language = chart.id, chart.chart_data, user.preferred_language or "english"
    # Same 0.1-degree convention as /panchang so Rahu Kaal etc. agree to the minute.
    lat, lon = insight_service.round_coords(float(chart.latitude), float(chart.longitude))
    tz = quota_service.user_zone(user).key
    await db.commit()  # no DB connection held across engine/LLM work

    try:
        facts = await engine.personal_day(chart_data, on, system=system, latitude=lat, longitude=lon, timezone=tz)
    except UpstreamUnavailable as exc:
        # Never substitute a generic or other-system horoscope: the client shows a retry state instead.
        raise UpstreamUnavailable(
            "Your personal reading is taking longer than usual. Please try again in a moment.",
            code="PERSONAL_READING_UNAVAILABLE",
            headers={"Retry-After": "30"},
        ) from exc
    facts = _system_consistent(facts, system)
    narrative, generated_by = await ai.daily_personal(
        facts, language=language, system=system, user_id_hash=user_id_hash(user.id)
    )
    reading = assemble(facts, narrative, on=on, chart_id=str(chart_id), system=system, generated_by=generated_by)

    async with SessionLocal() as s:
        stmt = insert(PersonalReading).values(
            user_id=user.id, date=on, system=system, chart_id=chart_id, reading=reading, generated_by=generated_by
        )
        await s.execute(
            stmt.on_conflict_do_update(
                index_elements=[PersonalReading.user_id, PersonalReading.date, PersonalReading.system],
                set_={"chart_id": chart_id, "reading": reading, "generated_by": generated_by},
            )
        )
        await s.commit()
    await cache.set_json(key, reading, _ttl(user, on) if generated_by == "llm" else 600)
    return reading


def _system_consistent(facts: dict[str, Any], system: str) -> dict[str, Any]:
    """Keep one zodiac system in everything we show or send to the LLM, and label each chip with it.

    TEMPORARY (BUG-017): until the engine stops emitting tropical transit-aspect factors (ids ``T.<planet>.<aspect>.N.<point>``)
    for vedic requests, drop them for vedic users. REMOVE this filter once the engine fix lands; the labelling stays."""
    out = dict(facts)
    for key in ("key_factors", "factors"):
        items = [f for f in (facts.get(key) or []) if isinstance(f, dict)]
        if system == "vedic":
            items = [f for f in items if not fnmatch.fnmatchcase(str(f.get("factor_id") or f.get("id") or ""), "T.*.N.*")]
        out[key] = [{**f, "system": system} for f in items]
    return out


def assemble(facts: dict[str, Any], narrative: dict[str, Any], *, on: date, chart_id: str, system: str,
             generated_by: str) -> dict[str, Any]:
    """Contract shape (R3). Scores/factors/timing/lucky are engine values; text is narrative."""
    areas_f = facts.get("areas") or {}
    areas_t = narrative.get("areas") or {}
    areas = {}
    for k in ("love", "career", "wellness", "money"):
        try:
            score = int(round(float((areas_f.get(k) or {}).get("score", 3))))
        except (TypeError, ValueError):
            score = 3
        areas[k] = {"score": min(5, max(1, score)), "text": str((areas_t.get(k) or {}).get("text") or "")}
    out: dict[str, Any] = {
        "date": on.isoformat(),
        "chart_id": chart_id,
        "system": system,
        "headline": str(narrative.get("headline") or "")[:90],
        "overview": str(narrative.get("overview") or ""),
        "areas": areas,
        "key_factors": list(facts.get("key_factors") or [])[:5],
        "timing": facts.get("timing") or {},
        "affirmation": str(narrative.get("affirmation") or ""),
        "lucky": facts.get("lucky") or {},
        "generated_by": generated_by,
        "engine_version": engine.engine_version(),
    }
    if facts.get("dasha_context"):
        out["dasha_context"] = facts["dasha_context"]
    return out
