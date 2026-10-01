"""Nakshion astrology engine: pure Python, no DB / FastAPI / network.

Single source of astrological truth (docs/astrology-engine.md). Services call it; it never
calls services. All swe calls are serialised internally; callers on an asyncio loop should
still run these functions in a worker thread (CPU-bound, ~10-50 ms per natal chart).
"""

from .chart import compute_natal_chart, refresh_time_dependent
from .compatibility import METHOD_VERSION, ashtakoota, compute_compatibility, synastry
from .ephemeris import self_check as ephemeris_self_check
from .errors import AstroInputError, EphemerisUnavailableError
from .timeutil import resolve_birth_time, resolve_timezone
from .transits import compute_transits, find_events, sade_sati, sign_transit_data
from .panchang import panchang
from .personal import lucky_for, personal_day
from .transits import sade_sati_period
from .version import ENGINE_VERSION

__all__ = [
    "ENGINE_VERSION", "METHOD_VERSION",
    "AstroInputError", "EphemerisUnavailableError",
    "compute_natal_chart", "refresh_time_dependent",
    "resolve_timezone", "resolve_birth_time",
    "sign_transit_data", "compute_transits", "sade_sati", "find_events",
    "compute_compatibility", "synastry", "ashtakoota",
    "ephemeris_self_check", "panchang", "personal_day", "lucky_for", "sade_sati_period",
]
