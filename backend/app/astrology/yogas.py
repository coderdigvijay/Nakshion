"""MVP yoga / dosha set (spec section 5.6). Whole-sign houses from the lagna basis.

Strength (spec: dignity, combustion -1 level, kendra/trikona +1 level), made concrete:
  level = round(mean dignity level of participants)  [exalted/mooltrikona/own 2,
          friendly/neutral 1, enemy/debilitated 0]
        - 1 if any participant is combust
        + 1 if every participant sits in a kendra or trikona from the lagna basis
  clamped to 0..2 -> weak / moderate / strong.
"""

from __future__ import annotations

from .data.grahas import DIGNITIES
from .data.signs import CLASSICAL, SIGN_LORDS
from .mathutil import separation
from .vedic import aspected_signs, house_from

STRENGTH = ("weak", "moderate", "strong")
_DIG_LEVEL = {"exalted": 2, "mooltrikona": 2, "own": 2, "friendly": 1, "neutral": 1,
              "enemy": 0, "debilitated": 0}
MAHAPURUSHA = {"Mars": "Ruchaka Yoga", "Mercury": "Bhadra Yoga", "Jupiter": "Hamsa Yoga",
               "Venus": "Malavya Yoga", "Saturn": "Sasa Yoga"}


class YogaContext:
    def __init__(self, planets: dict[str, dict], signs: dict[str, int], lons: dict[str, float],
                 lagna_sign: int | None):
        self.p = planets          # english -> VedicPlanet dict (D1)
        self.sign = signs         # english -> sign index
        self.lon = lons           # english -> sidereal longitude
        self.lagna = lagna_sign

    def house(self, planet: str) -> int:
        return house_from(self.sign[planet], self.lagna)

    def from_moon(self, planet: str) -> int:
        return house_from(self.sign[planet], self.sign["Moon"])

    def lord_of(self, house: int) -> str:
        return SIGN_LORDS[(self.lagna + house - 1) % 12]

    def strength(self, participants: list[str], *, cap: int | None = None) -> str:
        levels = [_DIG_LEVEL[self.p[x]["dignity"]] for x in participants]
        level = round(sum(levels) / len(levels))
        if any(self.p[x]["combust"] for x in participants):
            level -= 1
        if self.lagna is not None and all(self.house(x) in (1, 4, 5, 7, 9, 10) for x in participants):
            level += 1
        level = max(0, min(2, level))
        if cap is not None:
            level = min(level, cap)
        return STRENGTH[level]


def _yoga(name: str, present: bool, strength: str, description: str, factors: list[str]) -> dict:
    return {"name": name, "present": present, "strength": strength if present else "weak",
            "description": description, "factors": factors}


def _mutual_aspect(a: str, b: str, c: YogaContext) -> bool:
    return c.sign[b] in aspected_signs(a, c.sign[a]) and c.sign[a] in aspected_signs(b, c.sign[b])


def _exchange(a: str, b: str, c: YogaContext) -> bool:
    return SIGN_LORDS[c.sign[a]] == b and SIGN_LORDS[c.sign[b]] == a


LAGNA_DEPENDENT = ("Ruchaka Yoga", "Bhadra Yoga", "Hamsa Yoga", "Malavya Yoga", "Sasa Yoga",
                   "Raja Yoga", "Dhana Yoga", "Viparita Raja Yoga", "Neecha Bhanga Raja Yoga")


def compute_yogas(c: YogaContext) -> list[dict]:
    """With `c.lagna is None` (unknown birth time) every lagna/house-based yoga (LAGNA_DEPENDENT)
    is not computed at all and strength ignores house placement; Moon- and sign-based yogas
    remain (the caller labels them approximate)."""
    return _compute_yogas(c)


def _lagna_yogas(c: YogaContext) -> list[dict]:
    """Yogas that need the ascendant (kendra/trikona/dusthana lords, houses from the lagna)."""
    out: list[dict] = []
    up = str.upper
    # Pancha Mahapurusha.
    for planet, name in MAHAPURUSHA.items():
        d = DIGNITIES[planet]
        strong_sign = c.sign[planet] in d.own or c.sign[planet] == d.exalt_sign
        kendra = c.house(planet) in (1, 4, 7, 10)
        present = strong_sign and kendra
        out.append(_yoga(name, present, c.strength([planet]),
                         f"{planet} in its own or exaltation sign and in a kendra from the lagna.",
                         [f"N.{up(planet)}.H{c.house(planet)}"] if present else []))

    # Raja Yoga: kendra lord + trikona lord (different planets) linked.
    kendra_lords = {c.lord_of(h) for h in (1, 4, 7, 10)}
    trikona_lords = {c.lord_of(h) for h in (1, 5, 9)}
    pairs, participants = [], set()
    seen = set()
    for a in sorted(kendra_lords):
        for b in sorted(trikona_lords):
            key = frozenset((a, b))
            if a == b or key in seen:
                continue
            seen.add(key)
            link = ("CONJ" if c.sign[a] == c.sign[b] else "ASPECT" if _mutual_aspect(a, b, c)
                    else "EXCHANGE" if _exchange(a, b, c) else None)
            if link:
                pairs.append(f"Y.RAJA.{up(a)}.{link}.{up(b)}")
                participants.update((a, b))
    out.append(_yoga("Raja Yoga", bool(pairs), c.strength(sorted(participants)) if pairs else "weak",
                     "A kendra lord and a trikona lord are conjunct, in mutual aspect, or exchange signs.",
                     pairs))

    # Dhana Yoga: lord of 2/11 conjunct or exchanging with lord of 1/5/9.
    pairs, participants = [], set()
    for a in sorted({c.lord_of(2), c.lord_of(11)}):
        for b in sorted({c.lord_of(1), c.lord_of(5), c.lord_of(9)}):
            if a == b:
                continue
            link = "CONJ" if c.sign[a] == c.sign[b] else "EXCHANGE" if _exchange(a, b, c) else None
            if link:
                pairs.append(f"Y.DHANA.{up(a)}.{link}.{up(b)}")
                participants.update((a, b))
    out.append(_yoga("Dhana Yoga", bool(pairs), c.strength(sorted(participants)) if pairs else "weak",
                     "A wealth lord (2nd/11th) is joined with a lord of the 1st, 5th or 9th.", pairs))

    # Viparita Raja Yoga: lord of 6/8/12 placed in another of 6/8/12.
    factors, participants = [], set()
    for h in (6, 8, 12):
        lord = c.lord_of(h)
        placed = c.house(lord)
        if placed in (6, 8, 12) and placed != h:
            factors.append(f"Y.VIPARITA.{up(lord)}.L{h}.H{placed}")
            participants.add(lord)
    out.append(_yoga("Viparita Raja Yoga", bool(factors),
                     c.strength(sorted(participants)) if factors else "weak",
                     "A dusthana lord (6th, 8th or 12th) occupies another dusthana.", factors))

    # Neecha Bhanga Raja Yoga.
    factors, participants = [], set()
    for planet in CLASSICAL:
        if c.p[planet]["dignity"] != "debilitated":
            continue
        d = DIGNITIES[planet]
        for helper in {SIGN_LORDS[d.debil_sign], SIGN_LORDS[d.exalt_sign]}:
            if c.house(helper) in (1, 4, 7, 10) or c.from_moon(helper) in (1, 4, 7, 10):
                factors.append(f"Y.NEECHABHANGA.{up(planet)}.{up(helper)}")
                participants.add(planet)
    out.append(_yoga("Neecha Bhanga Raja Yoga", bool(factors),
                     "moderate" if factors else "weak",
                     "A debilitated planet's dispositor or exaltation lord is in a kendra from the lagna or Moon.",
                     factors))
    return out


def _compute_yogas(c: YogaContext) -> list[dict]:
    out: list[dict] = []
    up = str.upper

    # Gajakesari: Jupiter in a kendra from the Moon.
    h = c.from_moon("Jupiter")
    present = h in (1, 4, 7, 10)
    out.append(_yoga("Gajakesari Yoga", present, c.strength(["Jupiter", "Moon"]),
                     f"Jupiter is in house {h} counted from the Moon"
                     + (" (a kendra)." if present else " (not a kendra)."),
                     ["N.JUPITER.KENDRA_FROM_MOON"] if present else []))

    # Budhaditya: Sun and Mercury in one sign; weak if Mercury within 4 deg of the Sun.
    present = c.sign["Sun"] == c.sign["Mercury"]
    close = separation(c.lon["Sun"], c.lon["Mercury"]) <= 4.0
    out.append(_yoga("Budhaditya Yoga", present,
                     "weak" if close else c.strength(["Sun", "Mercury"]),
                     "Sun and Mercury share a sign" + (" (Mercury within 4 deg of the Sun)." if close and present else "."),
                     ["N.SUN.CONJ.MERCURY"] if present else []))

    if c.lagna is not None:
        out.extend(_lagna_yogas(c))

    # Chandra-Mangala: Moon and Mars in one sign.
    present = c.sign["Moon"] == c.sign["Mars"]
    out.append(_yoga("Chandra-Mangala Yoga", present, c.strength(["Moon", "Mars"]),
                     "Moon and Mars share a sign.", ["N.MOON.CONJ.MARS"] if present else []))

    # Kemadruma: no planet (excl. Sun, nodes, outers) in 2nd/12th from the Moon, and none in a
    # kendra from the Moon (cancellation built in). Kendra includes the Moon's own sign.
    others = [p for p in CLASSICAL if p not in ("Sun", "Moon")]
    flank = [p for p in others if c.from_moon(p) in (2, 12)]
    kendra = [p for p in others if c.from_moon(p) in (1, 4, 7, 10)]
    present = not flank and not kendra
    out.append(_yoga("Kemadruma Yoga", present, "moderate",
                     "No planet flanks the Moon (2nd/12th) and none is in a kendra from it."
                     if present else "Not formed: the Moon has planetary support.",
                     ["D.KEMADRUMA"] if present else []))
    return out


def kaal_sarp(c: YogaContext) -> dict:
    rahu, ketu = c.lon["Rahu"], c.lon["Ketu"]

    def between(lon: float, start: float) -> bool:  # strictly within the 180 deg arc from start
        d = (lon - start) % 360.0
        return 0.0 < d < 180.0

    side_a = all(between(c.lon[p], rahu) for p in CLASSICAL)
    side_b = all(between(c.lon[p], ketu) for p in CLASSICAL)
    present = side_a or side_b
    near_node = any(min(separation(c.lon[p], rahu), separation(c.lon[p], ketu)) <= 1.0
                    for p in CLASSICAL)
    return _yoga("Kaal Sarp Dosha", present, "moderate" if near_node else "strong",
                 "All seven classical planets lie on one side of the Rahu-Ketu axis."
                 if present else "Not formed: planets lie on both sides of the Rahu-Ketu axis.",
                 ["D.KAALSARP"] if present else [])


def mangal_dosha(c: YogaContext) -> tuple[dict, dict]:
    """Returns (yoga entry, ManglikResult). Mars in 1/2/4/7/8/12 from the lagna and from the
    Moon. Unknown birth time: only the Moon reference is evaluated (from_lagna is None)."""
    houses = (1, 2, 4, 7, 8, 12)
    h_moon = c.from_moon("Mars")
    from_moon = h_moon in houses
    if c.lagna is None:
        h_lagna, from_lagna = None, None
        refs = ["Moon"] if from_moon else []
        desc = (f"Mars is in house {h_moon} from the Moon; "
                + ("dosha counted from the Moon." if from_moon else "no Mangal Dosha from the Moon.")
                + " Lagna reference unavailable (birth time unknown). Traditional cancellations "
                  "are not evaluated.")
        strength = "moderate"
    else:
        h_lagna = c.house("Mars")
        from_lagna = h_lagna in houses
        refs = [r for r, ok in (("lagna", from_lagna), ("Moon", from_moon)) if ok]
        desc = (f"Mars is in house {h_lagna} from the lagna and house {h_moon} from the Moon; "
                + (f"dosha counted from: {', '.join(refs)}." if refs else "no Mangal Dosha.")
                + " Traditional cancellations are not evaluated.")
        strength = "strong" if from_lagna and from_moon else "moderate"
    present = bool(refs)
    entry = _yoga("Mangal Dosha", present, strength, desc, ["D.MANGAL"] if present else [])
    manglik = {"present": present, "from_lagna": from_lagna, "from_moon": from_moon,
               "mars_house_from_lagna": h_lagna, "mars_house_from_moon": h_moon}
    return entry, manglik
