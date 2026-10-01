"""Compatibility: Ashtakoota hand-worked cases from the spec rules + cited matrices
(app/astrology/data/ashtakoota.py), synastry scoring determinism and contract shape.

NOT a substitute for the spec's 30 Prokerala golden pairs (none available yet): these prove
the rules are wired as written, not that the school-variant matrices match Prokerala.
"""

from datetime import date, datetime, time, timezone

import pytest

from app.astrology import compute_compatibility, compute_natal_chart
from app.astrology.compatibility import guna_milan
from app.astrology.data import ashtakoota as AK

NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)


def moon(rashi: int, degree: float, nak: int) -> dict:
    return {"rashi": rashi, "degree": degree, "nak": nak, "approximate": False}


def scores(result):
    return {k["name"]: k["score"] for k in result["kootas"]}


def test_same_nakshatra_ashwini():
    r = guna_milan(bride=moon(0, 5, 0), groom=moon(0, 5, 0))
    assert scores(r) == {"Varna": 1, "Vashya": 2, "Tara": 3, "Yoni": 4, "Graha Maitri": 5,
                         "Gana": 6, "Bhakoot": 7, "Nadi": 0}
    assert r["total"] == 28 and r["nadi_dosha"] is True and r["bhakoot_dosha"] is False


def test_rohini_bride_jyeshtha_groom_hand_worked():
    """Bride Taurus 15 Rohini (#4), groom Scorpio 20 Jyeshtha (#18):
    Varna Vaishya vs Brahmin -> 1; Vashya Chatushpada(bride) x Keeta(groom) -> 0;
    Tara b->g count 15 (r6 ok) 1.5, g->b count 14 (r5 bad) 0; Yoni Serpent x Deer -> 2;
    Graha Maitri Venus/Mars neutral both ways -> 3; Gana Manushya x Rakshasa -> 0;
    Bhakoot 7/7 -> 7; Nadi Antya vs Adi -> 8. Total 22.5 (average)."""
    r = guna_milan(bride=moon(1, 15, 3), groom=moon(7, 20, 17))
    assert scores(r) == {"Varna": 1, "Vashya": 0, "Tara": 1.5, "Yoni": 2, "Graha Maitri": 3,
                         "Gana": 0, "Bhakoot": 7, "Nadi": 8}
    assert r["total"] == 22.5 and r["gana_dosha"] is True


@pytest.mark.parametrize("b,g,dosha", [(0, 1, True), (0, 4, True), (0, 5, True), (0, 2, False),
                                       (0, 3, False), (0, 6, False)])
def test_bhakoot_pairs(b, g, dosha):
    r = guna_milan(bride=moon(b, 5, 0), groom=moon(g, 5, g * 9 // 4))
    assert r["bhakoot_dosha"] is dosha


def test_yoni_matrix_sworn_enemies_zero_and_same_four():
    for a, b in AK.YONI_ENEMIES:
        i, j = AK.YONIS.index(a), AK.YONIS.index(b)
        assert AK.YONI_MATRIX[i][j] == 0 and AK.YONI_MATRIX[j][i] == 0
    assert all(AK.YONI_MATRIX[i][i] == 4 for i in range(14))
    assert all(len(row) == 14 for row in AK.YONI_MATRIX)


def test_vashya_half_sign_split():
    assert AK.vashya_group(8, 10) == 1 and AK.vashya_group(8, 20) == 0   # Sagittarius
    assert AK.vashya_group(9, 10) == 0 and AK.vashya_group(9, 20) == 2   # Capricorn


@pytest.fixture(scope="module")
def charts():
    a = compute_natal_chart(date_of_birth=date(1994, 7, 21), time_of_birth=time(14, 5), has_exact_time=True,
                            latitude=19.076, longitude=72.8777, timezone="Asia/Kolkata", now_utc=NOW)
    b = compute_natal_chart(date_of_birth=date(1996, 2, 11), time_of_birth=time(6, 40), has_exact_time=True,
                            latitude=28.6139, longitude=77.209, timezone="Asia/Kolkata", now_utc=NOW)
    u = compute_natal_chart(date_of_birth=date(1995, 3, 3), time_of_birth=None, has_exact_time=False,
                            latitude=51.5074, longitude=-0.1278, timezone="Europe/London", now_utc=NOW)
    return a, b, u


def test_contract_shape_and_determinism(charts):
    a, b, _ = charts
    r1 = compute_compatibility(a, b, "romantic")
    assert r1 == compute_compatibility(a, b, "romantic")
    assert set(r1["categories"]) == {"emotional", "communication", "romance", "passion", "long-term"}
    assert all(0 <= v["score"] <= 10 for v in r1["categories"].values())
    assert len(r1["synastry_aspects"]) <= 10 and r1["method_version"] == "compat-1.1"
    for s in r1["synastry_aspects"]:
        assert set(s) == {"planet1", "planet2", "aspect", "orb", "contribution"}
        assert not ({s["planet1"], s["planet2"]} <= {"Uranus", "Neptune", "Pluto", "North Node"})
    ak = r1["ashtakoota"]
    assert ak["orientation"] == "unspecified" and ak["total"] <= ak["alternate_total"]
    assert [k["name"] for k in ak["kootas"]] == ["Varna", "Vashya", "Tara", "Yoni", "Graha Maitri",
                                                 "Gana", "Bhakoot", "Nadi"]
    assert r1["overall_score"] == round(0.5 * r1["overall_western"] + 0.5 * ak["total"] / 36 * 10, 1)
    assert set(r1["manglik"]) == {"person1", "person2"}


def test_roles(charts):
    a, b, _ = charts
    g = compute_compatibility(a, b, "romantic", self_role="groom")["ashtakoota"]
    br = compute_compatibility(a, b, "romantic", partner_role="groom")["ashtakoota"]
    assert g["orientation"] == "self_as_groom" and br["orientation"] == "self_as_bride"
    assert "alternate_total" not in g


def test_non_romantic_has_no_ashtakoota(charts):
    a, b, _ = charts
    r = compute_compatibility(a, b, "coworker")
    assert r["ashtakoota"] is None and r["manglik"] is None
    assert r["overall_score"] == r["overall_western"]


def test_unknown_time_excludes_asc_and_flags(charts):
    a, _, u = charts
    r = compute_compatibility(a, u, "romantic")
    assert r["approximate"] is True
    assert not any("ASC" in (s["planet1"], s["planet2"]) for s in r["synastry_aspects"])


def test_bad_relationship_type(charts):
    a, b, _ = charts
    with pytest.raises(ValueError):
        compute_compatibility(a, b, "enemies")


def test_score_breakdown_reproduces_overall(charts):
    a, b, _ = charts
    for rt in ("romantic", "friend"):
        r = compute_compatibility(a, b, rt)
        sb = r["score_breakdown"]
        w = sb["category_weights"]
        assert sum(w.values()) == pytest.approx(1.0)
        western = round(sum(w[k] * sb["category_scores"][k] for k in w), 1)
        assert western == sb["western_overall"] == r["overall_western"]
        if rt == "romantic":
            blend = round(0.5 * western + 0.5 * sb["ashtakoota"]["total"] / 36 * 10, 1)
            assert blend == sb["overall"] == r["overall_score"] and sb["blend"] == {"western": 0.5, "ashtakoota": 0.5}
            assert sb["ashtakoota"]["tables_fixture_verified"] is False and "NOT yet verified" in sb["ashtakoota"]["tables_note"]
        else:
            assert sb["ashtakoota"]["included"] is False and sb["blend"]["western"] == 1.0
            assert sb["overall"] == r["overall_score"] == western
        assert sb["weighting"] == ("romantic" if rt == "romantic" else "non_romantic")
        assert sb["explanation"] and sb["formula"]


def test_unknown_time_degrades_to_moon_range(charts):
    a, _, u = charts
    r = compute_compatibility(a, u, "romantic")
    ak = r["ashtakoota"]
    assert ak["approximate"] is True and ak["total_range"][0] <= ak["total"] <= ak["total_range"][1]
    assert "Moon-based" in ak["note"] and ak["tables_fixture_verified"] is False
    assert r["manglik"]["person2"]["from_lagna"] is None and r["manglik"]["person2"]["from_moon"] in (True, False)
    assert r["score_breakdown"]["angles_included"] is False


def test_moon_change_day_widens_total_range():
    a = compute_natal_chart(date_of_birth=date(1994, 7, 21), time_of_birth=time(14, 5), has_exact_time=True,
                            latitude=19.076, longitude=72.8777, timezone="Asia/Kolkata", now_utc=NOW)
    u = compute_natal_chart(date_of_birth=date(2000, 1, 5), time_of_birth=None, has_exact_time=False,
                            latitude=28.6, longitude=77.2, now_utc=NOW)  # Moon Jyeshtha -> Mula that day
    ak = compute_compatibility(a, u, "romantic")["ashtakoota"]
    assert ak["moon_ambiguous"] is True and ak["total_range"][0] < ak["total_range"][1]


def test_overall_band_matches_frontend_table():
    """frontend/src/lib/compatBands.tsx is the source of truth: parse its thresholds + labels."""
    import re
    from pathlib import Path

    from app.astrology.compatibility import OVERALL_BANDS, overall_band

    src = (Path(__file__).resolve().parents[3] / "frontend/src/lib/compatBands.tsx").read_text()
    parsed = [(float(t), l) for t, l in re.findall(r"s10 >= ([\d.]+)\) return \{ label: \"(\w+)\"", src)]
    last = re.search(r"return \{ label: \"(\w+)\"[^\n]*\n\}", src).group(1)
    assert parsed == [(t, l) for t, l in OVERALL_BANDS[:-1]] and last == OVERALL_BANDS[-1][1]
    for score, label in [(10, "Exceptional"), (8.5, "Exceptional"), (8.4, "Harmonious"), (6.5, "Harmonious"),
                         (6.4, "Workable"), (4.0, "Workable"), (3.9, "Challenging"), (0, "Challenging")]:
        assert overall_band(score) == label


def test_report_keeps_full_ashtakoota_and_band(charts):
    a, b, _ = charts
    r = compute_compatibility(a, b, "romantic")
    assert r["overall_band"] == r["score_breakdown"]["overall_band"]
    ak = r["ashtakoota"]
    assert {"kootas", "nadi_dosha", "bhakoot_dosha", "gana_dosha", "verdict", "total"} <= set(ak)
    assert ak["verdict"] in ("excellent", "good", "average", "below_average")  # own /36 scale
