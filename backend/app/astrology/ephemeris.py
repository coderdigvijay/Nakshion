"""The only module that touches pyswisseph.

pyswisseph keeps process-global state (ephemeris path, sidereal mode). Every swe call goes
through `_LOCK`, and any state a call depends on is (re)set inside the same locked section, so a
concurrent caller can never observe another caller's mode. The service layer should still run
engine calls off the event loop (a single-worker executor, spec section 3.2).

Sidereal longitudes are computed as `tropical - ayanamsa(Lahiri, true)`, which equals
`calc_ut(..., FLG_SIDEREAL)` to < 1e-12 deg (verified 2026-10-01), so the tropical and sidereal
layers share one ephemeris call per body and can never mix frames.
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import NamedTuple

import swisseph as swe

from .errors import EphemerisUnavailableError

EPHE_DIR = Path(os.environ.get("NAKSHION_EPHE_PATH", Path(__file__).parent / "ephe"))
REQUIRED_FILES = ("sepl_18.se1", "semo_18.se1", "seas_18.se1")
# Data files cover 1800-01-01 .. 2399-12-31 (CE). Inputs are validated to this range.
FLAGS = swe.FLG_SWIEPH | swe.FLG_SPEED

BODY_IDS = {
    "Sun": swe.SUN, "Moon": swe.MOON, "Mercury": swe.MERCURY, "Venus": swe.VENUS,
    "Mars": swe.MARS, "Jupiter": swe.JUPITER, "Saturn": swe.SATURN, "Uranus": swe.URANUS,
    "Neptune": swe.NEPTUNE, "Pluto": swe.PLUTO,
    "TrueNode": swe.TRUE_NODE, "MeanNode": swe.MEAN_NODE,
}

_LOCK = threading.RLock()
_path_set = False


class Position(NamedTuple):
    longitude: float  # tropical, apparent, true equinox of date, [0, 360)
    latitude: float
    speed: float      # deg/day in longitude


def _ensure_path() -> None:
    global _path_set
    if not _path_set:
        missing = [f for f in REQUIRED_FILES if not (EPHE_DIR / f).is_file()]
        if missing:
            raise EphemerisUnavailableError(f"Swiss Ephemeris files missing in {EPHE_DIR}: {missing}")
        swe.set_ephe_path(str(EPHE_DIR))
        _path_set = True


def calc(jd_ut: float, body: str) -> Position:
    with _LOCK:
        _ensure_path()
        xx, retflag = swe.calc_ut(jd_ut, BODY_IDS[body], FLAGS)
    if not retflag & swe.FLG_SWIEPH:
        raise EphemerisUnavailableError(
            f"pyswisseph fell back from SWIEPH (retflag={retflag}) for {body} at jd={jd_ut}"
        )
    return Position(xx[0] % 360.0, xx[1], xx[3])


def ayanamsa_lahiri(jd_ut: float) -> float:
    """True (nutation-including) Lahiri ayanamsa, matching the apparent tropical positions."""
    with _LOCK:
        _ensure_path()
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        retflag, value = swe.get_ayanamsa_ex_ut(jd_ut, swe.FLG_SWIEPH | swe.FLG_SIDEREAL)
    return value


def ayanamsa_lahiri_mean(jd_ut: float) -> float:
    """Mean (nutation-free) Lahiri ayanamsa: the value Jagannatha Hora / Prokerala / published
    tables report (J2000.0: 23.8571 deg). The true value differs by the nutation in longitude
    (<= 0.005 deg). Reported only: positions use the true value (see module docstring)."""
    with _LOCK:
        _ensure_path()
        swe.set_sid_mode(swe.SIDM_LAHIRI)
        return swe.get_ayanamsa_ex_ut(jd_ut, swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_NONUT)[1]


def houses(jd_ut: float, lat: float, lon: float, hsys: bytes) -> tuple[tuple[float, ...], float, float]:
    """Return (12 cusps, ASC, MC), tropical. Raises swe.Error where the system is undefined."""
    with _LOCK:
        _ensure_path()
        cusps, ascmc = swe.houses_ex(jd_ut, lat, lon, hsys)
    return tuple(c % 360.0 for c in cusps[:12]), ascmc[0] % 360.0, ascmc[1] % 360.0


def moon_phase(jd_ut: float) -> float:
    """Illuminated fraction of the Moon's disc, 0..1."""
    with _LOCK:
        _ensure_path()
        attr = swe.pheno_ut(jd_ut, swe.MOON, swe.FLG_SWIEPH)
    return attr[1]


def julday(year: int, month: int, day: int, hour: float) -> float:
    return swe.julday(year, month, day, hour, swe.GREG_CAL)


def self_check() -> dict:
    """Startup / readiness probe. Raises EphemerisUnavailableError on Moshier fallback.

    Reference: Sun at J2000.0 (2000-01-01 12:00 UT) = 280.36891 deg apparent, from JPL
    Horizons DE441 (QUANTITIES=31), retrieved 2026-10-01.
    """
    with _LOCK:
        _ensure_path()
        xx, retflag = swe.calc_ut(2451545.0, swe.SUN, FLAGS)
    if not retflag & swe.FLG_SWIEPH:
        raise EphemerisUnavailableError(f"Moshier fallback active (retflag={retflag})")
    if abs(xx[0] - 280.36891) > 0.001:
        raise EphemerisUnavailableError(f"self-check position off: {xx[0]}")
    return {"ephemeris": "swieph", "retflag": retflag, "swe_version": swe.version,
            "ephe_path": str(EPHE_DIR)}


def sun_rise_set(jd_start: float, lat: float, lon: float, *, rise: bool) -> float | None:
    """First Sun rise/set after `jd_start`: UPPER LIMB with refraction (atpress 1013.25 hPa,
    15 C, sea level), the Drik Panchang convention (verified to the minute on 5 city/dates;
    disc-centre was 1-3 min late at sunrise, see tests/astrology/golden/test_panchang.py).
    None when the Sun does not rise/set (polar day/night, retflag -2)."""
    flag = swe.CALC_RISE if rise else swe.CALC_SET
    with _LOCK:
        _ensure_path()
        ret, tret = swe.rise_trans(jd_start, swe.SUN, flag, (lon, lat, 0.0), 1013.25, 15.0, swe.FLG_SWIEPH)
    return tret[0] if ret == 0 else None
