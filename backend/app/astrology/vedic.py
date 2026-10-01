"""Vedic sidereal layer (spec section 5): planets, dignity, combustion, vargas, house lords,
functional nature, graha drishti. All longitudes here are SIDEREAL (Lahiri)."""

from __future__ import annotations

from dataclasses import dataclass

from .data.grahas import (
    COMBUSTION_ORBS, DIGNITIES, DRISHTI, NATURAL_BENEFICS, NODE_RELATIONSHIP_ROW, RELATIONSHIPS,
)
from .data.nakshatras import NAKSHATRAS
from .data.signs import CLASSICAL, RASHIS, SIGN_LORDS, SIGNS, VEDIC_NAMES, VEDIC_ORDER
from .mathutil import deg2, lon2, norm360, separation, sign_of

KENDRAS = (1, 4, 7, 10)
TRIKONAS = (1, 5, 9)
DUSTHANAS = (6, 8, 12)


@dataclass(frozen=True)
class Graha:
    english: str
    lon: float     # sidereal
    speed: float
    retrograde: bool


def nakshatra_of(sid_lon: float) -> tuple[int, int]:
    """(0-based nakshatra index, pada 1..4). Only valid on sidereal longitudes."""
    # Multiply first: 40/3 is not representable, and `120 // (40/3)` == 8.0 in IEEE floats,
    # which put a body at exactly 0 Leo in Ashlesha 4 instead of Magha 1 (BUG_LEDGER).
    lon = norm360(sid_lon)
    quarter = int(lon * 108.0 / 360.0)  # pada index 0..107; exact at every pada boundary
    quarter = min(quarter, 107)
    return quarter // 4, quarter % 4 + 1


def relationship(planet: str, other: str) -> str:
    """Natural relationship of `planet` toward `other`: friend | neutral | enemy | self."""
    row = NODE_RELATIONSHIP_ROW.get(planet, planet)
    if row == other:
        return "self"
    friends, neutrals, enemies = RELATIONSHIPS[row]
    if other in friends:
        return "friend"
    if other in enemies:
        return "enemy"
    return "neutral"


def dignity(planet: str, sid_lon: float) -> str:
    """Spec 2.4 precedence: exalted > debilitated > mooltrikona > own > friendly/neutral/enemy.
    A node in a sign ruled by its own relationship row (Rahu in Saturn's signs, Ketu in Mars's)
    has no own sign, so it is emitted as "friendly" (a planet is its own friend)."""
    if planet not in DIGNITIES:
        return "neutral"  # Uranus, Neptune, Pluto
    sign, deg = sign_of(sid_lon)
    d = DIGNITIES[planet]
    if sign == d.exalt_sign:
        return "exalted"
    if sign == d.debil_sign:
        return "debilitated"
    if d.mooltrikona and sign == d.mooltrikona[0] and d.mooltrikona[1] <= deg < d.mooltrikona[2]:
        return "mooltrikona"
    if sign in d.own:
        return "own"
    rel = relationship(planet, SIGN_LORDS[sign])
    return {"friend": "friendly", "self": "friendly", "neutral": "neutral", "enemy": "enemy"}[rel]


def is_combust(planet: str, sid_lon: float, sun_lon: float, retrograde: bool) -> bool:
    orbs = COMBUSTION_ORBS.get(planet)
    if orbs is None:
        return False
    return separation(sid_lon, sun_lon) <= (orbs[1] if retrograde else orbs[0])


def d9(sid_lon: float) -> tuple[int, float]:
    """Navamsa sign index and degree (spec 5.3)."""
    x = norm360(sid_lon) * 9.0
    return int(x // 30.0) % 12, x % 30.0


def d10(sid_lon: float) -> tuple[int, float]:
    """Dashamsa: odd signs (even index) start from themselves, even signs from the 9th."""
    s, deg = sign_of(sid_lon)
    part = min(int(deg // 3.0), 9)
    start = s if s % 2 == 0 else s + 8
    return (start + part) % 12, (deg - part * 3.0) * 10.0


def planet_entry(g: Graha, *, house: int, sun_lon: float, rashi_idx: int | None = None,
                 degree: float | None = None, nak_lon: float | None = None) -> dict:
    """VedicPlanet (spec section 9). rashi/degree may be overridden for vargas; nakshatra
    fields always come from the D1 longitude."""
    sign, deg = sign_of(g.lon)
    if rashi_idx is not None:
        sign, deg = rashi_idx, degree if degree is not None else 0.0
    nak, pada = nakshatra_of(nak_lon if nak_lon is not None else g.lon)
    varga_lon = sign * 30.0 + deg
    return {
        "name": VEDIC_NAMES[g.english],
        "english": g.english,
        "rashi": RASHIS[sign],
        "rashi_english": SIGNS[sign],
        "degree": deg2(deg),
        "nakshatra": NAKSHATRAS[nak].name,
        "pada": pada,
        "nakshatra_lord": NAKSHATRAS[nak].lord,
        "house": house,
        "retrograde": g.retrograde,
        "combust": is_combust(g.english, g.lon, sun_lon, g.retrograde),
        "dignity": dignity(g.english, varga_lon),
        "speed": round(g.speed, 4),
        "longitude": lon2(g.lon if rashi_idx is None else varga_lon),
    }


def lagna_entry(lagna_lon: float | None, lagna_sign: int, *, basis: str,
                moon_lon: float | None = None) -> dict:
    if basis == "moon":
        nak, pada = nakshatra_of(moon_lon if moon_lon is not None else lagna_sign * 30.0)
        degree = 0.0
    else:
        assert lagna_lon is not None
        nak, pada = nakshatra_of(lagna_lon)
        degree = sign_of(lagna_lon)[1]
    out = {
        "rashi": RASHIS[lagna_sign], "rashi_english": SIGNS[lagna_sign], "degree": deg2(degree),
        "nakshatra": NAKSHATRAS[nak].name, "pada": pada, "basis": basis,
    }
    if basis == "ascendant":
        out["longitude"] = lon2(lagna_lon)
    return out


def house_from(sign_idx: int, first_sign: int) -> int:
    return (sign_idx - first_sign) % 12 + 1


def house_lords(lagna_sign: int, signs_of: dict[str, int]) -> list[dict]:
    out = []
    for h in range(1, 13):
        sign = (lagna_sign + h - 1) % 12
        lord = SIGN_LORDS[sign]
        lord_sign = signs_of[lord]
        out.append({"house": h, "lord": lord, "lord_in_house": house_from(lord_sign, lagna_sign),
                    "lord_rashi": RASHIS[lord_sign]})
    return out


def owned_houses(planet: str, lagna_sign: int) -> list[int]:
    return [h for h in range(1, 13) if SIGN_LORDS[(lagna_sign + h - 1) % 12] == planet]


def functional_nature(lagna_sign: int, moon_waxing: bool) -> tuple[list[str], list[str], str | None]:
    """Simplified Parashari scoring (spec 5.4). Interpretation choices, documented:
    - house 6 scores -2 (the specific dusthana rule), not -1 -2;
    - house 12 scores 0: the spec's "2 and 12: neutral" rule wins over the parenthetical
      "(and 12)". Otherwise Jupiter (9+12 lord) would be neutral for Aries lagna, contradicting
      every per-lagna table.
    """
    benefics, malefics, yogakaraka = [], [], None
    for planet in CLASSICAL:
        owned = owned_houses(planet, lagna_sign)
        if not owned:
            continue
        natural_benefic = planet in NATURAL_BENEFICS or (planet == "Moon" and moon_waxing)
        score = 0
        for h in owned:
            if h in TRIKONAS:
                score += 2
            elif h in (4, 7, 10):
                score += -1 if natural_benefic else 1
            elif h in (3, 11):
                score -= 1
            elif h == 6:
                score -= 2
            elif h == 8:
                score += 0 if 1 in owned else -2
        if score > 0:
            benefics.append(planet)
        elif score < 0:
            malefics.append(planet)
        kendra = any(h in (4, 7, 10) for h in owned)
        trikona = any(h in (5, 9) for h in owned)
        if kendra and trikona:
            yogakaraka = planet
    return benefics, malefics, yogakaraka


def aspected_signs(planet: str, sign_idx: int) -> list[int]:
    return [(sign_idx + n - 1) % 12 for n in DRISHTI.get(planet, ())]


def graha_drishti(signs_of: dict[str, int], first_sign: int | None) -> list[dict]:
    """first_sign None (unknown birth time): no house numbers, only signs and occupants."""
    out = []
    for planet in CLASSICAL:
        for target in aspected_signs(planet, signs_of[planet]):
            occupants = [p for p in VEDIC_ORDER if p in signs_of and p != planet
                         and signs_of[p] == target and p in CLASSICAL + ("Rahu", "Ketu")]
            out.append({"from": planet,
                        "to_house": None if first_sign is None else house_from(target, first_sign),
                        "to_rashi": RASHIS[target], "to_planets": occupants})
    return out
