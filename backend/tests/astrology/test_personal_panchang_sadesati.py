"""personal_day contract, Sade Sati dates, panchang determinism."""

from datetime import date, datetime, time, timezone

import pytest

from app.astrology import compute_natal_chart, lucky_for, personal_day, sade_sati_period, panchang

NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)
MUMBAI = dict(latitude=19.076, longitude=72.8777)


@pytest.fixture(scope="module")
def chart():
    return compute_natal_chart(date_of_birth=date(1994, 7, 21), time_of_birth=time(14, 5), has_exact_time=True,
                               timezone="Asia/Kolkata", now_utc=NOW, **MUMBAI)


def day(chart, **kw):
    return personal_day(chart, date(2026, 10, 1), latitude=19.076, longitude=72.8777,
                        timezone="Asia/Kolkata", **kw)


def test_contract_shape(chart):
    r = day(chart, system="vedic")
    assert set(r["areas"]) == {"love", "career", "wellness", "money"}
    assert all(1 <= a["score"] <= 5 and isinstance(a["score"], int) for a in r["areas"].values())
    assert 2 <= len(r["key_factors"]) <= 5
    ids = {f["id"] for f in r["factors"]}
    for kf in r["key_factors"]:
        assert set(kf) == {"factor_id", "label", "weight", "kb_keys", "system"} and kf["factor_id"] in ids
    assert {"V.MD.MOON", "V.AD.VENUS"} <= {k["factor_id"] for k in r["key_factors"]}
    assert r["dasha_context"]["maha"] == "Moon" and r["dasha_context"]["antar"] == "Venus"
    assert r["timing"]["rahu_kaal"] and r["timing"]["best_window"]["reason"]
    assert r["lucky"] == dict(zip(("number", "color"), lucky_for("Sagittarius", date(2026, 10, 1))))


def test_deterministic_and_western(chart):
    assert day(chart, system="vedic") == day(chart, system="vedic")
    w = day(chart, system="western")
    assert w["system"] == "western" and w["moon_transit"]["from"] == "natal Sun sign"


def test_unknown_time_drops_angle_factors_and_flags():
    c = compute_natal_chart(date_of_birth=date(1994, 7, 21), time_of_birth=None, has_exact_time=False,
                            timezone="Asia/Kolkata", now_utc=NOW, **MUMBAI)
    r = day(c, system="vedic")
    assert r["approximate_time"] is True
    assert "META.TIME_UNKNOWN" in {f["id"] for f in r["factors"]}
    assert not any(".N.ASC" in f["id"] or ".N.MC" in f["id"] for f in r["factors"])


def test_polar_has_no_timing_windows(chart):
    r = personal_day(chart, date(2026, 6, 21), system="vedic", latitude=78.22, longitude=15.65,
                     timezone="Arctic/Longyearbyen")
    assert r["timing"] == {}


def test_lucky_for_is_stable_and_in_range():
    n, c = lucky_for("leo", date(2026, 10, 1))
    assert (n, c) == lucky_for("Leo", date(2026, 10, 1)) and 1 <= n <= 9 and c in ("Yellow", "Saffron")


# Saturn's sidereal (Lahiri) ingresses are widely published: Pisces 2025-03-29, Aquarius 2022-04-29
# (e.g. Drik Panchang "Shani Gochar"). A Moon in Aries / Pisces starts Sade Sati then.
@pytest.mark.parametrize("rashi,start", [(0, "2025-03-29"), (11, "2022-04-29")])
def test_sade_sati_start_matches_published_saturn_ingress(rashi, start):
    p = sade_sati_period(rashi, NOW)
    assert p["running"] is True
    assert abs((date.fromisoformat(p["start"]) - date.fromisoformat(start)).days) <= 1


def test_sade_sati_end_includes_retrograde_return():
    """Pisces Moon: Saturn re-enters Mesha 2029-10-08 (retrograde) and finally leaves 2030-04-18
    (checked by a 3-day scan of Saturn's sidereal sign); the period ends then, not 2029-08."""
    p = sade_sati_period(11, NOW)
    assert abs((date.fromisoformat(p["end"]) - date(2030, 4, 18)).days) <= 3


def test_sade_sati_next_period_when_inactive():
    p = sade_sati_period(3, NOW)  # Cancer Moon: starts when Saturn enters Gemini (2032-05-31)
    assert p["running"] is False and p["start"] == "2032-05-31"


def test_refresh_adds_sade_sati_dates(chart):
    from app.astrology import refresh_time_dependent
    ss = refresh_time_dependent(chart, NOW)["vedic"]["sade_sati"]
    assert {"start", "end"} <= set(ss)


def test_panchang_deterministic():
    a = panchang(date(2026, 10, 1), 28.6139, 77.209)
    assert a == panchang(date(2026, 10, 1), 28.6139, 77.209)


def test_one_zodiac_per_reading_vedic_has_no_tropical_ids(chart):
    """Real prefixes: Western T.* (tropical transits) and W.*; Vedic G.* (sidereal gochara), V.*
    (dasha, Sade Sati), P.* (panchang). No cross-over, no outer planets in Vedic, every factor
    carries its system."""
    v = day(chart, system="vedic")
    ids = [f["id"] for f in v["factors"]]
    assert ids and not any(i.startswith(("T.", "W.")) for i in ids)
    assert all(i.startswith(("G.", "V.", "P.", "META.")) for i in ids)
    assert not any(p in i for i in ids for p in ("URANUS", "NEPTUNE", "PLUTO", "ASC", "MC"))
    assert all(f["system"] in ("vedic",) for f in v["factors"] if not f["id"].startswith("META."))
    assert {k["system"] for k in v["key_factors"]} == {"vedic"}
    w = day(chart, system="western")
    wids = [f["id"] for f in w["factors"]]
    assert wids and not any(i.startswith(("G.", "V.", "P.")) for i in wids)
    assert all(f["system"] == "western" for f in w["factors"])
    assert w["dasha_context"] is None


def test_vedic_unknown_time_has_no_lagna_items():
    c = compute_natal_chart(date_of_birth=date(1994, 7, 21), time_of_birth=None, has_exact_time=False,
                            timezone="Asia/Kolkata", now_utc=NOW, **MUMBAI)
    for sy in ("vedic", "western"):
        r = personal_day(c, date(2026, 10, 1), system=sy, latitude=19.076, longitude=72.8777,
                         timezone="Asia/Kolkata")
        assert not any(i["id"].endswith((".N.ASC", ".N.MC", ".N.LAGNA")) for i in r["factors"])


def test_vedic_graha_conjunction_factor_is_sidereal(chart):
    """Natal sidereal Sun 94.58 deg (Karka 4.58). The transiting Sun reaches it around 2026-07-22
    (tropical ~119, Lahiri ayanamsa ~24.2: a day later than the 07-21 tropical return). A tropical comparison would never fire here: the
    tropical natal Sun is 118.37 and the tropical aspect id would be T.SUN.*."""
    r = personal_day(chart, date(2026, 7, 22), system="vedic", latitude=19.076, longitude=72.8777,
                     timezone="Asia/Kolkata")
    ids = {f["id"] for f in r["factors"]}
    assert "G.SUN.CONJ.N.SUN" in ids
    assert not any(i.startswith("T.") for i in ids)
