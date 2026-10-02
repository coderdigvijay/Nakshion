"""Vimshottari dasha arithmetic (spec 5.2). Expected dates are hand-computed (shown inline)."""

from datetime import datetime, timedelta, timezone

import pytest

from app.astrology import dasha

BIRTH = datetime(2000, 1, 1, 0, 0, tzinfo=timezone.utc)


def test_moon_at_ashwini_start_full_ketu_balance():
    lord, elapsed = dasha.birth_balance(0.0)
    assert (lord, elapsed) == ("Ketu", 0.0)
    tl = dasha.timeline(0.0, BIRTH)
    # Ketu MD = 7 * 365.25 d = 2556.75 d -> 2006-12-31T18:00Z
    assert tl[0] == {**tl[0], "lord": "Ketu", "start": "2000-01-01", "end": "2006-12-31"}
    # Ketu/Ketu AD = 7*7/120 y = 149.14 d -> 2000-05-29
    assert tl[0]["antar"][0] == {"lord": "Ketu", "start": "2000-01-01", "end": "2000-05-29",
                                 "start_utc": "2000-01-01T00:00:00Z", "end_utc": "2000-05-29T03:27:00Z"}
    assert [m["lord"] for m in tl] == ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu",
                                      "Jupiter", "Saturn", "Mercury"]


def test_half_elapsed_nakshatra_balance():
    lord, elapsed = dasha.birth_balance(6.0 + 2 / 3)  # half of Ashwini
    assert lord == "Ketu" and elapsed == pytest.approx(0.5)
    out = dasha.compute(6.0 + 2 / 3, BIRTH, BIRTH, approximate=False)
    assert out["balance_at_birth_years"] == pytest.approx(3.5)
    # virtual start = birth - 3.5 y = 1278.375 d: 1997-01-01 is 1095 d back, then 183.375 d
    # more -> 1996-07-01T15:00Z
    assert out["timeline"][0]["start"] == "1996-07-01"


@pytest.mark.parametrize("moon,lord", [(13.34, "Venus"), (201.0, "Jupiter"), (359.9, "Mercury"),
                                       (240.0, "Ketu"), (93.4, "Saturn")])
def test_starting_lord_by_nakshatra(moon, lord):
    assert dasha.birth_balance(moon)[0] == lord


def test_timeline_spans_120_years_and_antars_tile_each_md():
    tl = dasha.timeline(123.456, BIRTH)
    start = datetime.fromisoformat(tl[0]["start"])
    end = datetime.fromisoformat(tl[-1]["end"])
    assert abs((end - start).days - 120 * 365.25) <= 1
    for md in tl:
        assert md["antar"][0]["start"] == md["start"] and md["antar"][-1]["end"] == md["end"]
        assert md["antar"][0]["lord"] == md["lord"]


def test_current_pointers_move_with_now():
    a = dasha.current(0.0, BIRTH, BIRTH + timedelta(days=10))
    b = dasha.current(0.0, BIRTH, BIRTH + timedelta(days=3000))
    assert a["maha_dasha"]["current"] == "Ketu" and a["antar_dasha"]["current"] == "Ketu"
    assert b["maha_dasha"]["current"] == "Venus" and b["maha_dasha"]["duration_years"] == 20


def test_current_beyond_one_cycle_wraps():
    far = dasha.current(0.0, BIRTH, BIRTH + timedelta(days=365.25 * 125))
    assert far["maha_dasha"]["current"] == "Ketu"  # 120 y cycle restarts with Ketu


def test_year_length_is_configurable():
    a = dasha.timeline(0.0, BIRTH, year_days=360.0)
    assert a[0]["end"] == (BIRTH + timedelta(days=7 * 360)).date().isoformat()
