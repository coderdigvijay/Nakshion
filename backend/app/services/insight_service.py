"""Read-only chart insights: transits (C7), Vimshottari timeline (C8), Panchang (C9).

Pure engine output, no LLM. Ownership is checked through chart_service.get_owned (404 for not-yours).
Caches fail open; keys live under the chart's invalidation patterns (transits:{chart_id}:*).
"""
from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFound, ValidationFailed
from app.models import User
from app.services import cache, chart_service, engine, quota_service

TRANSIT_TTL_S = 6 * 3600
PANCHANG_TTL_S = 24 * 3600
PANCHANG_MIN, PANCHANG_MAX = date(1900, 1, 1), date(2100, 12, 31)


def _overlaps(item: dict[str, Any], start: datetime, end: datetime) -> bool:
    ws, we = item.get("window_start"), item.get("window_end")
    if not ws or not we:
        return True
    return ws <= end.strftime("%Y-%m-%dT%H:%M:%SZ") and we >= start.strftime("%Y-%m-%dT%H:%M:%SZ")


async def get_transits(db: AsyncSession, user: User, chart_id: uuid.UUID, start: date | None, days: int) -> dict[str, Any]:
    chart = await chart_service.get_owned(db, user.id, chart_id)
    chart_data = chart.chart_data
    await db.commit()
    start = start or quota_service.local_today(user)
    key = f"transits:{chart_id}:{start.isoformat()}:{days}"
    hit = await cache.get_json(key)
    if hit:
        return hit
    begin = datetime.combine(start, time(12, 0), tzinfo=UTC)
    end = begin + timedelta(days=days)
    raw = await engine.transits(chart_data, begin, with_windows=True)
    out = {
        "chart_id": str(chart_id),
        "from": start.isoformat(),
        "days": days,
        "computed_for": raw.get("computed_for"),
        "western": [t for t in raw.get("western", []) if isinstance(t, dict) and _overlaps(t, begin, end)],
        "vedic": raw.get("vedic", {}),
    }
    await cache.set_json(key, out, TRANSIT_TTL_S)
    return out


async def get_dasha(db: AsyncSession, user: User, chart_id: uuid.UUID, levels: int) -> dict[str, Any]:
    if levels != 2:
        raise ValidationFailed("Only levels=2 (mahadasha and antardasha) is available right now.", code="VALIDATION_ERROR")
    chart = await chart_service.get_owned(db, user.id, chart_id)
    await db.commit()
    data = await engine.refresh_time_dependent(chart.chart_data)  # "current" pointers recomputed on read
    dasha = (data.get("vedic") or {}).get("dasha")
    if not dasha or not dasha.get("timeline"):
        raise NotFound("No dasha timeline for this chart.")
    return {
        "chart_id": str(chart_id),
        "levels": levels,
        "approximate": bool(dasha.get("approximate")),
        "current": {k: dasha.get(k) for k in ("maha_dasha", "antar_dasha", "pratyantar_dasha")},
        "timeline": dasha["timeline"],
    }


def _end_markers(out: dict[str, Any]) -> dict[str, Any]:
    """Add ``end_local_date`` (ISO) and ``end_day_offset`` (0, 1, ...) to tithi/nakshatra/yoga/karana,
    relative to the requested date in the location's zone, so the UI can render "04:27 (+1)"."""
    try:
        zone = ZoneInfo(out["timezone"])
        base = date.fromisoformat(out["date"])
    except (KeyError, ValueError, ZoneInfoNotFoundError):
        return out
    for key in ("tithi", "nakshatra", "yoga", "karana"):
        item = out.get(key)
        if isinstance(item, dict) and item.get("end"):
            local = datetime.fromisoformat(item["end"].replace("Z", "+00:00")).astimezone(zone).date()
            item["end_local_date"] = local.isoformat()
            item["end_day_offset"] = (local - base).days
    return out


def round_coords(lat: float, lon: float) -> tuple[float, float]:
    """The one coordinate convention for Panchang-derived output (/panchang and R3): 0.1 degree."""
    return round(lat, 1), round(lon, 1)


async def get_panchang(day: date, lat: float, lon: float) -> dict[str, Any]:
    if not (PANCHANG_MIN <= day <= PANCHANG_MAX):
        raise ValidationFailed("Please choose a date between 1900 and 2100.", code="DATE_OUT_OF_RANGE")
    if lat == 0 and lon == 0:
        raise ValidationFailed("Please choose a valid location.", code="INVALID_LOCATION")
    rlat, rlon = round_coords(lat, lon)  # contract: cached per (date, lat/lon rounded to 0.1 deg)
    key = f"panchang:{day.isoformat()}:{rlat:.1f}:{rlon:.1f}"
    hit = await cache.get_json(key)
    if hit:
        return hit
    tz = await engine.resolve_timezone(rlat, rlon)
    out = _end_markers(await engine.panchang(day, rlat, rlon, tz))
    await cache.set_json(key, out, PANCHANG_TTL_S)
    return out
