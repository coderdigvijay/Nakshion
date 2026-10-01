"""chart_data shape (spec section 9), unknown-time path (3.5), published Vedic chart, refresh,
property tests and the performance budget."""

import math
import time as _time
from datetime import date, datetime, time, timezone

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.astrology import ENGINE_VERSION, compute_natal_chart, refresh_time_dependent
from app.astrology.data.signs import RASHIS, SIGNS

NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)
MUMBAI = dict(latitude=19.076, longitude=72.8777, timezone="Asia/Kolkata")
DIGNITIES = {"exalted", "debilitated", "mooltrikona", "own", "friendly", "neutral", "enemy"}


@pytest.fixture(scope="module")
def chart():
    return compute_natal_chart(date_of_birth=date(1994, 7, 21), time_of_birth=time(14, 5),
                               has_exact_time=True, now_utc=NOW, **MUMBAI)


@pytest.fixture(scope="module")
def unknown():
    # 2000-01-05 in Mumbai: Horizons DE441 Moon = 262.169 deg at 00:00 IST (Sagittarius) and
    # 273.988 deg at 23:59 IST (Capricorn); sidereally Jyeshtha -> Mula (retrieved 2026-10-01).
    return compute_natal_chart(date_of_birth=date(2000, 1, 5), time_of_birth=None,
                               has_exact_time=False, now_utc=NOW, **MUMBAI)


def test_top_level_shape(chart):
    for key in ("sun_sign", "moon_sign", "rising_sign", "mc", "planets", "houses", "aspects",
                "metadata", "vedic", "western_summary"):
        assert key in chart
    assert [p["name"] for p in chart["planets"]] == [
        "Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Uranus", "Neptune",
        "Pluto", "North Node", "South Node"]
    assert len(chart["houses"]) == 12
    m = chart["metadata"]
    assert m["engine_version"] == ENGINE_VERSION and m["ephemeris"] == "swieph"
    assert m["utc_datetime"] == "1994-07-21T08:35:00Z" and m["utc_offset_minutes"] == 330
    assert (m["zodiac_western"], m["ayanamsa"], m["node_type_western"], m["node_type_vedic"]) == \
        ("tropical", "lahiri", "true", "mean")


def test_vedic_shape_and_strings(chart):
    v = chart["vedic"]
    assert [p["english"] for p in v["planets"]][:9] == [
        "Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]
    for p in v["planets"] + v["navamsa_d9"]["planets"] + v["dashamsa_d10"]["planets"]:
        assert p["rashi"] in RASHIS and p["rashi_english"] in SIGNS
        assert p["dignity"] in DIGNITIES and 1 <= p["pada"] <= 4 and 1 <= p["house"] <= 12
        assert 0 <= p["degree"] < 30
    rahu = next(p for p in v["planets"] if p["english"] == "Rahu")
    ketu = next(p for p in v["planets"] if p["english"] == "Ketu")
    assert abs((ketu["longitude"] - rahu["longitude"]) % 360 - 180) < 0.02
    assert len(v["house_lords"]) == 12
    assert set(v["dasha"]) >= {"maha_dasha", "antar_dasha", "approximate", "timeline"}
    assert len(v["dasha"]["timeline"]) == 9
    assert {y["name"] for y in v["yogas"]} >= {"Gajakesari Yoga", "Kaal Sarp Dosha", "Mangal Dosha"}


def test_sidereal_equals_tropical_minus_ayanamsa(chart):
    ay = chart["vedic"]["ayanamsa_value"]
    trop = {p["name"]: p["longitude"] for p in chart["planets"]}
    for p in chart["vedic"]["planets"]:
        if p["english"] in trop:
            assert abs(((trop[p["english"]] - ay - p["longitude"]) + 180) % 360 - 180) < 0.011


def test_gandhi_published_vedic_chart():
    """Published Lahiri chart of M.K. Gandhi (e.g. B.V. Raman, "Notable Horoscopes"):
    1869-10-02 07:11 LMT Porbandar (21N37, 69E36; LMT +4:38:24). Lagna Tula; Sun Kanya;
    Moon and Rahu together in Karka (10th); Mars, Mercury, Venus Tula; Jupiter Mesha;
    Saturn Vrishchika; Ketu Makara (4th). Signs only (published sources give whole signs).
    Note: a first draft of this test wrote Rahu Simha / Ketu Kumbha from memory; that is the
    TROPICAL North Node sign (Leo 5.7), not the sidereal one. Rahu is 12 deg inside Karka,
    nowhere near a boundary, so this is a transcription fix, not a tolerance change."""
    c = compute_natal_chart(date_of_birth=date(1869, 10, 2), time_of_birth=time(7, 11),
                            has_exact_time=True, latitude=21 + 37 / 60, longitude=69 + 36 / 60,
                            utc_offset_override=4 * 60 + 38 + 24 / 60, now_utc=NOW)
    signs = {p["english"]: p["rashi"] for p in c["vedic"]["planets"]}
    assert c["vedic"]["lagna"]["rashi"] == "Tula"
    houses = {p["english"]: p["house"] for p in c["vedic"]["planets"]}
    assert (houses["Moon"], houses["Rahu"], houses["Ketu"], houses["Sun"]) == (10, 10, 4, 12)
    assert signs == {**signs, "Sun": "Kanya", "Moon": "Karka", "Mars": "Tula", "Mercury": "Tula",
                     "Venus": "Tula", "Jupiter": "Mesha", "Saturn": "Vrishchika", "Rahu": "Karka",
                     "Ketu": "Makara"}


def test_unknown_time_path(unknown):
    """accuracy rules section 6: no houses, angles, lagna, house-based yogas or vargas."""
    m = unknown["metadata"]
    assert m["approximate_time"] is True and m["house_system"] == "none"
    assert m["houses_available"] is False and m["lagna_basis"] == "none"
    assert m["local_datetime_used"].endswith("T12:00:00")
    assert unknown["rising_sign"] == {"sign": "Unknown", "degree": 0, "approximate": True}
    assert "mc" not in unknown and unknown["houses"] == []
    assert all(p["house"] is None for p in unknown["planets"])
    assert "house" not in unknown["sun_sign"] and "house" not in unknown["moon_sign"]
    assert not any(a["planet1"] in ("ASC", "MC") or a["planet2"] in ("ASC", "MC")
                   for a in unknown["aspects"])
    v = unknown["vedic"]
    assert v["lagna"] is None and v["houses_available"] is False
    assert all(p["house"] is None for p in v["planets"])
    assert v["house_lords"] == [] and v["functional_benefics"] == [] and v["yogakaraka"] is None
    assert "navamsa_d9" not in v and "dashamsa_d10" not in v
    names = {y["name"] for y in v["yogas"]}
    from app.astrology.yogas import LAGNA_DEPENDENT
    assert not names & set(LAGNA_DEPENDENT)
    assert {"Gajakesari Yoga", "Kaal Sarp Dosha", "Mangal Dosha"} <= names
    assert all(y["approximate"] for y in v["yogas"])
    assert all(a["to_house"] is None for a in v["aspects"])
    mg = v["manglik"]
    assert mg["from_lagna"] is None and mg["mars_house_from_lagna"] is None and mg["approximate"]


def test_unknown_time_dasha_everything_approximate(unknown):
    d = unknown["vedic"]["dasha"]
    assert d["approximate"] and "Moon moves" in d["approximate_note"]
    for k in ("maha_dasha", "antar_dasha", "pratyantar_dasha"):
        assert d[k]["approximate"] is True
    assert all(md["approximate"] and all(a["approximate"] for a in md["antar"]) for md in d["timeline"])
    # 2000-01-05 Delhi: Moon 262.2 (Jyeshtha, Mercury) -> 274.0 (Mula, Ketu): two candidates
    # with different starting lords (Horizons Moon longitudes, see fixture comment above).
    assert len(d["candidates"]) == 2 and {c["maha_dasha"] for c in d["candidates"]} == {
        d["candidates"][0]["maha_dasha"], d["candidates"][1]["maha_dasha"]}
    assert d["candidates"][0]["moon_longitude"] != d["candidates"][1]["moon_longitude"]
    assert unknown["vedic"]["suppressed"]["items"]


def test_known_time_chart_has_houses_and_all_yogas(chart):
    assert chart["metadata"]["houses_available"] is True and len(chart["houses"]) == 12
    assert all(isinstance(p["house"], int) for p in chart["planets"])
    assert chart["vedic"]["lagna"] and chart["vedic"]["navamsa_d9"] and chart["vedic"]["house_lords"]


def test_unknown_time_moon_change_flagged(unknown):
    assert unknown["moon_sign"]["approximate"] is True
    assert unknown["moon_sign"]["candidates"] == ["Sagittarius", "Capricorn"]
    nk = unknown["vedic"]["moon_nakshatra"]
    assert nk["approximate"] is True and nk["candidates"] == ["Jyeshtha", "Mula"]


def test_unknown_time_stable_moon_not_flagged():
    c = compute_natal_chart(date_of_birth=date(2000, 1, 7), time_of_birth=None, has_exact_time=False,
                            now_utc=NOW, **MUMBAI)
    assert c["moon_sign"]["approximate"] is False and len(c["moon_sign"]["candidates"]) == 1


def test_inexact_time_marks_angles_only():
    c = compute_natal_chart(date_of_birth=date(1994, 7, 21), time_of_birth=time(14, 0),
                            has_exact_time=False, now_utc=NOW, **MUMBAI)
    assert c["rising_sign"]["approximate"] is True and c["mc"]["approximate"] is True
    assert all(h["approximate"] for h in c["houses"])
    assert c["metadata"]["approximate_time"] is False
    assert c["vedic"]["dasha"]["approximate"] is False


def test_refresh_time_dependent_moves_pointers_without_mutating(chart):
    later = datetime(2040, 1, 1, tzinfo=timezone.utc)
    before = chart["vedic"]["dasha"]["maha_dasha"]["current"]
    out = refresh_time_dependent(chart, later)
    assert chart["vedic"]["dasha"]["maha_dasha"]["current"] == before
    assert out["vedic"]["dasha"]["maha_dasha"]["current"] != before
    assert out["vedic"]["dasha"]["timeline"] == chart["vedic"]["dasha"]["timeline"]
    assert out["metadata"]["snapshot_at"] == "2040-01-01T00:00:00Z"
    md = out["vedic"]["dasha"]["maha_dasha"]
    assert md["start"] <= "2040-01-01" < md["end"]


def test_deterministic(chart):
    again = compute_natal_chart(date_of_birth=date(1994, 7, 21), time_of_birth=time(14, 5),
                                has_exact_time=True, now_utc=NOW, **MUMBAI)
    assert again == chart


def _walk_numbers(x):
    if isinstance(x, dict):
        for v in x.values():
            yield from _walk_numbers(v)
    elif isinstance(x, list):
        for v in x:
            yield from _walk_numbers(v)
    elif isinstance(x, float):
        yield x


@given(
    d=st.dates(min_value=date(1800, 1, 2), max_value=date(2399, 12, 31)),
    hour=st.integers(0, 23), minute=st.integers(0, 59),
    lat=st.floats(-89.9, 89.9), lon=st.floats(-180, 180),
)
@settings(max_examples=40, deadline=None)
def test_property_any_valid_input(d, hour, minute, lat, lon):
    from app.astrology import AstroInputError

    try:
        c = compute_natal_chart(date_of_birth=d, time_of_birth=time(hour, minute), has_exact_time=True,
                                latitude=lat, longitude=lon, timezone="UTC", now_utc=NOW)
    except AstroInputError as e:  # only the UT-range guard may fire, at the extreme edges
        assert e.code == "DATE_OUT_OF_RANGE"
        return
    assert len(c["houses"]) == 12
    assert not any(math.isnan(v) or math.isinf(v) for v in _walk_numbers(c))
    tl = c["vedic"]["dasha"]["timeline"]
    span = date.fromisoformat(tl[-1]["end"]) - date.fromisoformat(tl[0]["start"])
    assert abs(span.days - 120 * 365.25) <= 1
    for p in c["vedic"]["planets"]:
        nine = int(p["longitude"] * 9 // 30) % 12
        d9p = next(x for x in c["vedic"]["navamsa_d9"]["planets"] if x["english"] == p["english"])
        assert abs(nine - RASHIS.index(d9p["rashi"])) in (0, 1, 11)  # 2-dp rounding at a boundary


def test_performance_budget():
    t0 = _time.perf_counter()
    for _ in range(10):
        compute_natal_chart(date_of_birth=date(1994, 7, 21), time_of_birth=time(14, 5),
                            has_exact_time=True, now_utc=NOW, **MUMBAI)
    assert (_time.perf_counter() - t0) / 10 < 0.05


def test_unknown_time_flags_every_planet_that_changes_sign():
    """Delhi 2000-03-20: Sun enters Aries 07:35 UT (13:05 IST). Horizons Sun at 00:00 IST
    (18:30 UT prev day) is 359.9 deg, at 23:59 IST it is 0.1 deg."""
    c = compute_natal_chart(date_of_birth=date(2000, 3, 20), time_of_birth=None, has_exact_time=False,
                            latitude=28.6, longitude=77.2, now_utc=NOW)
    assert c["sun_sign"]["approximate"] is True and c["sun_sign"]["candidates"] == ["Pisces", "Aries"]
    assert c["houses"] == []
    sun = next(p for p in c["planets"] if p["name"] == "Sun")
    assert sun["approximate"] is True
    stable = next(p for p in c["planets"] if p["name"] == "Saturn")
    assert stable["approximate"] is False and "candidates" not in stable
    # every flagged Vedic planet lists >= 2 candidate rashis
    for p in c["vedic"]["planets"]:
        assert p["approximate"] == ("candidates" in p)


def test_north_node_flag_follows_speed_and_mean_convention_kept():
    n = next(p for p in compute_natal_chart(date_of_birth=date(1951, 3, 3), time_of_birth=time(12),
                                             has_exact_time=True, latitude=0, longitude=0,
                                             timezone="UTC", now_utc=NOW)["planets"]
             if p["name"] == "North Node")
    assert n["retrograde"] == (n["speed"] < 0) and n["mean_node_retrograde"] is True


def test_ayanamsa_reported_mean_matches_jagannatha_hora_convention():
    """Lahiri mean ayanamsa at J2000.0 = 23.8571 deg (published; JH). 2000-01-01 12:00 UT."""
    c = compute_natal_chart(date_of_birth=date(2000, 1, 1), time_of_birth=time(12), has_exact_time=True,
                            latitude=0, longitude=0, timezone="UTC", now_utc=NOW)
    assert abs(c["vedic"]["ayanamsa_value"] - 23.8571) <= 0.001
    assert abs(c["vedic"]["ayanamsa_true_value"] - 23.8532) <= 0.001
    assert c["metadata"]["ayanamsa_value_convention"] == "mean"


def test_aware_time_and_naive_now_rejected():
    from app.astrology import AstroInputError
    base = dict(date_of_birth=date(2000, 1, 1), has_exact_time=True, latitude=0, longitude=0)
    for kw in ({"time_of_birth": time(12, tzinfo=timezone.utc)},
               {"time_of_birth": time(12), "now_utc": datetime(2026, 1, 1)},
               {"time_of_birth": time(12), "date_of_birth": datetime(2000, 1, 1)}):
        with pytest.raises(AstroInputError):
            compute_natal_chart(**{**base, **kw})
