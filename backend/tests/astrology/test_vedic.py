"""Vedic derived math: nakshatra/pada, dignity, combustion, vargas, functional nature, drishti.
Expected values are hand-derived from the spec tables (section 2, 5) or classical rules, never
from the code under test."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.astrology.vedic import (
    d9, d10, dignity, functional_nature, graha_drishti, is_combust, nakshatra_of,
)


@pytest.mark.parametrize("lon,idx,pada", [
    (0.0, 0, 1), (3.3333, 0, 1), (3.3334, 0, 2), (13.3333, 0, 4), (13.3334, 1, 1),
    (120.0, 9, 1),  # Magha starts at 0 Leo
    (240.0, 18, 1),  # Mula starts at 0 Sagittarius
    (359.99, 26, 4),
])
def test_nakshatra_boundaries(lon, idx, pada):
    assert nakshatra_of(lon) == (idx, pada)


@given(st.floats(min_value=0, max_value=359.999999, allow_nan=False))
@settings(max_examples=300, deadline=None)
def test_d9_matches_classical_rule(lon):
    """Movable signs start from themselves, fixed from the 9th, dual from the 5th."""
    sign, deg = int(lon // 30), lon % 30
    part = min(int(deg // (10 / 3)), 8)
    start = {0: sign, 1: sign + 8, 2: sign + 4}[sign % 3]
    if abs(deg - round(deg / (10 / 3)) * (10 / 3)) < 1e-6:
        return  # exact boundary: floating representation decides
    assert d9(lon)[0] == (start + part) % 12


@pytest.mark.parametrize("lon,expected", [
    (0.0, 0), (29.9, 9),          # Aries (odd): from Aries
    (30.0, 9), (32.9, 9), (33.0, 10), (59.9, 6),  # Taurus (even): from 9th = Capricorn
    (95.0, 0),                    # Cancer (even sign) starts from its 9th = Pisces; part 1 -> Aries
])
def test_d10(lon, expected):
    assert d10(lon)[0] == expected


@pytest.mark.parametrize("planet,lon,expected", [
    ("Sun", 10.0, "exalted"), ("Sun", 190.0, "debilitated"), ("Sun", 125.0, "mooltrikona"),
    ("Sun", 145.0, "own"), ("Moon", 35.0, "exalted"),  # exalted beats mooltrikona (Taurus 3-30)
    ("Moon", 100.0, "own"), ("Saturn", 310.0, "mooltrikona"), ("Saturn", 325.0, "own"),
    ("Jupiter", 70.0, "enemy"),    # Gemini, lord Mercury: Jupiter's enemy
    ("Mars", 130.0, "friendly"),   # Leo, lord Sun
    ("Mercury", 0.0, "neutral"),   # Aries, lord Mars
    ("Mercury", 350.0, "debilitated"),
    ("Rahu", 40.0, "exalted"), ("Ketu", 220.0, "exalted"), ("Rahu", 280.0, "friendly"),
    ("Uranus", 10.0, "neutral"),
])
def test_dignity(planet, lon, expected):
    assert dignity(planet, lon) == expected


@pytest.mark.parametrize("planet,lon,sun,retro,expected", [
    ("Mercury", 113.0, 100.0, False, True), ("Mercury", 113.0, 100.0, True, False),
    ("Venus", 109.0, 100.0, False, True), ("Venus", 109.0, 100.0, True, False),
    ("Mars", 357.0, 10.0, False, True),  # wraps 0 deg
    ("Rahu", 100.0, 100.0, True, False), ("Uranus", 100.0, 100.0, False, False),
])
def test_combustion(planet, lon, sun, retro, expected):
    assert is_combust(planet, lon, sun, retro) is expected


# Classical yogakarakas: Taurus/Libra -> Saturn, Cancer/Leo -> Mars, Capricorn/Aquarius -> Venus.
@pytest.mark.parametrize("lagna,karaka", [(1, "Saturn"), (6, "Saturn"), (3, "Mars"), (4, "Mars"),
                                          (9, "Venus"), (10, "Venus"), (0, None), (2, None)])
def test_yogakaraka(lagna, karaka):
    assert functional_nature(lagna, True)[2] == karaka


def test_functional_nature_aries_hand_derived():
    """Aries lagna (spec 5.4 rules): Mars 1+8 -> +2 (8th waived for lagna lord); Sun 5 -> +2;
    Jupiter 9+12 -> +2; Venus 2+7 -> -1; Mercury 3+6 -> -3; Moon 4 (waxing) -> -1;
    Saturn 10+11 -> 0 (neither)."""
    ben, mal, _ = functional_nature(0, True)
    assert set(ben) == {"Mars", "Sun", "Jupiter"}
    assert set(mal) == {"Venus", "Mercury", "Moon"}


def test_functional_nature_waning_moon_in_kendra_is_benefic():
    ben, _, _ = functional_nature(0, False)  # Moon owns the 4th, waning -> natural malefic -> +1
    assert "Moon" in ben


def test_graha_drishti_special_aspects():
    signs = {"Sun": 0, "Moon": 0, "Mercury": 0, "Venus": 0, "Mars": 0, "Jupiter": 0,
             "Saturn": 0, "Rahu": 3, "Ketu": 9}
    out = {(a["from"], a["to_house"]) for a in graha_drishti(signs, 0)}
    assert {("Mars", 4), ("Mars", 7), ("Mars", 8)} <= out
    assert {("Jupiter", 5), ("Jupiter", 9), ("Saturn", 3), ("Saturn", 10)} <= out
    assert ("Sun", 4) not in out and not any(f in ("Rahu", "Ketu") for f, _ in out)
    mars4 = next(a for a in graha_drishti(signs, 0) if a["from"] == "Mars" and a["to_house"] == 4)
    assert mars4["to_planets"] == ["Rahu"]
