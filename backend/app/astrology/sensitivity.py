"""Birth-time sensitivity: which chart facts would flip if the birth time were off by a few
minutes (metadata.sensitivity, additive, engine >= 2.1.1).

For each point (Ascendant, Midheaven, Moon; tropical and sidereal; sign and nakshatra-pada
boundaries) the engine looks +-WINDOW minutes around the birth instant. If the sign / pada index
differs anywhere inside the window, the point is "near a cusp" and the crossing instant is
bisected to a second. Positive `minutes_to_boundary` is the distance to the crossing;
`flips_if_birth_time_is` says whether an EARLIER or a LATER true birth time changes the fact.
"""

from __future__ import annotations

from typing import Callable

from . import ephemeris
from .data.nakshatras import NAKSHATRAS
from .data.signs import RASHIS, SIGNS
from .mathutil import norm360

WINDOW_MINUTES = 5.0


def _asc(jd: float, lat: float, lon: float) -> float:
    return ephemeris.houses(jd, lat, lon, b"O")[1]


def _mc(jd: float, lat: float, lon: float) -> float:
    return ephemeris.houses(jd, lat, lon, b"O")[2]


def _idx(lon: float, k: int) -> int:
    """Index of the 360/k-degree cell; multiply first so exact boundaries are exact."""
    return int(norm360(lon) * k / 360.0) % k


def _label(kind: str, idx: int, sidereal: bool) -> str:
    if kind == "sign":
        return (RASHIS if sidereal else SIGNS)[idx]
    return f"{NAKSHATRAS[idx // 4].name} pada {idx % 4 + 1}"


def _crossing(f: Callable[[float], float], k: int, jd: float, side: int, w_days: float) -> float | None:
    """Minutes (signed, + = after jd) to the first cell change on one side, or None."""
    base = _idx(f(jd), k)
    far = jd + side * w_days
    if _idx(f(far), k) == base:
        return None
    lo, hi = jd, far  # base at lo, different at hi
    for _ in range(40):
        mid = (lo + hi) / 2.0
        if _idx(f(mid), k) == base:
            lo = mid
        else:
            hi = mid
    return ((lo + hi) / 2.0 - jd) * 1440.0


def sensitivity(jd_ut: float, lat: float, lon: float, window_minutes: float = WINDOW_MINUTES) -> dict:
    w = window_minutes / 1440.0
    ay = lambda j: ephemeris.ayanamsa_lahiri(j)  # noqa: E731
    sid_asc = lambda j: norm360(_asc(j, lat, lon) - ay(j))  # noqa: E731
    sid_moon = lambda j: norm360(ephemeris.calc(j, "Moon").longitude - ay(j))  # noqa: E731
    # (point, kind, k cells, sidereal?, function)
    points = [
        ("western_ascendant", "sign", 12, False, lambda j: _asc(j, lat, lon)),
        ("western_midheaven", "sign", 12, False, lambda j: _mc(j, lat, lon)),
        ("sidereal_lagna", "sign", 12, True, sid_asc),
        ("sidereal_lagna_pada", "pada", 108, True, sid_asc),
        ("moon_tropical_sign", "sign", 12, False, lambda j: ephemeris.calc(j, "Moon").longitude),
        ("moon_rashi", "sign", 12, True, sid_moon),
        ("moon_nakshatra_pada", "pada", 108, True, sid_moon),
    ]
    near = []
    for name, kind, k, sidereal, f in points:
        hits = [(m, side) for side in (-1, 1) if (m := _crossing(f, k, jd_ut, side, w)) is not None]
        if not hits:
            continue
        m, side = min(hits, key=lambda h: abs(h[0]))
        before = _idx(f(jd_ut), k)
        after = _idx(f(jd_ut + side * w), k)
        near.append({
            "point": name, "kind": kind, "minutes_to_boundary": round(abs(m), 2),
            "flips_if_birth_time_is": "earlier" if m < 0 else "later",
            "from": _label(kind, before, sidereal), "to": _label(kind, after, sidereal),
        })
    flat = {f"{n['point']}_minutes": n["minutes_to_boundary"] for n in near}
    return {
        "window_minutes": window_minutes,
        "near_cusp": near,
        "lagna_near_sign_cusp_minutes": flat.get("sidereal_lagna_minutes"),
        "lagna_near_pada_boundary_minutes": flat.get("sidereal_lagna_pada_minutes"),
        "western_ascendant_near_sign_cusp_minutes": flat.get("western_ascendant_minutes"),
        "moon_near_sign_cusp_minutes": min(
            (v for k2, v in flat.items() if k2 in ("moon_tropical_sign_minutes", "moon_rashi_minutes")),
            default=None),
        "moon_near_pada_boundary_minutes": flat.get("moon_nakshatra_pada_minutes"),
        "robust": not near,
    }
