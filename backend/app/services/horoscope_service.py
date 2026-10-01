"""Daily sign horoscopes (api-contract R1/R2): Redis -> Postgres -> generate under a lock.

- Transit facts come from the engine; the LLM only narrates (llm-integration.md section 4).
- LLM output is persisted (ON CONFLICT DO NOTHING on (sign, date, system)) and cached until
  06:00 UTC the day after ``date``. Template fallbacks are NOT persisted (a later LLM run
  replaces them) and are cached for 10 minutes only.
- No DB session is held across the engine/LLM calls.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AIUnavailable, BadRequest, ValidationFailed
from app.db.session import SessionLocal
from app.models import DailyHoroscope, User
from app.schemas.horoscope import DailyHoroscopeOut
from app.services import ai, cache, engine, quota_service

log = logging.getLogger("app.horoscope")

SIGNS = (
    "aries", "taurus", "gemini", "cancer", "leo", "virgo",
    "libra", "scorpio", "sagittarius", "capricorn", "aquarius", "pisces",
)
SYSTEMS = ("western", "vedic")
LOCK_TTL_S = 30
WAIT_FOR_PEER_S = 10.0
TEMPLATE_TTL_S = 600


def _key(sign: str, on: date, system: str) -> str:
    return f"horoscope:{sign}:{on.isoformat()}:{system}"


def _ttl_for(on: date) -> int:
    expires = datetime.combine(on + timedelta(days=1), time(6, 0), tzinfo=UTC)
    return max(60, int((expires - datetime.now(UTC)).total_seconds()))


def normalise_sign(sign: str | None) -> str:
    s = (sign or "").strip().lower()
    if s not in SIGNS:
        raise BadRequest("Please choose a valid zodiac sign.", code="INVALID_SIGN")
    return s


def resolve_date(user: User | None, requested: date | None, *, past_days: int, future_days: int = 1) -> date:
    today = quota_service.local_today(user)
    if requested is None:
        return today
    if not (today - timedelta(days=past_days) <= requested <= today + timedelta(days=future_days)):
        raise ValidationFailed("That date is outside the available range.", code="DATE_OUT_OF_RANGE")
    return requested


def _row_out(row: DailyHoroscope) -> dict[str, Any]:
    return DailyHoroscopeOut(
        id=row.id,
        zodiac_sign=row.zodiac_sign,
        date=row.date,
        general_reading=row.general_reading,
        love_reading=row.love_reading,
        career_reading=row.career_reading,
        wellness_reading=row.wellness_reading,
        lucky_number=row.lucky_number,
        lucky_color=row.lucky_color,
        transit_data=row.transit_data,
        created_at=row.created_at,
        system=row.system,
        generated_by="llm",
    ).model_dump(mode="json")


async def _load_row(db: AsyncSession, sign: str, on: date, system: str) -> DailyHoroscope | None:
    return await db.scalar(
        select(DailyHoroscope).where(
            DailyHoroscope.zodiac_sign == sign, DailyHoroscope.date == on, DailyHoroscope.system == system
        )
    )


async def _generate(sign: str, on: date, system: str) -> dict[str, Any]:
    transit_data = await engine.sign_transit_data(sign, on, system)
    readings, generated_by = await ai.daily_sign(sign, on, transit_data, system)
    number, colour = engine.lucky_for(sign, on)
    if generated_by == "llm":
        async with SessionLocal() as s:
            await s.execute(
                insert(DailyHoroscope)
                .values(
                    id=uuid.uuid4(),
                    zodiac_sign=sign,
                    date=on,
                    system=system,
                    transit_data=transit_data,
                    general_reading=readings["general"],
                    love_reading=readings.get("love") or None,
                    career_reading=readings.get("career") or None,
                    wellness_reading=readings.get("wellness") or None,
                    lucky_number=number,
                    lucky_color=colour,
                )
                .on_conflict_do_nothing(constraint="uq_horoscope_sign_date_system")
            )
            await s.commit()
            row = await _load_row(s, sign, on, system)
        out = _row_out(row)  # type: ignore[arg-type]
        await cache.set_json(_key(sign, on, system), out, _ttl_for(on))
        return out
    out = DailyHoroscopeOut(
        id=uuid.uuid4(),
        zodiac_sign=sign,
        date=on,
        general_reading=readings["general"],
        love_reading=readings.get("love") or None,
        career_reading=readings.get("career") or None,
        wellness_reading=readings.get("wellness") or None,
        lucky_number=number,
        lucky_color=colour,
        transit_data=transit_data,
        created_at=datetime.now(UTC),
        system=system,
        generated_by="template",
    ).model_dump(mode="json")
    await cache.set_json(_key(sign, on, system), out, min(TEMPLATE_TTL_S, _ttl_for(on)))
    return out


async def get_daily(db: AsyncSession, sign: str, on: date, system: str = "western") -> dict[str, Any]:
    key = _key(sign, on, system)
    hit = await cache.get_json(key)
    if hit:
        return hit
    row = await _load_row(db, sign, on, system)
    if row is not None:
        out = _row_out(row)
        await cache.set_json(key, out, _ttl_for(on))
        return out
    await db.commit()  # release the connection before engine/LLM work

    lock_key = f"lock:horoscope:{sign}:{on.isoformat()}:{system}"
    if await cache.acquire_lock(lock_key, LOCK_TTL_S):
        try:
            return await _generate(sign, on, system)
        finally:
            await cache.release_lock(lock_key)
    # Another request is generating: poll the cache, then give up gracefully.
    loop = asyncio.get_running_loop()
    end = loop.time() + WAIT_FOR_PEER_S
    while loop.time() < end:
        await asyncio.sleep(0.5)
        hit = await cache.get_json(key)
        if hit:
            return hit
    raise AIUnavailable("Today's reading is still being prepared. Please try again in a moment.")


async def daily_for_request(
    db: AsyncSession, user: User | None, sign: str | None, requested: date | None, system: str, *, past_days: int
) -> dict[str, Any]:
    s = normalise_sign(sign)
    if system not in SYSTEMS:
        raise BadRequest("Unknown astrology system.", code="VALIDATION_ERROR")
    on = resolve_date(user, requested, past_days=past_days)
    return await get_daily(db, s, on, system)


async def pregenerate(on: date) -> dict[str, int]:
    """Cron: generate all signs x systems for ``on`` (skips existing rows)."""
    done = 0
    for system in SYSTEMS:
        for sign in SIGNS:
            try:
                async with SessionLocal() as s:
                    await get_daily(s, sign, on, system)
                done += 1
            except Exception:  # noqa: BLE001 - one sign failing must not stop the batch
                log.exception("pregen_failed", extra={"sign": sign, "system": system})
    return {"generated_or_present": done, "total": len(SIGNS) * len(SYSTEMS)}
