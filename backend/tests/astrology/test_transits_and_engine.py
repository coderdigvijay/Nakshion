"""Transits, event finder, Sade Sati, sign transit_data shape, and the Moshier guard."""

import json
import math
from datetime import date, datetime, time, timezone
from pathlib import Path

import pytest

from app.astrology import (
    EphemerisUnavailableError, compute_natal_chart, compute_transits, ephemeris_self_check,
    find_events, sade_sati, sign_transit_data,
)
from app.astrology import ephemeris

HORIZONS = json.loads((Path(__file__).parent / "golden" / "fixtures" / "horizons_positions.json").read_text())
NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)


def test_self_check_reports_swieph():
    info = ephemeris_self_check()
    assert info["ephemeris"] == "swieph" and info["retflag"] & 2  # FLG_SWIEPH


def test_moshier_fallback_is_detected_not_silent():
    # Before 1800-01-01 05:45 UT the shipped files do not apply; pyswisseph silently switches
    # to Moshier (retflag 260). The engine must raise, never return those numbers.
    with pytest.raises(EphemerisUnavailableError):
        ephemeris.calc(2378496.0, "Sun")


def test_find_events_bisects_to_a_minute():
    roots = find_events(lambda t: math.sin(t), 0.5, 7.0, 0.7)
    assert [round(r, 2) for r in roots] == [round(math.pi, 2), round(2 * math.pi, 2)]
    assert abs(roots[0] - math.pi) < 1 / 1440


def test_find_events_ignores_wrap_jumps():
    # Sawtooth in (-180, 180]: jumps +180 -> -180 at t=1.8 (a wrap, not a root); no true root
    # inside (0.1, 3.5).
    assert find_events(lambda t: ((t * 100 + 180) % 360) - 180, 0.1, 3.5, 0.5) == []


@pytest.mark.parametrize("moon_rashi,phase", [(0, "rising"), (11, "peak"), (10, "setting"), (5, "none")])
def test_sade_sati_phases_2026(moon_rashi, phase):
    """Horizons: Saturn tropical 2026-10-01 00:00 UT ~ 11.6 Aries; Lahiri ayanamsa ~24.2 ->
    sidereal ~347 = Meena (Pisces, index 11)."""
    sat = HORIZONS["cases"]["today_2026"]["longitudes"]["Saturn"]
    assert int(((sat - 24.2) % 360) // 30) == 11
    assert sade_sati(moon_rashi, NOW)["phase"] == phase


def test_sign_transit_data_shape_and_positions():
    t = sign_transit_data("Leo", date(2026, 10, 1))
    assert t["computed_for"] == "2026-10-01T00:00:00Z" and t["zodiac"] == "tropical"
    assert set(t) >= {"moon", "positions", "aspects_today", "ingresses_today", "solar_house_focus"}
    assert set(t["moon"]) == {"sign", "phase", "illumination", "void_of_course"}
    ref = HORIZONS["cases"]["today_2026"]["longitudes"]
    signs = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio",
             "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
    for p in t["positions"]:
        lon = signs.index(p["sign"]) * 30 + p["degree"]
        assert abs((lon - ref[p["planet"]] + 180) % 360 - 180) <= 0.01
    moon = next(p for p in t["positions"] if p["planet"] == "Moon")
    assert t["solar_house_focus"]["moon_house"] == (signs.index(moon["sign"]) - 4) % 12 + 1
    v = sign_transit_data("Simha", date(2026, 10, 1), system="vedic")
    assert v["zodiac"] == "sidereal" and v["positions"][0]["sign"] in (
        "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula", "Vrishchika", "Dhanu",
        "Makara", "Kumbha", "Meena")


def test_ingress_found_when_moon_changes_sign():
    # 2000-01-05 UT: Horizons Moon 262.2 -> 274.0 across the (IST) day; it enters Capricorn.
    t = sign_transit_data("Aries", date(2000, 1, 5))
    moon = [i for i in t["ingresses_today"] if i["planet"] == "Moon"]
    assert moon and moon[0]["to"] == "Capricorn" and moon[0]["at"].startswith("2000-01-05")


def test_personal_transits():
    chart = compute_natal_chart(date_of_birth=date(1994, 7, 21), time_of_birth=time(14, 5),
                                has_exact_time=True, latitude=19.076, longitude=72.8777,
                                timezone="Asia/Kolkata", now_utc=NOW)
    out = compute_transits(chart, NOW)
    assert out["western"] and all(set(x) >= {"transiting", "natal", "type", "orb", "applying",
                                             "exact_at", "window_start", "window_end"}
                                  for x in out["western"])
    for x in out["western"]:
        if x["window_start"] and x["window_end"]:
            assert x["window_start"] <= "2026-10-01T00:00:00Z" <= x["window_end"]
    v = out["vedic"]
    assert [g["planet"] for g in v["gochara"]] == ["Jupiter", "Saturn", "Rahu", "Ketu"]
    assert 1 <= v["moon_transit_house"] <= 12
