"""Compatibility (spec section 7): Western synastry scoring + Ashtakoota Guna Milan.

Deterministic: the same two chart_data dicts and type always give identical output. The LLM
phrases the seeds; it never chooses or scores them.
"""

from __future__ import annotations

import math

from .data import ashtakoota as AK
from .data.nakshatras import NAKSHATRAS
from .data.signs import ELEMENTS, SIGN_LORDS, sign_index
from .vedic import relationship
from .western import ASPECTS, Point, find_aspect, orb_limit

METHOD_VERSION = "compat-1.1"
# Overall-score bands: the single table shared with the UI (frontend/src/lib/compatBands.tsx is the
# source of truth; tests/astrology/test_compatibility.py parses it and fails on drift).
OVERALL_BANDS = ((8.5, "Exceptional"), (6.5, "Harmonious"), (4.0, "Workable"), (float("-inf"), "Challenging"))


def overall_band(score: float) -> str:
    for floor, label in OVERALL_BANDS:
        if score >= floor:
            return label
    return "Challenging"
SYNASTRY_POINTS = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus",
                   "Neptune", "Pluto", "North Node", "ASC")
CATEGORIES = {
    "emotional": {("Moon", "Moon"), ("Moon", "Sun"), ("Moon", "Venus"), ("Moon", "ASC"), ("Moon", "Saturn")},
    "communication": {("Mercury", "Mercury"), ("Mercury", "Sun"), ("Mercury", "Moon"),
                      ("Mercury", "Jupiter"), ("Mercury", "Saturn")},
    "romance": {("Venus", "Venus"), ("Venus", "Sun"), ("Venus", "Moon"), ("Venus", "Mars"), ("Venus", "ASC")},
    "passion": {("Mars", "Mars"), ("Mars", "Venus"), ("Mars", "Sun"), ("Mars", "Pluto"), ("Mars", "ASC")},
    "long-term": {("Saturn", "Sun"), ("Saturn", "Moon"), ("Saturn", "Venus"), ("Jupiter", "Sun"),
                  ("Jupiter", "Venus"), ("North Node", "Sun"), ("North Node", "Moon"), ("North Node", "Venus")},
}
WEIGHTS = {
    "romantic": {"emotional": 0.25, "communication": 0.2, "romance": 0.2, "passion": 0.15, "long-term": 0.2},
    "other": {"emotional": 0.3, "communication": 0.3, "romance": 0.1, "passion": 0.1, "long-term": 0.2},
}
_ASPECT_H = {"trine": 1.0, "sextile": 0.8, "square": -0.7, "opposition": -0.3}
_HARD = {"Saturn", "Mars", "Pluto"}
_SOFTENERS = {"Venus", "Moon"}
# Pairs where both points are slow/generational (shared by everyone born within months of each
# other) carry no couple-specific information; they are excluded from the top-10 list and the
# strength/challenge seeds (deviation from spec 7.1, which ranks all pairs). They never enter a
# category anyway.
_GENERATIONAL = frozenset({"Uranus", "Neptune", "Pluto", "North Node"})
_COMPLEMENT = {frozenset(("fire", "air")), frozenset(("earth", "water"))}


def _h(aspect: str, p1: str, p2: str) -> float:
    if aspect != "conjunction":
        return _ASPECT_H[aspect]
    if p1 in _HARD or p2 in _HARD:
        other = p2 if p1 in _HARD else p1
        return 0.3 if other in _SOFTENERS else -0.4
    return 0.7


def _points(chart: dict, include_asc: bool) -> list[Point]:
    pts = [Point(p["name"], p["longitude"], p.get("speed", 0.0)) for p in chart["planets"]
           if p["name"] in SYNASTRY_POINTS]
    if include_asc and "longitude" in chart.get("rising_sign", {}):
        pts.append(Point("ASC", chart["rising_sign"]["longitude"], 0.0))
    return pts


def _element_term(sign1: str, sign2: str) -> float:
    e1, e2 = ELEMENTS[sign_index(sign1)], ELEMENTS[sign_index(sign2)]
    return 0.5 if e1 == e2 or frozenset((e1, e2)) in _COMPLEMENT else -0.5


def _time_unknown(chart: dict) -> bool:
    return bool(chart.get("metadata", {}).get("approximate_time"))


def synastry(chart1: dict, chart2: dict, relationship_type: str) -> dict:
    both_known = not _time_unknown(chart1) and not _time_unknown(chart2)
    pairs = []
    for a in _points(chart1, both_known):
        for b in _points(chart2, both_known):
            hit = find_aspect(a, b, reduction=1.0, aspects=ASPECTS)
            if hit is None:
                continue
            name, angle, orb = hit
            max_orb = orb_limit(name, a.name, b.name, reduction=1.0)
            contribution = _h(name, a.name, b.name) * (1.0 - orb / max_orb)
            pairs.append({"planet1": a.name, "planet2": b.name, "aspect": name,
                          "orb": round(orb, 2), "contribution": round(contribution, 4)})

    categories = {}
    for cat, members in CATEGORIES.items():
        total = sum(p["contribution"] for p in pairs
                    if (p["planet1"], p["planet2"]) in members or (p["planet2"], p["planet1"]) in members)
        score = 5.0 + 5.0 * math.tanh(total / 2.0)
        if cat == "emotional":
            score += _element_term(chart1["moon_sign"]["sign"], chart2["moon_sign"]["sign"])
        elif cat == "communication":
            m1 = next(p["sign"] for p in chart1["planets"] if p["name"] == "Mercury")
            m2 = next(p["sign"] for p in chart2["planets"] if p["name"] == "Mercury")
            score += _element_term(m1, m2)
        categories[cat] = {"score": round(max(0.0, min(10.0, score)), 1), "raw": round(total, 4)}

    w = WEIGHTS["romantic" if relationship_type == "romantic" else "other"]
    overall = round(sum(w[c] * categories[c]["score"] for c in w), 1)
    personal = [p for p in pairs if not (p["planet1"] in _GENERATIONAL and p["planet2"] in _GENERATIONAL)]
    ranked = sorted(personal, key=lambda p: (-abs(p["contribution"]), p["planet1"], p["planet2"]))
    positives = sorted((p for p in personal if p["contribution"] > 0), key=lambda p: -p["contribution"])
    negatives = sorted((p for p in personal if p["contribution"] < 0), key=lambda p: p["contribution"])
    return {"categories": categories, "overall_western": overall, "synastry_aspects": ranked[:10],
            "strengths_seeds": positives[:3], "challenges_seeds": negatives[:3],
            "angles_included": both_known}


# --------------------------------------------------------------------------- Ashtakoota

def _moon(chart: dict) -> dict:
    vedic = chart["vedic"]
    m = next(p for p in vedic["planets"] if p["english"] == "Moon")
    nak = next(i for i, n in enumerate(NAKSHATRAS) if n.name == m["nakshatra"])
    return {"rashi": sign_index(m["rashi"]), "degree": m["degree"], "nak": nak,
            "approximate": bool(vedic["moon_nakshatra"].get("approximate"))
            or bool(vedic["moon_nakshatra"].get("rashi_changes"))}


def _moon_from_longitude(lon: float) -> dict:
    from .vedic import nakshatra_of

    lon %= 360.0
    return {"rashi": int(lon // 30) % 12, "degree": lon % 30, "nak": nakshatra_of(lon)[0],
            "approximate": True}


def _moon_variants(chart: dict) -> list[dict]:
    """Moon placements to evaluate: the stored one, plus both ends of the birth day when the
    birth time is unknown (vedic.moon_range_sidereal = local 00:00 and 23:59)."""
    rng = chart["vedic"].get("moon_range_sidereal")
    return [_moon(chart)] + ([_moon_from_longitude(x) for x in rng] if rng else [])


def _graha_maitri(lord_b: str, lord_g: str) -> float:
    if lord_b == lord_g:
        return 5.0
    rels = sorted((relationship(lord_b, lord_g), relationship(lord_g, lord_b)))
    table = {("friend", "friend"): 5.0, ("friend", "neutral"): 4.0, ("neutral", "neutral"): 3.0,
             ("enemy", "friend"): 1.0, ("enemy", "neutral"): 0.5, ("enemy", "enemy"): 0.0}
    return table[tuple(rels)]


def _tara_ok(frm: int, to: int) -> bool:
    count = (to - frm) % 27 + 1
    return count % 9 not in (3, 5, 7)


def guna_milan(bride: dict, groom: dict) -> dict:
    """Bride and groom are `_moon()` dicts. Matrices: data/ashtakoota.py (cited there)."""
    b_nak, g_nak = NAKSHATRAS[bride["nak"]], NAKSHATRAS[groom["nak"]]
    kootas = []

    varna = 1.0 if AK.VARNA_RANK[groom["rashi"]] >= AK.VARNA_RANK[bride["rashi"]] else 0.0
    kootas.append({"name": "Varna", "score": varna, "max": 1,
                   "note": f"temperament (Varna): {AK.VARNA_NAMES[AK.VARNA_RANK[bride['rashi']]]} / "
                           f"{AK.VARNA_NAMES[AK.VARNA_RANK[groom['rashi']]]}"})

    vb = AK.vashya_group(bride["rashi"], bride["degree"])
    vg = AK.vashya_group(groom["rashi"], groom["degree"])
    kootas.append({"name": "Vashya", "score": float(AK.VASHYA_MATRIX[vb][vg]), "max": 2,
                   "note": f"{AK.VASHYA_GROUPS[vb]} / {AK.VASHYA_GROUPS[vg]}"})

    tara = 1.5 * _tara_ok(bride["nak"], groom["nak"]) + 1.5 * _tara_ok(groom["nak"], bride["nak"])
    kootas.append({"name": "Tara", "score": tara, "max": 3, "note": f"{b_nak.name} / {g_nak.name}"})

    yb, yg = AK.YONIS.index(b_nak.yoni), AK.YONIS.index(g_nak.yoni)
    kootas.append({"name": "Yoni", "score": float(AK.YONI_MATRIX[yb][yg]), "max": 4,
                   "note": f"{b_nak.yoni} / {g_nak.yoni}"})

    lb, lg = SIGN_LORDS[bride["rashi"]], SIGN_LORDS[groom["rashi"]]
    kootas.append({"name": "Graha Maitri", "score": _graha_maitri(lb, lg), "max": 5,
                   "note": f"Moon-sign lords {lb} / {lg}"})

    gb, gg = AK.GANAS.index(b_nak.gana), AK.GANAS.index(g_nak.gana)
    gana = float(AK.GANA_MATRIX[gb][gg])
    kootas.append({"name": "Gana", "score": gana, "max": 6, "note": f"{b_nak.gana} / {g_nak.gana}"})

    g_from_b = (groom["rashi"] - bride["rashi"]) % 12 + 1
    b_from_g = (bride["rashi"] - groom["rashi"]) % 12 + 1
    bhakoot_dosha = (g_from_b, b_from_g) in {(2, 12), (12, 2), (5, 9), (9, 5), (6, 8), (8, 6)}
    kootas.append({"name": "Bhakoot", "score": 0.0 if bhakoot_dosha else 7.0, "max": 7,
                   "note": f"Moon signs {g_from_b}/{b_from_g} from each other"})

    nadi_dosha = b_nak.nadi == g_nak.nadi
    kootas.append({"name": "Nadi", "score": 0.0 if nadi_dosha else 8.0, "max": 8,
                   "note": f"{b_nak.nadi} / {g_nak.nadi}"})

    total = sum(k["score"] for k in kootas)
    return {"total": total, "kootas": kootas, "nadi_dosha": nadi_dosha,
            "bhakoot_dosha": bhakoot_dosha,
            # Gana dosha: the matrix gives <= 1 point (a Rakshasa pairing with a non-Rakshasa
            # in the unfavourable direction).
            "gana_dosha": gana <= 1.0}


def _verdict(total: float) -> str:
    if total >= 33:
        return "excellent"
    if total >= 25:
        return "good"
    if total >= 18:
        return "average"
    return "below_average"


TABLES_NOTE = ("Vashya, Gana and Yoni matrices follow one published school (Saravali/Maitreya) and "
               "are NOT yet verified against Prokerala golden pairs; other software may differ by a "
               "point or two on those kootas.")


def _oriented_total(me: dict, partner: dict, self_role: str | None) -> tuple[dict, str, float | None]:
    as_groom = guna_milan(bride=partner, groom=me)
    as_bride = guna_milan(bride=me, groom=partner)
    if self_role == "groom":
        return as_groom, "self_as_groom", None
    if self_role == "bride":
        return as_bride, "self_as_bride", None
    if self_role is None:
        chosen, other = (as_groom, as_bride) if as_groom["total"] <= as_bride["total"] else (as_bride, as_groom)
        return chosen, "unspecified", other["total"]
    raise ValueError("self_role must be 'groom', 'bride' or None")


def ashtakoota(chart_self: dict, chart_partner: dict, self_role: str | None = None) -> dict:
    """Spec 7.2. self_role: "groom" | "bride" | None (compute both, headline = lower).

    All eight kootas derive from the Moon (rashi / nakshatra), so an unknown birth time does not
    remove any koota; it makes the Moon ambiguous. Then `total` is for local noon and
    `total_range` spans the Moon positions at local 00:00 and 23:59 for the unknown chart(s)."""
    me, partner = _moon(chart_self), _moon(chart_partner)
    chosen, orientation, alt = _oriented_total(me, partner, self_role)
    totals = [chosen["total"]]
    for m1 in _moon_variants(chart_self):
        for m2 in _moon_variants(chart_partner):
            totals.append(_oriented_total(m1, m2, self_role)[0]["total"])
    out = {"total": chosen["total"], "max": 36, "kootas": chosen["kootas"], "orientation": orientation,
           "nadi_dosha": chosen["nadi_dosha"], "bhakoot_dosha": chosen["bhakoot_dosha"],
           "gana_dosha": chosen["gana_dosha"], "verdict": _verdict(chosen["total"]),
           "approximate": me["approximate"] or partner["approximate"],
           "tables_source": AK.SOURCE, "tables_fixture_verified": AK.FIXTURE_VERIFIED,
           "tables_note": TABLES_NOTE,
           "total_range": [min(totals), max(totals)]}
    unknown = bool(chart_self["vedic"].get("moon_range_sidereal") or chart_partner["vedic"].get("moon_range_sidereal"))
    if unknown:
        out["approximate"] = True
        out["moon_ambiguous"] = out["total_range"][0] != out["total_range"][1]
        out["note"] = ("Birth time unknown for at least one person: all eight kootas are Moon-based, "
                       "so they are computed for local noon; total_range shows the effect of the "
                       "Moon's movement during the birth day.")
    if alt is not None:
        out["alternate_total"] = alt
    return out


def _breakdown(rt: str, syn: dict, ak: dict | None, overall: float) -> dict:
    w = WEIGHTS["romantic" if rt == "romantic" else "other"]
    scores = {k: v["score"] for k, v in syn["categories"].items()}
    western = syn["overall_western"]
    blend = {"western": 0.5, "ashtakoota": 0.5} if ak is not None else {"western": 1.0, "ashtakoota": 0.0}
    if ak is not None:
        scaled = round(ak["total"] / 36.0 * 10.0, 2)
        formula = "overall = 0.5 x western_overall + 0.5 x (ashtakoota_total / 36 x 10)"
        pull = "Ashtakoota" if scaled < western else "Western synastry"
        explanation = (f"Western synastry weights its five categories into {western} (a weighted mean "
                       f"of the category scores, not an average of the headline numbers). Ashtakoota "
                       f"scores {ak['total']}/36 = {scaled}/10. The overall is their 50/50 blend "
                       f"({overall}), so it can sit below or above individual categories; "
                       f"{pull} is the lower of the two.")
        ak_info = {"included": True, "total": ak["total"], "max": 36, "scaled_0_10": scaled,
                   "orientation": ak["orientation"], "approximate": ak["approximate"],
                   "tables_fixture_verified": AK.FIXTURE_VERIFIED, "tables_note": TABLES_NOTE}
    else:
        formula = "overall = western_overall"
        explanation = (f"Overall {overall} is the weighted mean of the five category scores using the "
                       f"{'romantic' if rt == 'romantic' else 'non-romantic'} weights listed above.")
        ak_info = {"included": False,
                   "reason": ("both charts need Vedic data" if rt == "romantic"
                              else "Ashtakoota (Guna Milan) is a marriage-matching system: romantic pairs only")}
    return {
        "method": METHOD_VERSION, "relationship_type": rt,
        "weighting": "romantic" if rt == "romantic" else "non_romantic",
        "category_weights": w, "category_scores": scores,
        "weighted_contributions": {k: round(w[k] * scores[k], 3) for k in w},
        "western_overall": western, "ashtakoota": ak_info, "blend": blend,
        "formula": formula, "overall": overall, "overall_band": overall_band(overall),
        "explanation": explanation,
        "angles_included": syn["angles_included"],
    }


def compute_compatibility(chart1_data: dict, chart2_data: dict, relationship_type: str, *,
                          self_role: str | None = None, partner_role: str | None = None) -> dict:
    """chart1 = the user's chart, chart2 = partner. Roles are optional ("groom"/"bride");
    if only partner_role is given, self_role is inferred as the other one.

    overall_score is a documented function (see `score_breakdown`): the weighted mean of the five
    category scores (romantic 0.25/0.2/0.2/0.15/0.2, others 0.3/0.3/0.1/0.1/0.2 for emotional/
    communication/romance/passion/long-term), and for romantic pairs with Vedic data a 50/50 blend
    with Ashtakoota total/36 x 10."""
    if relationship_type not in ("romantic", "friend", "family", "coworker"):
        raise ValueError(f"unknown relationship_type {relationship_type!r}")
    if self_role is None and partner_role is not None:
        self_role = {"groom": "bride", "bride": "groom"}.get(partner_role)
    syn = synastry(chart1_data, chart2_data, relationship_type)
    romantic = relationship_type == "romantic"
    ak = manglik = None
    if romantic and chart1_data.get("vedic") and chart2_data.get("vedic"):
        ak = ashtakoota(chart1_data, chart2_data, self_role)
        manglik = {"person1": chart1_data["vedic"].get("manglik"),
                   "person2": chart2_data["vedic"].get("manglik")}
    overall = syn["overall_western"]
    if ak is not None:
        overall = round(0.5 * overall + 0.5 * (ak["total"] / 36.0 * 10.0), 1)
    breakdown = _breakdown(relationship_type, syn, ak, overall)
    if ak is not None and ak["total_range"][0] != ak["total_range"][1]:
        breakdown["overall_range"] = [round(0.5 * syn["overall_western"] + 0.5 * t / 36.0 * 10.0, 1)
                                      for t in ak["total_range"]]
    return {
        "overall_score": overall,
        "overall_band": overall_band(overall),
        "score_breakdown": breakdown,
        "categories": {k: {"score": v["score"]} for k, v in syn["categories"].items()},
        "synastry_aspects": syn["synastry_aspects"],
        "strengths_seeds": syn["strengths_seeds"],
        "challenges_seeds": syn["challenges_seeds"],
        "overall_western": syn["overall_western"],
        "ashtakoota": ak,
        "manglik": manglik,
        "method_version": METHOD_VERSION,
        "approximate": _time_unknown(chart1_data) or _time_unknown(chart2_data),
    }
