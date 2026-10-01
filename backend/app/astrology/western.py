"""Western tropical layer: houses, planets, aspects, summary (spec sections 3.4, 4)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import swisseph as swe

from . import ephemeris
from .data.signs import ELEMENTS, MODALITIES, SIGN_LORDS, SIGNS, WESTERN_PLANETS
from .mathutil import deg2, lon2, norm360, separation, sign_of

# Single orb table (accuracy rules section 7). (angle, default orb, orb with Sun/Moon)
ASPECTS: Final = {
    "conjunction": (0.0, 8.0, 10.0),
    "opposition": (180.0, 8.0, 10.0),
    "trine": (120.0, 7.0, 8.0),
    "square": (90.0, 7.0, 8.0),
    "sextile": (60.0, 5.0, 6.0),
}
OPTIONAL_ASPECTS: Final = {"quincunx": (150.0, 3.0, 3.0), "semi-sextile": (30.0, 2.0, 2.0)}
LUMINARIES: Final = frozenset({"Sun", "Moon"})
ANGLE_POINTS: Final = frozenset({"ASC", "MC"})
ANGLE_ORB_REDUCTION: Final = 2.0
EXACT_ORB: Final = 0.01
POLAR_LATITUDE: Final = 66.0


@dataclass(frozen=True)
class Point:
    name: str
    lon: float
    speed: float  # deg/day


@dataclass(frozen=True)
class HouseResult:
    cusps: tuple[float, ...]
    asc: float
    mc: float
    system: str  # "placidus" | "porphyry_fallback"
    asc_speed: float
    mc_speed: float


def compute_houses(jd_ut: float, lat: float, lon: float) -> HouseResult:
    """Placidus, falling back to Porphyry above 66 deg or wherever SE says Placidus is undefined.

    Placidus is undefined inside the polar circles (some cusps never rise); pyswisseph raises
    swisseph.Error there (verified at lat 70 and 75 on 2026-10-01). PITFALLS #18.
    """
    system, hsys = "placidus", b"P"
    if abs(lat) > POLAR_LATITUDE:
        system, hsys = "porphyry_fallback", b"O"
    try:
        cusps, asc, mc = ephemeris.houses(jd_ut, lat, lon, hsys)
    except swe.Error:
        system, hsys = "porphyry_fallback", b"O"
        cusps, asc, mc = ephemeris.houses(jd_ut, lat, lon, hsys)
    # Angle speeds (deg/day) by finite difference over one hour, for "applying".
    dt = 1.0 / 24.0
    _, asc2, mc2 = ephemeris.houses(jd_ut + dt, lat, lon, b"O")
    asc_speed = ((asc2 - asc + 180.0) % 360.0 - 180.0) / dt
    mc_speed = ((mc2 - mc + 180.0) % 360.0 - 180.0) / dt
    return HouseResult(cusps, asc, mc, system, asc_speed, mc_speed)


def house_of(lon: float, cusps: tuple[float, ...]) -> int:
    """1-based house whose [cusp_i, cusp_i+1) interval contains lon, wrapping at 360."""
    lon = norm360(lon)
    for i in range(12):
        start, end = cusps[i], cusps[(i + 1) % 12]
        span = norm360(end - start)
        if norm360(lon - start) < span or span == 0.0 and lon == start:
            return i + 1
    return 12  # unreachable for valid cusps


def whole_sign_house(lon: float, first_sign: int) -> int:
    return (sign_of(lon)[0] - first_sign) % 12 + 1


def sign_data(lon: float, *, house: int | None = None, approximate: bool | None = None,
              include_longitude: bool = False) -> dict:
    idx, deg = sign_of(lon)
    out: dict = {"sign": SIGNS[idx], "degree": deg2(deg)}
    if house is not None:
        out["house"] = house
    out["element"] = ELEMENTS[idx]
    out["modality"] = MODALITIES[idx]
    if approximate is not None:
        out["approximate"] = approximate
    if include_longitude:
        out["longitude"] = lon2(lon)
    return out


def orb_limit(aspect: str, p1: str, p2: str, *, reduction: float = 0.0) -> float:
    table = ASPECTS.get(aspect) or OPTIONAL_ASPECTS[aspect]
    base = table[2] if (p1 in LUMINARIES or p2 in LUMINARIES) else table[1]
    if p1 in ANGLE_POINTS or p2 in ANGLE_POINTS:
        base -= ANGLE_ORB_REDUCTION
    return base - reduction


def find_aspect(a: Point, b: Point, *, reduction: float = 0.0,
                aspects: dict = ASPECTS) -> tuple[str, float, float] | None:
    """Return (aspect, exact angle, orb) for the tightest aspect in orb, else None."""
    sep = separation(a.lon, b.lon)
    best = None
    for name, (angle, _, _) in aspects.items():
        orb = abs(sep - angle)
        if orb <= orb_limit(name, a.name, b.name, reduction=reduction) and (best is None or orb < best[2]):
            best = (name, angle, orb)
    return best


def is_applying(a: Point, b: Point, angle: float) -> bool:
    """Orb decreases over the next hour (linear motion from speeds)."""
    dt = 1.0 / 24.0
    now = abs(separation(a.lon, b.lon) - angle)
    later = abs(separation(a.lon + a.speed * dt, b.lon + b.speed * dt) - angle)
    return later < now


def aspects_between(points: list[Point]) -> list[dict]:
    out = []
    for i, a in enumerate(points):
        for b in points[i + 1:]:
            if a.name in ANGLE_POINTS and b.name in ANGLE_POINTS:
                continue
            hit = find_aspect(a, b)
            if hit is None:
                continue
            name, angle, orb = hit
            out.append({
                "planet1": a.name, "planet2": b.name, "type": name, "angle": int(angle),
                "orb": round(orb, 2), "applying": is_applying(a, b, angle),
                "exact": orb <= EXACT_ORB,
            })
    out.sort(key=lambda x: x["orb"])  # stable: ties keep canonical body order
    return out


def western_summary(planets: dict[str, Point], asc: float | None, houses_of: dict[str, int]) -> dict:
    """Spec 4.2 (partial v1): element/modality balance, chart ruler, stelliums."""
    weights = {name: (2 if name in LUMINARIES else 1) for name in WESTERN_PLANETS}
    lons = {name: planets[name].lon for name in WESTERN_PLANETS}
    if asc is not None:
        weights["ASC"], lons["ASC"] = 2, asc
    elements = {"fire": 0, "earth": 0, "air": 0, "water": 0}
    modalities = {"cardinal": 0, "fixed": 0, "mutable": 0}
    for name, lon in lons.items():
        idx = sign_of(lon)[0]
        elements[ELEMENTS[idx]] += weights[name]
        modalities[MODALITIES[idx]] += weights[name]
    by_sign: dict[str, list[str]] = {}
    by_house: dict[int, list[str]] = {}
    for name in WESTERN_PLANETS:
        by_sign.setdefault(SIGNS[sign_of(lons[name])[0]], []).append(name)
        if name in houses_of:
            by_house.setdefault(houses_of[name], []).append(name)
    stelliums = [{"sign": s, "planets": p} for s, p in by_sign.items() if len(p) >= 3]
    stelliums += [{"house": h, "planets": p} for h, p in sorted(by_house.items()) if len(p) >= 3]
    return {
        "element_balance": elements,
        "modality_balance": modalities,
        "dominant_element": max(elements, key=lambda k: elements[k]),
        "dominant_modality": max(modalities, key=lambda k: modalities[k]),
        "chart_ruler": SIGN_LORDS[sign_of(asc)[0]] if asc is not None else None,
        "stelliums": stelliums,
    }
