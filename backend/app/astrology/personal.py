"""R3 personal daily reading facts (spec 6.3-6.4, PRD 6.4). Deterministic: everything the LLM
may narrate (factors, scores, windows, lucky items) is decided here; the LLM writes text only.

Scoring (documented heuristics, covered by tests):
- factor weight (spec 6.4): transit = base(transiting) x base(natal) x (1 - orb/max_orb)^1.5 x
  speed_factor; dasha MD 1.0, AD 0.8; Moon-gochara 0.35.
- area score 1..5 = clamp(round(3 + 2 * tanh(S / 1.0)), 1, 5) with S = sum over factors that
  touch the area of weight * valence (dasha factors count half). No factors -> 3 (neutral).
- best_window = Abhijit Muhurta (the 8th of 15 daytime muhurtas, centred on solar noon),
  dropped when it overlaps Rahu Kaal; no sunrise (polar) -> no windows.
"""

from __future__ import annotations

import hashlib
import math
from datetime import date, datetime, time
from datetime import timezone as _tz
from zoneinfo import ZoneInfo

from .chart import refresh_time_dependent
from .compatibility import _h
from .data.signs import RASHIS, SIGNS, sign_index
from .mathutil import sign_of
from .panchang import panchang
from .timeutil import require_aware, resolve_timezone
from .transits import compute_transits, iso_minute

AREAS = ("love", "career", "wellness", "money")
BASE = {"Sun": 1.0, "Moon": 1.0, "ASC": 1.0, "MC": 1.0, "Saturn": 0.9, "Jupiter": 0.9, "Mars": 0.7,
        "Venus": 0.7, "Mercury": 0.7, "Rahu": 0.8, "Ketu": 0.8, "North Node": 0.8,
        "Uranus": 0.6, "Neptune": 0.6, "Pluto": 0.6}
SPEED = {"Moon": 0.15, "Sun": 0.4, "Mercury": 0.4, "Venus": 0.4, "Mars": 0.4}
TRANSIT_ORB = {"Moon": 3.0, "Sun": 2.0, "Mercury": 2.0, "Venus": 2.0, "Mars": 2.0, "Jupiter": 2.0,
               "Saturn": 2.0, "Uranus": 1.5, "Neptune": 1.5, "Pluto": 1.5}
PLANET_TOPICS = {
    "Sun": ("career", "wellness"), "Moon": ("wellness", "love"), "Mercury": ("career",),
    "Venus": ("love", "money"), "Mars": ("wellness", "love"), "Jupiter": ("money", "career"),
    "Saturn": ("career",), "ASC": ("wellness",), "MC": ("career",), "Rahu": ("career",),
    "Ketu": ("wellness",), "Uranus": ("career",), "Neptune": ("love",), "Pluto": ("money",),
}
# Moon's transit house (counted from the natal Moon / Sun sign) -> topics (spec 6.4 mapping).
HOUSE_TOPICS = {1: ("wellness",), 2: ("money",), 3: ("career",), 4: ("wellness",), 5: ("love",),
                6: ("wellness", "career"), 7: ("love",), 8: ("money",), 9: ("career",), 10: ("career",),
                11: ("money",), 12: ("wellness",)}
GOOD_MOON_HOUSES = (1, 3, 6, 7, 10, 11)  # classical Chandra gochara
LUCKY_COLOURS = {
    0: ("Silver white", "Pearl"), 1: ("Red", "Coral"), 2: ("Green", "Emerald green"),
    3: ("Yellow", "Saffron"), 4: ("Pink", "Rose"), 5: ("Navy blue", "Indigo"), 6: ("Gold", "Orange"),
}


def lucky_for(sign: str, on: date) -> tuple[int, str]:
    """Spec 8.3: deterministic number (sha256) and weekday-ruler colour (2 shades by hash parity)."""
    h = int(hashlib.sha256(f"{sign.lower()}:{on.isoformat()}".encode()).hexdigest(), 16)
    return 1 + (h % 9), LUCKY_COLOURS[on.weekday()][h % 2]


def _kb(*words: str) -> tuple[str, ...]:
    return tuple(w.lower() for w in words)


def _factor(fid, kind, label, topics, weight, valence, window=None, kb=(), system="both"):
    return {"id": fid, "kind": kind, "system": system, "label": label, "topics": sorted(set(topics)),
            "weight": round(weight, 3), "valence": round(valence, 3), "window": window,
            "kb_keys": list(kb)}


def _upper(s: str) -> str:
    return s.upper().replace(" ", "_")


def _local_date(iso_utc: str, zone) -> str:
    """Calendar date of a UTC ISO instant in the viewer/birth zone (not the UTC date)."""
    return datetime.fromisoformat(iso_utc.replace("Z", "+00:00")).astimezone(zone).date().isoformat()


def _transit_factors(trs: list[dict], zone=_tz.utc) -> list[dict]:
    out = []
    for t in trs:
        tp, nat, asp = t["transiting"], t["natal"], t["type"]
        w = (BASE[tp] * BASE[nat] * (1 - t["orb"] / TRANSIT_ORB[tp]) ** 1.5 * SPEED.get(tp, 1.0))
        win = None
        if t.get("window_start") and t.get("window_end"):
            win = [_local_date(t["window_start"], zone), _local_date(t["window_end"], zone)]
        word = "applying" if t["applying"] else "separating"
        out.append(_factor(
            f"T.{_upper(tp)}.{_upper(asp)}.N.{_upper(nat)}", "transit",
            f"Transiting {tp} {asp} natal {nat} (orb {t['orb']:.1f}°, {word})",
            PLANET_TOPICS.get(tp, ()) + PLANET_TOPICS.get(nat, ()), w, _h(asp, tp, nat), win,
            _kb(f"{tp} {nat} {asp} transit", f"{tp} transit"), "western"))
    return out


# Vedic transit factors (sidereal, nine grahas only). Id prefixes: G.* = gochara/graha transit,
# V.* = dasha/sade sati, P.* = panchang. Western ids: T.*, W.*. Never mixed in one reading.
GRAHAS = ("Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu")
VEDIC_NATAL = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Rahu", "Ketu")
BENEFIC_GRAHAS = {"Jupiter", "Venus", "Mercury", "Moon"}
GOOD_GOCHARA = {"Jupiter": (2, 5, 7, 9, 11), "Saturn": (3, 6, 11), "Rahu": (3, 6, 11), "Ketu": (3, 6, 11)}
VEDIC_ORB = 2.0


def _vedic_factors(chart: dict, trs_vedic: dict, at_utc, on: date) -> list[dict]:
    from . import ephemeris
    from .mathutil import norm360, separation
    from .timeutil import jd_from_utc

    vedic = chart["vedic"]
    jd = jd_from_utc(at_utc)
    ay = ephemeris.ayanamsa_lahiri(jd)
    sid = {n: norm360(ephemeris.calc(jd, n).longitude - ay) for n in ("Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")}
    sid["Rahu"] = norm360(ephemeris.calc(jd, "MeanNode").longitude - ay)
    sid["Ketu"] = norm360(sid["Rahu"] + 180.0)
    speed = {n: ephemeris.calc(jd, n).speed for n in ("Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn")}
    natal = {p["english"]: p["longitude"] for p in vedic["planets"] if p["english"] in VEDIC_NATAL}
    if vedic.get("lagna") and "longitude" in vedic["lagna"]:
        natal["Lagna"] = vedic["lagna"]["longitude"]
    out = []
    for g in GRAHAS:
        for n, nlon in natal.items():
            sep = separation(sid[g], nlon)
            for kind, ang in (("CONJUNCTION", 0.0), ("OPPOSITION", 180.0)):
                orb = abs(sep - ang)
                if orb > VEDIC_ORB:
                    continue
                w = (BASE[g] * BASE.get(n, 1.0) * (1 - orb / VEDIC_ORB) ** 1.5 * (0.4 if g in SPEED else 1.0))
                val = (0.6 if g in BENEFIC_GRAHAS else -0.4) * (1.0 if ang == 0.0 else 0.5)
                nlabel = "Lagna" if n == "Lagna" else n
                out.append(_factor(
                    f"G.{_upper(g)}.{kind[:4]}.N.{_upper(n)}", "transit",
                    f"Transiting {g} {'conjunct' if ang == 0.0 else 'opposite (7th aspect)'} natal {nlabel} "
                    f"(sidereal, orb {orb:.1f}\u00b0)",
                    PLANET_TOPICS.get(g, ()) + PLANET_TOPICS.get(n, ("wellness",)), w, val, None,
                    _kb(f"{g} {n} conjunction gochara" if ang == 0.0 else f"{g} {n} opposition gochara",
                        f"{g} gochara"), "vedic"))
    for gc in trs_vedic["gochara"]:
        g, h = gc["planet"], gc["house_from_moon"]
        good = h in GOOD_GOCHARA[g]
        out.append(_factor(f"G.{_upper(g)}.H{h}", "transit",
                           f"Transiting {g} in {gc['rashi']}, house {h} from your natal Moon (gochara)",
                           HOUSE_TOPICS[h], BASE[g] * 0.5, 0.5 if good else -0.3, None,
                           _kb(f"{g} gochara house {h}", f"{g} transit from moon"), "vedic"))
    return out


def personal_day(chart_data: dict, on: date, *, system: str = "vedic", latitude: float,
                 longitude: float, timezone: str | None = None) -> dict:
    """Facts for R3. Keys: date, system, approximate_time, areas{love,career,wellness,money:
    {score 1..5}}, key_factors[{factor_id,label,weight,kb_keys}] (<=5, strongest first, current
    MD/AD included for vedic), factors[...] (full list with kind/topics/valence/window),
    timing{best_window?,rahu_kaal?}, dasha_context?, moon_transit, panchang, lucky{number,color}."""
    if system not in ("vedic", "western"):
        raise ValueError("system must be 'vedic' or 'western'")
    tzname = timezone or chart_data["metadata"].get("timezone") or resolve_timezone(latitude, longitude)
    zone = ZoneInfo(tzname)
    at = datetime.combine(on, time(12, 0), tzinfo=zone).astimezone(_tz.utc)
    chart = refresh_time_dependent(chart_data, at)
    approx = bool(chart["metadata"].get("approximate_time"))
    vedic = chart.get("vedic")
    pan = panchang(on, latitude, longitude, tzname)
    trs = compute_transits(chart, at, with_windows=True)

    if system == "vedic" and not vedic:
        raise ValueError("vedic reading needs chart_data['vedic']")
    # One zodiac per reading: Western = tropical T.*/W.* factors, Vedic = sidereal G.*/V.*/P.*.
    factors = _transit_factors(trs["western"], zone) if system == "western" else \
        _vedic_factors(chart, trs["vedic"], at, on)

    # Moon's transit house: vedic from the natal Moon rashi, western from the natal Sun sign.
    if system == "vedic":
        base_sign = sign_index(next(p["rashi"] for p in vedic["planets"] if p["english"] == "Moon"))
        moon_sign = sign_index(trs["vedic"]["moon_transit_rashi"])
        basis, names = "natal Moon", RASHIS
    else:
        base_sign = sign_index(chart["sun_sign"]["sign"])
        sky = compute_moon_tropical(at)
        moon_sign, basis, names = sky, "natal Sun sign", SIGNS
    house = (moon_sign - base_sign) % 12 + 1
    factors.append(_factor(
        f"{'G' if system == 'vedic' else 'T'}.MOON.H{house}", "transit",
        f"Transiting Moon in house {house} from your {basis} ({names[moon_sign]})",
        HOUSE_TOPICS[house], 0.35, 0.6 if house in GOOD_MOON_HOUSES else -0.4,
        [on.isoformat(), on.isoformat()], _kb(f"moon transit house {house}", "moon gochara"),
        system))

    dasha_context = None
    if system == "vedic":
        d = vedic["dasha"]
        md, ad = d["maha_dasha"]["current"], d["antar_dasha"]["current"]
        fn = set(vedic.get("functional_benefics", [])), set(vedic.get("functional_malefics", []))
        for level, lord, w in (("MD", md, 1.0), ("AD", ad, 0.8)):
            val = 0.5 if lord in fn[0] else -0.3 if lord in fn[1] else 0.0
            span = d["maha_dasha" if level == "MD" else "antar_dasha"]
            factors.append(_factor(
                f"V.{level}.{_upper(lord)}", "dasha",
                f"{lord} {'Mahadasha' if level == 'MD' else 'Antardasha'} "
                f"({span['start']} to {span['end']})", PLANET_TOPICS.get(lord, ()), w, val,
                [span["start"], span["end"]], _kb(f"{lord} dasha", f"{lord} {'mahadasha' if level == 'MD' else 'antardasha'}"),
                "vedic"))
        dasha_context = {"maha": md, "antar": ad,
                         "note": f"{md} Mahadasha until {d['maha_dasha']['end']}, {ad} Antardasha until "
                                 f"{d['antar_dasha']['end']}" + (" (approximate: birth time unknown)" if d.get("approximate") else "")}
        ss = vedic.get("sade_sati", {})
        if ss.get("active"):
            factors.append(_factor(f"V.SADESATI.{ss['phase'].upper()}", "dosha",
                                   f"Sade Sati ({ss['phase']} phase): Saturn in {ss['saturn_rashi']}",
                                   ("career", "wellness"), 0.9, -0.5,
                                   [ss["start"], ss["end"]] if ss.get("start") else None,
                                   _kb("sade sati", f"sade sati {ss['phase']}"), "vedic"))
    if system == "vedic":
          factors.append(_factor(f"P.TITHI.{_upper(pan['tithi']['name'])}", "panchang",
                               f"Tithi: {pan['tithi']['paksha']} {pan['tithi']['name']}", ("spiritual",),
                               0.1, 0.0, None, _kb(f"{pan['tithi']['name']} tithi"), "vedic"))
          factors.append(_factor(f"P.NAKSHATRA.{_upper(pan['nakshatra']['name'])}", "panchang",
                               f"Moon's nakshatra today: {pan['nakshatra']['name']}", ("self",), 0.1, 0.0,
                               None, _kb(f"{pan['nakshatra']['name']} nakshatra"), "vedic"))
    else:
        factors.append(_factor(f"W.NATAL.SUN.{_upper(chart['sun_sign']['sign'])}", "natal",
                               f"Natal Sun in {chart['sun_sign']['sign']} (tropical)", ("self",), 0.1, 0.0,
                               None, _kb(f"sun in {chart['sun_sign']['sign']}"), "western"))
    if approx:
        factors.append(_factor("META.TIME_UNKNOWN", "natal",
                               "Birth time unknown: house, ascendant and exact dasha timing are approximate",
                               ("timing",), 0.05, 0.0, None, (), system))

    # Deterministic ordering: weight desc, then id.
    factors.sort(key=lambda f: (-f["weight"], f["id"]))
    areas = {}
    for area in AREAS:
        s = sum(f["weight"] * f["valence"] * (0.5 if f["kind"] == "dasha" else 1.0)
                for f in factors if area in f["topics"])
        areas[area] = {"score": max(1, min(5, round(3 + 2 * math.tanh(s / 1.0))))}

    mandatory = [f for f in factors if f["id"].startswith(("V.MD.", "V.AD."))]
    rest = [f for f in factors if f not in mandatory and f["kind"] != "panchang"
            and f["id"] != "META.TIME_UNKNOWN"]
    chosen = (mandatory + rest)[:5] if len(mandatory) < 5 else mandatory[:5]
    if len(chosen) < 2:  # contract: >= 2 key factors; fall back to panchang / natal factors
        chosen += [f for f in factors if f["kind"] in ("panchang", "natal") and f not in chosen
                   and f["id"] != "META.TIME_UNKNOWN"][: 2 - len(chosen)]
    chosen.sort(key=lambda f: (-f["weight"], f["id"]))
    key_factors = [{"factor_id": f["id"], "label": f["label"], "weight": f["weight"],
                    "kb_keys": f["kb_keys"], "system": f["system"]} for f in chosen]

    timing: dict = {}
    if pan["rahu_kaal"]:
        timing["rahu_kaal"] = {"start": pan["rahu_kaal"]["start"], "end": pan["rahu_kaal"]["end"]}
    if pan["sunrise"] and pan["sunset"]:
        rise = datetime.fromisoformat(pan["sunrise"].replace("Z", "+00:00"))
        sset = datetime.fromisoformat(pan["sunset"].replace("Z", "+00:00"))
        muhurta = (sset - rise) / 15
        a, b = rise + muhurta * 7, rise + muhurta * 8
        rk = pan["rahu_kaal"]
        r0 = datetime.fromisoformat(rk["start"].replace("Z", "+00:00"))
        r1 = datetime.fromisoformat(rk["end"].replace("Z", "+00:00"))
        if b <= r0 or a >= r1:
            timing["best_window"] = {"start": a.strftime("%Y-%m-%dT%H:%M:00Z"),
                                     "end": b.strftime("%Y-%m-%dT%H:%M:00Z"),
                                     "reason": "Abhijit Muhurta (midday, traditionally auspicious)"}

    sign_for_lucky = (chart["moon_sign"]["sign"] if system == "vedic" and vedic is None else
                      next(p["rashi_english"] for p in vedic["planets"] if p["english"] == "Moon")
                      if system == "vedic" else chart["sun_sign"]["sign"])
    num, colour = lucky_for(sign_for_lucky, on)
    return {
        "date": on.isoformat(), "system": system, "approximate_time": approx,
        "areas": areas, "key_factors": key_factors, "factors": factors, "timing": timing,
        "dasha_context": dasha_context,
        "moon_transit": {"house": house, "from": basis, "sign": names[moon_sign]},
        "panchang": {"system": "vedic (sidereal)", "vara": pan["vara"], "tithi": pan["tithi"]["name"], "paksha": pan["tithi"]["paksha"],
                     "nakshatra": pan["nakshatra"]["name"], "yoga": pan["yoga"]["name"],
                     "karana": pan["karana"]["name"]},
        "lucky": {"number": num, "color": colour},
    }


def compute_moon_tropical(at_utc: datetime) -> int:
    from . import ephemeris
    from .timeutil import jd_from_utc

    return sign_of(ephemeris.calc(jd_from_utc(require_aware(at_utc)), "Moon").longitude)[0]
