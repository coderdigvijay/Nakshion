"""Birth input -> UTC -> Julian Day (spec section 3.1, accuracy rules section 3).

Local wall time is interpreted in the IANA zone with historical rules (zoneinfo + the pinned
`tzdata` package). Nonexistent local times (DST gaps, skipped days such as Samoa 2011-12-30)
are rejected; ambiguous ones (DST fall-back) use `dst_fold` (default 0 = the earlier, pre-
transition offset) and are flagged.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import ephemeris
from .errors import AstroInputError

# Shipped files (sepl/semo/seas_18) give SWIEPH from 1800-01-01 05:45 UT to 2400-01-07 UT
# (bisected 2026-10-01). Before 05:45 UT on 1800-01-01 pyswisseph silently returns MOSHIER
# (retflag 260). The local-date floor is therefore 1800-01-02, so every offset up to +16 h and
# the unknown-time 00:00 probe stay inside the files; the UT instant is checked as well.
MIN_DATE = date(1800, 1, 2)
MAX_DATE = date(2399, 12, 31)
MIN_UTC = datetime(1800, 1, 1, 6, 0, tzinfo=timezone.utc)
MAX_UTC = datetime(2400, 1, 7, 0, 0, tzinfo=timezone.utc)
UNKNOWN_TIME_DEFAULT = time(12, 0)


@dataclass(frozen=True)
class ResolvedTime:
    local: datetime            # naive local wall time used
    utc: datetime              # aware UTC instant
    jd_ut: float
    timezone: str | None       # IANA name (None when an explicit offset override was used)
    utc_offset_minutes: float
    tz_source: str             # "zoneinfo" | "user_override"
    tz_confidence: str         # "high" | "medium" | "low"
    ambiguous_time: bool


@functools.lru_cache(maxsize=1)
def _finder():
    from timezonefinder import TimezoneFinder

    return TimezoneFinder()


def validate_location(latitude: float, longitude: float) -> None:
    try:
        lat, lon = float(latitude), float(longitude)
    except (TypeError, ValueError):
        raise AstroInputError("INVALID_LOCATION", "latitude/longitude must be numbers") from None
    if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0) or lat != lat or lon != lon:
        raise AstroInputError("INVALID_LOCATION", f"coordinates out of range: {lat}, {lon}")


def resolve_timezone(lat: float, lon: float) -> str:
    """IANA zone for a point. Ocean points return Etc/GMT+-N (nautical zones)."""
    validate_location(lat, lon)
    tf = _finder()
    zone = tf.timezone_at(lng=lon, lat=lat) or tf.certain_timezone_at(lng=lon, lat=lat)
    if not zone:
        # Nautical fallback: 15-degree bands. Etc/GMT signs are inverted by POSIX convention.
        hours = int(round(lon / 15.0))
        zone = "Etc/GMT" if hours == 0 else f"Etc/GMT{-hours:+d}"
    return zone


def _zone(name: str) -> ZoneInfo:
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        raise AstroInputError("INVALID_TIMEZONE", f"unknown IANA time zone: {name!r}") from None


def _confidence(local: datetime, offset: timedelta, tzname: str | None) -> str:
    # LMT-style offsets (not a multiple of 15 min, e.g. Kolkata's 1906 MMT +5:21:10) are
    # best-effort reconstructions in IANA, so they are low confidence regardless of year.
    lmt_like = tzname == "LMT" or offset.total_seconds() % 900 != 0
    if local.year < 1900 or lmt_like:
        return "low"
    if local.year < 1970:
        return "medium"
    return "high"


def to_utc_lenient(naive_local: datetime, zone_name: str) -> datetime:
    """UTC for a wall time without raising on gaps (used for the unknown-time Moon probes)."""
    return naive_local.replace(tzinfo=_zone(zone_name), fold=0).astimezone(timezone.utc)


def _check_utc(utc: datetime) -> datetime:
    if not (MIN_UTC <= utc <= MAX_UTC):
        raise AstroInputError("DATE_OUT_OF_RANGE", f"UT instant {utc.isoformat()} outside ephemeris range")
    return utc


def jd_from_utc(utc: datetime) -> float:
    hour = utc.hour + utc.minute / 60.0 + (utc.second + utc.microsecond / 1e6) / 3600.0
    return ephemeris.julday(utc.year, utc.month, utc.day, hour)


def resolve_birth_time(
    *,
    date_of_birth: date,
    time_of_birth: time | None,
    latitude: float,
    longitude: float,
    timezone_name: str | None = None,
    dst_fold: int = 0,
    utc_offset_override: float | None = None,
) -> ResolvedTime:
    validate_location(latitude, longitude)
    if not (MIN_DATE <= date_of_birth <= MAX_DATE):
        raise AstroInputError(
            "DATE_OUT_OF_RANGE", f"date must be within {MIN_DATE}..{MAX_DATE} (ephemeris range)"
        )
    if dst_fold not in (0, 1):
        raise AstroInputError("INVALID_INPUT", "dst_fold must be 0 or 1")
    local = datetime.combine(date_of_birth, time_of_birth or UNKNOWN_TIME_DEFAULT)
    local = local.replace(tzinfo=None)

    if utc_offset_override is not None:
        minutes = float(utc_offset_override)
        if not -16 * 60 <= minutes <= 16 * 60:
            raise AstroInputError("INVALID_INPUT", "utc_offset_override out of range (+-16h)")
        offset = timedelta(minutes=minutes)
        utc = _check_utc((local - offset).replace(tzinfo=timezone.utc))
        return ResolvedTime(
            local=local, utc=utc, jd_ut=jd_from_utc(utc), timezone=timezone_name,
            utc_offset_minutes=minutes, tz_source="user_override",
            tz_confidence=_confidence(local, offset, None), ambiguous_time=False,
        )

    zone_name = timezone_name or resolve_timezone(latitude, longitude)
    zone = _zone(zone_name)
    aware = local.replace(tzinfo=zone, fold=dst_fold)
    utc = aware.astimezone(timezone.utc)
    # Nonexistent: the round trip local -> UTC -> local changes the wall time.
    if utc.astimezone(zone).replace(tzinfo=None) != local:
        raise AstroInputError(
            "BIRTH_TIME_NONEXISTENT",
            f"{local.isoformat()} does not exist in {zone_name} (clocks skipped it)",
        )
    _check_utc(utc)
    ambiguous = (
        local.replace(tzinfo=zone, fold=0).utcoffset() != local.replace(tzinfo=zone, fold=1).utcoffset()
    )
    offset = aware.utcoffset()
    assert offset is not None
    return ResolvedTime(
        local=local, utc=utc, jd_ut=jd_from_utc(utc), timezone=zone_name,
        utc_offset_minutes=offset.total_seconds() / 60.0, tz_source="zoneinfo",
        tz_confidence=_confidence(local, offset, aware.tzname()), ambiguous_time=ambiguous,
    )


def require_aware(dt: datetime, name: str = "now_utc") -> datetime:
    """Naive datetimes are rejected: astimezone() would silently apply the host time zone."""
    if not isinstance(dt, datetime) or dt.tzinfo is None:
        raise AstroInputError("INVALID_INPUT", f"{name} must be a timezone-aware datetime")
    return dt
