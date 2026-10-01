"""Adapter over the pure astrology engine (``app.astrology``, owned by astrology-domain-expert).

This is the ONLY module that imports ``app.astrology``. Every call runs on a dedicated
single-worker executor because pyswisseph keeps global state (astrology-engine.md 3.2) and
must never block the event loop. Engine errors carrying a ``code`` attribute are mapped to
contract error codes; anything else becomes 500 CHART_CALCULATION_FAILED.
"""
from __future__ import annotations

import asyncio
import hashlib
import importlib
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, time
from functools import lru_cache
from types import ModuleType
from typing import Any, Callable

from app.core.errors import ChartCalculationFailed, UpstreamUnavailable, ValidationFailed

log = logging.getLogger("app.engine")

astro_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="astro")

_VALIDATION_CODES = {
    "BIRTH_TIME_NONEXISTENT": "That time didn't exist in {zone} on that date (clocks moved forward). Please check the birth time.",
    "DATE_OUT_OF_RANGE": "Birth date is outside the supported range.",
    "INVALID_LOCATION": "Please choose a valid birth place.",
    "INVALID_TIMEZONE": "We couldn't determine the time zone for that place.",
    "INVALID_INPUT": "Please check the birth details.",
}
_CONTRACT_CODE = {"INVALID_TIMEZONE": "VALIDATION_ERROR", "INVALID_INPUT": "VALIDATION_ERROR"}


class EngineMissing(RuntimeError):
    pass


def _module() -> ModuleType:
    try:
        return importlib.import_module("app.astrology")
    except ImportError as exc:  # engine not landed / broken import
        raise EngineMissing(str(exc)) from exc


def _fn(name: str) -> Callable[..., Any]:
    mod = _module()
    fn = getattr(mod, name, None)
    if fn is None:
        raise EngineMissing(f"app.astrology.{name} not available")
    return fn


async def _run(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(astro_executor, lambda: fn(*args, **kwargs))


def _map_engine_error(exc: Exception, zone: str = "that time zone") -> Exception:
    code = getattr(exc, "code", None)
    if isinstance(code, str) and code in _VALIDATION_CODES:
        # User-facing copy from the contract; the engine's message is technical.
        return ValidationFailed(_VALIDATION_CODES[code].format(zone=zone), code=_CONTRACT_CODE.get(code, code))
    return ChartCalculationFailed()


def engine_available() -> bool:
    try:
        _module()
        return True
    except EngineMissing:
        return False


def engine_version() -> str:
    try:
        return str(getattr(_module(), "ENGINE_VERSION", "0.0.0"))
    except EngineMissing:
        return "0.0.0"


def major(version: str) -> int:
    try:
        return int(str(version).split(".")[0])
    except (ValueError, IndexError):
        return 0


# ------------------------------------------------------------------ time zones
@lru_cache(maxsize=1)
def _tzfinder() -> Any:
    from timezonefinder import TimezoneFinder

    return TimezoneFinder(in_memory=True)


def _resolve_tz_sync(lat: float, lon: float) -> str:
    try:
        fn = getattr(_module(), "resolve_timezone", None)
    except EngineMissing:
        fn = None
    if fn is not None:
        return str(fn(lat, lon))
    tf = _tzfinder()
    zone = tf.timezone_at(lng=lon, lat=lat) or tf.certain_timezone_at(lng=lon, lat=lat)
    if not zone:
        # Open ocean etc.: nearest zone via unique zones within a growing radius is not offered
        # by timezonefinder 8; fall back to the nautical Etc/GMT zone (sign is inverted in IANA).
        offset = round(lon / 15)
        zone = "Etc/GMT" + (f"{-offset:+d}" if offset else "")
    return zone


async def resolve_timezone(lat: float, lon: float) -> str:
    """Server-side IANA zone from coordinates (contract C1 step 5, gap G-05)."""
    try:
        return await _run(_resolve_tz_sync, lat, lon)
    except Exception as exc:  # noqa: BLE001
        raise _map_engine_error(exc) from exc


# ------------------------------------------------------------------ natal charts
async def compute_natal_chart(
    *,
    date_of_birth: date,
    time_of_birth: time | None,
    has_exact_time: bool,
    latitude: float,
    longitude: float,
    timezone: str,
    dst_fold: int | None = None,
    utc_offset_override: int | None = None,
) -> dict[str, Any]:
    try:
        fn = _fn("compute_natal_chart")
    except EngineMissing as exc:
        log.error("engine_missing", extra={"err": str(exc)})
        raise ChartCalculationFailed() from exc
    kwargs: dict[str, Any] = dict(
        date_of_birth=date_of_birth,
        time_of_birth=time_of_birth,
        has_exact_time=has_exact_time,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
    )
    if dst_fold is not None:
        kwargs["dst_fold"] = dst_fold
    if utc_offset_override is not None:
        kwargs["utc_offset_override"] = utc_offset_override
    try:
        data = await _run(fn, **kwargs)
    except Exception as exc:  # noqa: BLE001 - engine boundary; mapped below
        mapped = _map_engine_error(exc, timezone)
        if isinstance(mapped, ChartCalculationFailed):
            log.exception("chart_calculation_failed", extra={"exc_type": type(exc).__name__})
        raise mapped from exc
    if not isinstance(data, dict):
        data = dict(data)  # engine may return a mapping-like model
    return data


async def refresh_time_dependent(chart_data: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    """Recompute dasha 'current' pointers and sade_sati on read (astrology-engine.md 5.2, 9).

    Fail-soft: if the engine lacks the hook or errors, the stored snapshot is returned."""
    try:
        fn = _fn("refresh_time_dependent")
    except EngineMissing:
        return chart_data
    try:
        out = await _run(fn, chart_data, now or datetime.now(UTC))
        return out if isinstance(out, dict) else chart_data
    except Exception:  # noqa: BLE001
        log.warning("refresh_time_dependent_failed")
        return chart_data


# ------------------------------------------------------------------ daily sky
async def sign_transit_data(sign: str, on: date, system: str = "western") -> dict[str, Any]:
    try:
        fn = _fn("sign_transit_data")
    except EngineMissing as exc:
        raise UpstreamUnavailable("Daily sky data is unavailable right now.") from exc
    try:
        return await _run(fn, sign, on, system)
    except Exception as exc:  # noqa: BLE001
        log.exception("sign_transit_failed")
        raise UpstreamUnavailable("Daily sky data is unavailable right now.") from exc


_DAY_RULER_COLOURS = {
    0: ("Silver white", "Pearl"),      # Monday - Moon
    1: ("Red", "Coral"),               # Tuesday - Mars
    2: ("Green", "Emerald green"),     # Wednesday - Mercury
    3: ("Yellow", "Saffron"),          # Thursday - Jupiter
    4: ("Pink", "Rose"),               # Friday - Venus
    5: ("Navy blue", "Indigo"),        # Saturday - Saturn
    6: ("Gold", "Orange"),             # Sunday - Sun
}


def lucky_for(sign: str, on: date) -> tuple[int, str]:
    """Deterministic lucky number/colour (astrology-engine.md 8.3). Uses the engine's if exported."""
    try:
        fn = getattr(_module(), "lucky_for", None)
    except EngineMissing:
        fn = None
    if fn is not None:
        n, c = fn(sign, on)
        return int(n), str(c)
    h = int(hashlib.sha256(f"{sign.lower()}:{on.isoformat()}".encode()).hexdigest(), 16)
    return 1 + (h % 9), _DAY_RULER_COLOURS[on.weekday()][h % 2]


# ------------------------------------------------------------------ personal daily reading (R3)
async def personal_day(chart_data: dict[str, Any], on: date, *, system: str, latitude: float, longitude: float,
                       timezone: str) -> dict[str, Any]:
    """Engine facts for R3: {areas{love,career,wellness,money:{score 1..5}}, key_factors[], timing,
    dasha_context, lucky{number,color}}. Area scores are engine-computed (llm-integration.md 4)."""
    try:
        fn = _fn("personal_day")
    except EngineMissing as exc:
        raise UpstreamUnavailable("Personal readings aren't available yet.") from exc
    try:
        return await _run(fn, chart_data, on, system=system, latitude=latitude, longitude=longitude, timezone=timezone)
    except Exception as exc:  # noqa: BLE001
        log.exception("personal_day_failed")
        raise UpstreamUnavailable("Personal readings aren't available right now.") from exc


# ------------------------------------------------------------------ transits / panchang (C7, C9)
async def transits(chart_data: dict[str, Any], at: datetime, *, with_windows: bool = True) -> dict[str, Any]:
    try:
        fn = _fn("compute_transits")
        return await _run(fn, chart_data, at, with_windows=with_windows)
    except Exception as exc:  # noqa: BLE001
        log.exception("transits_failed")
        raise UpstreamUnavailable("Transit data is unavailable right now.") from exc


async def panchang(day: date, latitude: float, longitude: float, timezone: str | None = None) -> dict[str, Any]:
    try:
        fn = _fn("panchang")
        return await _run(fn, day, latitude, longitude, timezone)
    except Exception as exc:  # noqa: BLE001
        mapped = _map_engine_error(exc, timezone or "that location")
        if isinstance(mapped, ValidationFailed):
            raise mapped from exc
        log.exception("panchang_failed")
        raise UpstreamUnavailable("Panchang data is unavailable right now.") from exc


# ------------------------------------------------------------------ compatibility
async def compute_compatibility(
    chart1: dict[str, Any],
    chart2: dict[str, Any],
    relationship_type: str,
    *,
    self_role: str | None = None,
    partner_role: str | None = None,
) -> dict[str, Any]:
    try:
        fn = _fn("compute_compatibility")
    except EngineMissing as exc:
        log.error("engine_missing", extra={"err": str(exc)})
        raise ChartCalculationFailed() from exc
    try:
        return await _run(fn, chart1, chart2, relationship_type, self_role=self_role, partner_role=partner_role)
    except Exception as exc:  # noqa: BLE001
        log.exception("compatibility_calc_failed", extra={"exc_type": type(exc).__name__})
        raise ChartCalculationFailed() from exc


_self_test_result: bool | None = None


def last_self_test() -> bool:
    """Result of the startup ephemeris self-check (readiness reads this; it never re-runs swe)."""
    return bool(_self_test_result)


async def self_test() -> bool:
    global _self_test_result
    _self_test_result = await _self_test()
    return _self_test_result


async def _self_test() -> bool:
    """Readiness: engine imports and (if exported) its ephemeris self-test passes."""
    try:
        fn = getattr(_module(), "ephemeris_self_check", None)
    except EngineMissing:
        return False
    if fn is None:
        return True
    try:
        await _run(fn)  # raises EphemerisUnavailableError on Moshier fallback
        return True
    except Exception:  # noqa: BLE001
        log.error("ephemeris_self_check_failed")
        return False
