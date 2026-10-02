"""R3 personal daily reading (api-contract.md 7, R3; llm-integration.md section 4 daily_personal).

Facts and area scores come from the engine (``engine.personal_day``); the LLM writes text only
(``ai.daily_personal``) with a template fallback. Read path: Redis -> personal_readings row
(only if it was generated from the CURRENT primary chart) -> generate. Generated lazily on
first open, never by cron. Cache TTL: until the user's local midnight + 2 h.
"""
from __future__ import annotations

import asyncio
import fnmatch
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import select, text
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


FOREGROUND_WAIT_S = 6.0      # how long a request waits for the LLM before it is served the template
TEMPLATE_TTL_S = 300         # a template is a stop-gap: cached and trusted for 5 minutes, then regenerated
_inflight: dict[str, asyncio.Task] = {}      # single-flight per user + date + system + chart
_background: set[asyncio.Task] = set()       # strong references (the loop only keeps weak ones)


@dataclass(frozen=True)
class _Job:
    key: str                  # redis key
    flight: str               # single-flight key
    user_id: uuid.UUID
    uid_hash: str
    on: date
    system: str
    chart_id: uuid.UUID
    chart_updated_at: datetime
    facts: dict[str, Any]
    language: str
    ttl_s: int


_UPSERT = text(
    """
    INSERT INTO personal_readings (user_id, date, system, chart_id, reading, generated_by)
    SELECT CAST(:u AS uuid), CAST(:d AS date), CAST(:s AS varchar), CAST(:cid AS uuid), CAST(:r AS jsonb), CAST(:g AS varchar)
    WHERE EXISTS (SELECT 1 FROM birth_charts WHERE id = CAST(:cid AS uuid) AND updated_at = CAST(:ts AS timestamptz))   -- chart unchanged since we started (BUG-016)
    ON CONFLICT (user_id, date, system) DO UPDATE
      SET chart_id = EXCLUDED.chart_id, reading = EXCLUDED.reading,
          generated_by = EXCLUDED.generated_by, created_at = now()
      WHERE (CAST(:g AS varchar) = 'llm' OR personal_readings.generated_by <> 'llm'
             OR personal_readings.chart_id IS DISTINCT FROM CAST(:cid AS uuid))
    """
)


async def _store(job: _Job, reading: dict[str, Any], generated_by: str) -> bool:
    """Persist unless the chart changed meanwhile; a template never overwrites an LLM reading. Own short session."""
    async with SessionLocal() as s:
        res = await s.execute(
            _UPSERT,
            {"u": job.user_id, "d": job.on, "s": job.system, "cid": job.chart_id, "ts": job.chart_updated_at,
             "r": json.dumps(reading, default=str), "g": generated_by},
        )
        await s.commit()
        return bool(res.rowcount)


async def _llm_job(job: _Job) -> dict[str, Any] | None:
    """Generate the LLM reading and store it. Never raises; None means "keep serving the template"."""
    try:
        narrative = await ai.daily_personal_llm(
            job.facts, language=job.language, system=job.system, user_id_hash=job.uid_hash
        )
        if narrative is None:
            return None
        reading = assemble(job.facts, narrative, on=job.on, chart_id=str(job.chart_id), system=job.system,
                           generated_by="llm")
        if not await _store(job, reading, "llm"):
            log.info("personal_reading_upgrade_discarded", extra={"reason": "chart changed"})
            return None
        await cache.set_json(job.key, reading, job.ttl_s)
        return reading
    except Exception:  # noqa: BLE001
        log.exception("personal_reading_job_failed")
        return None


def _start_or_join(job: _Job) -> asyncio.Task:
    task = _inflight.get(job.flight)
    if task is not None and not task.done():
        return task  # single-flight: repeated page loads share one LLM call
    task = asyncio.create_task(_llm_job(job))
    _inflight[job.flight] = task
    _background.add(task)

    def _done(t: asyncio.Task) -> None:
        _background.discard(t)
        if _inflight.get(job.flight) is t:
            _inflight.pop(job.flight, None)

    task.add_done_callback(_done)
    return task


async def drain() -> None:
    """Await background upgrades (tests / graceful shutdown)."""
    if _background:
        await asyncio.gather(*list(_background), return_exceptions=True)


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
    # The stored row must also be newer than the chart's last edit (belt and braces: edits delete the rows),
    # and a TEMPLATE row is only a stop-gap: after 5 minutes we try for the LLM reading again.
    if row is not None and row.chart_id == chart.id and fresh(row.reading) and row.created_at >= chart.updated_at:
        age_s = (datetime.now(UTC) - row.created_at).total_seconds()
        if row.generated_by == "llm":
            await cache.set_json(key, row.reading, _ttl(user, on))
            return row.reading
        if age_s < TEMPLATE_TTL_S:
            await cache.set_json_nx(key, row.reading, int(TEMPLATE_TTL_S - age_s) + 1)
            return row.reading
    chart_id, chart_data, language = chart.id, chart.chart_data, user.preferred_language or "english"
    chart_updated_at = chart.updated_at
    # Same 0.1-degree convention as /panchang so Rahu Kaal etc. agree to the minute.
    lat, lon = insight_service.round_coords(float(chart.latitude), float(chart.longitude))
    tz = quota_service.user_zone(user).key
    ttl_full = _ttl(user, on)
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
    job = _Job(key=key, flight=f"{user.id}:{on}:{system}:{chart_id}", user_id=user.id, uid_hash=user_id_hash(user.id),
               on=on, system=system, chart_id=chart_id, chart_updated_at=chart_updated_at, facts=facts,
               language=language, ttl_s=ttl_full)

    # Try for the LLM reading for a few seconds; the work continues in the background if it is slower.
    task = _start_or_join(job)
    done, _ = await asyncio.wait({task}, timeout=FOREGROUND_WAIT_S)
    if task in done and not task.cancelled() and task.exception() is None and task.result():
        return task.result()

    template = assemble(facts, ai.template_daily_personal(facts, language), on=on, chart_id=str(chart_id),
                        system=system, generated_by="template")
    await _store(job, template, "template")
    if task.done() and not task.cancelled() and task.exception() is None and task.result():
        return task.result()  # the LLM reading landed while we were storing the template
    await cache.set_json_nx(key, template, TEMPLATE_TTL_S)
    return template


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
