"""Vimshottari dasha (spec section 5.2). Pure arithmetic on the sidereal Moon."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone, tzinfo
from typing import Iterator

from .data.grahas import DASHA_ORDER, DASHA_YEAR_DAYS, DASHA_YEARS
from .data.nakshatras import NAKSHATRAS
from .mathutil import norm360

TOTAL_YEARS = 120


def _fmt(dt: datetime, tz: tzinfo | None = None) -> str:
    """Calendar date of an instant in `tz` (the chart's birth zone; UTC when None). A period that
    starts at 05:20 IST must read as that IST date, not the previous UTC date."""
    return dt.astimezone(tz or timezone.utc).date().isoformat()


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _span(start: datetime, end: datetime, tz: tzinfo | None) -> dict:
    """start/end are local calendar dates; *_utc keep the exact instants."""
    return {"start": _fmt(start, tz), "end": _fmt(end, tz),
            "start_utc": _iso(start), "end_utc": _iso(end)}


def _years(y: float, year_days: float) -> timedelta:
    return timedelta(days=y * year_days)


def birth_balance(moon_sid: float) -> tuple[str, float]:
    """(starting lord, elapsed fraction of its period at birth)."""
    x = norm360(moon_sid) * 27.0 / 360.0  # multiply first: exact at nakshatra boundaries
    idx = min(int(x), 26)
    return NAKSHATRAS[idx].lord, x - idx


def _sub_periods(lord: str, start: datetime, total_years: float,
                 year_days: float) -> list[tuple[str, datetime, datetime]]:
    """Antar (or pratyantar) periods of a period of `lord` lasting `total_years`."""
    out = []
    i = DASHA_ORDER.index(lord)
    t = start
    for k in range(9):
        sub = DASHA_ORDER[(i + k) % 9]
        end = t + _years(total_years * DASHA_YEARS[sub] / TOTAL_YEARS, year_days)
        out.append((sub, t, end))
        t = end
    return out


def _mahadashas(moon_sid: float, birth_utc: datetime,
                year_days: float) -> Iterator[tuple[str, datetime, datetime]]:
    """Infinite MD sequence starting at the (virtual) start of the birth mahadasha."""
    lord, elapsed = birth_balance(moon_sid)
    start = birth_utc - _years(elapsed * DASHA_YEARS[lord], year_days)
    i = DASHA_ORDER.index(lord)
    k = 0
    while True:
        md = DASHA_ORDER[(i + k) % 9]
        end = start + _years(DASHA_YEARS[md], year_days)
        yield md, start, end
        start, k = end, k + 1


def timeline(moon_sid: float, birth_utc: datetime, year_days: float = DASHA_YEAR_DAYS,
             tz: tzinfo | None = None) -> list[dict]:
    out = []
    for n, (md, start, end) in enumerate(_mahadashas(moon_sid, birth_utc, year_days)):
        if n == 9:
            break
        out.append({
            "lord": md, **_span(start, end, tz),
            "antar": [{"lord": a, **_span(s, e, tz)}
                      for a, s, e in _sub_periods(md, start, DASHA_YEARS[md], year_days)],
        })
    return out


def current(moon_sid: float, birth_utc: datetime, now_utc: datetime,
            year_days: float = DASHA_YEAR_DAYS, tz: tzinfo | None = None) -> dict:
    """MD / AD / PD running at `now_utc` (before birth: the birth periods)."""
    now = max(now_utc, birth_utc)
    for md, start, end in _mahadashas(moon_sid, birth_utc, year_days):
        if now < end:
            break
    for ad, a_start, a_end in _sub_periods(md, start, DASHA_YEARS[md], year_days):
        if now < a_end:
            break
    ad_years = DASHA_YEARS[md] * DASHA_YEARS[ad] / TOTAL_YEARS
    for pd, p_start, p_end in _sub_periods(ad, a_start, ad_years, year_days):
        if now < p_end:
            break
    return {
        "maha_dasha": {"current": md, **_span(start, end, tz), "duration_years": DASHA_YEARS[md]},
        "antar_dasha": {"current": ad, **_span(a_start, a_end, tz)},
        "pratyantar_dasha": {"current": pd, **_span(p_start, p_end, tz)},
    }


APPROX_NOTE = (
    "Birth time unknown: the chart uses local noon. The Moon moves about 13 degrees (roughly one "
    "whole nakshatra) in a day, so the dasha balance at birth, every period boundary and even the "
    "running Mahadasha lord can differ from this timeline by up to the length of the starting "
    "lord's period (7 to 20 years). Treat dates as indicative only."
)


def mark_approximate(d: dict, moon_range: list[float] | None, birth_utc: datetime | None = None,
                     now_utc: datetime | None = None, year_days: float = DASHA_YEAR_DAYS,
                     tz: tzinfo | None = None) -> dict:
    """Flag every period approximate (unknown birth time) and attach the ambiguity the day's
    Moon motion causes: `candidates` = running MD/AD if the birth were at local 00:00 or 23:59."""
    d["approximate"] = True
    d["approximate_note"] = APPROX_NOTE
    for key in ("maha_dasha", "antar_dasha", "pratyantar_dasha"):
        if key in d:
            d[key]["approximate"] = True
    for md in d.get("timeline", []):
        md["approximate"] = True
        for ad in md["antar"]:
            ad["approximate"] = True
    if moon_range and birth_utc and now_utc:
        cands = []
        for lon in moon_range:
            cur = current(lon, birth_utc, now_utc, year_days, tz)
            cands.append({"moon_longitude": round(norm360(lon), 4),
                          "maha_dasha": cur["maha_dasha"]["current"],
                          "antar_dasha": cur["antar_dasha"]["current"],
                          "balance_at_birth_years": round((1 - birth_balance(lon)[1]) * DASHA_YEARS[birth_balance(lon)[0]], 2)})
        d["candidates"] = cands
    return d


def compute(moon_sid: float, birth_utc: datetime, now_utc: datetime, *, approximate: bool,
            year_days: float = DASHA_YEAR_DAYS, moon_range: list[float] | None = None,
            tz: tzinfo | None = None, tz_name: str | None = None) -> dict:
    """Dates (`start`/`end`) are calendar dates in `tz` (the birth zone); `*_utc` hold the instants."""
    lord, elapsed = birth_balance(moon_sid)
    out = current(moon_sid, birth_utc, now_utc, year_days, tz)
    out.update({
        "approximate": approximate,
        "year_days": year_days,
        "birth_lord": lord,
        "balance_at_birth_years": round((1.0 - elapsed) * DASHA_YEARS[lord], 4),
        # Precise anchor so the service can recompute "current" exactly on read
        # (stored dates are day-rounded; the Moon in vedic.planets is 2-dp rounded).
        "moon_longitude": round(norm360(moon_sid), 6),
        "timeline": timeline(moon_sid, birth_utc, year_days, tz),
        "date_timezone": tz_name or ("UTC" if tz is None else str(tz)),
    })
    if approximate:
        out["moon_range"] = [round(norm360(x), 4) for x in (moon_range or [])]
        mark_approximate(out, moon_range, birth_utc, now_utc, year_days, tz)
    return out
