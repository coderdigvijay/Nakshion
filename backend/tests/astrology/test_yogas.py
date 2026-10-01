"""Yoga / dosha rules (spec 5.6) on synthetic placements. Expected outcomes are hand-derived."""

import pytest

from app.astrology.vedic import dignity, is_combust
from app.astrology.yogas import YogaContext, compute_yogas, kaal_sarp, mangal_dosha

ALL = ("Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu")


def ctx(lagna: int, lons: dict[str, float]) -> YogaContext:
    lons = dict(lons)
    lons.setdefault("Ketu", (lons["Rahu"] + 180) % 360)
    signs = {k: int(v // 30) % 12 for k, v in lons.items()}
    planets = {k: {"dignity": dignity(k, v), "combust": is_combust(k, v, lons["Sun"], False)}
               for k, v in lons.items()}
    return YogaContext(planets, signs, lons, lagna)


BASE = {"Sun": 15, "Moon": 105, "Mars": 200, "Mercury": 45, "Jupiter": 290, "Venus": 75,
        "Saturn": 160, "Rahu": 140}


def by_name(c):
    return {y["name"]: y for y in compute_yogas(c)}


def test_gajakesari_jupiter_kendra_from_moon():
    # Moon Cancer (3), Jupiter Capricorn (9): 7th from the Moon -> present.
    assert by_name(ctx(0, BASE))["Gajakesari Yoga"]["present"] is True
    assert by_name(ctx(0, {**BASE, "Jupiter": 130}))["Gajakesari Yoga"]["present"] is False


def test_budhaditya_weak_when_mercury_close():
    y = by_name(ctx(0, {**BASE, "Mercury": 17}))["Budhaditya Yoga"]
    assert y["present"] and y["strength"] == "weak"


def test_ruchaka_mars_own_sign_in_kendra():
    # Lagna Aries, Mars in Aries (own) in the 1st house.
    y = by_name(ctx(0, {**BASE, "Mars": 5}))["Ruchaka Yoga"]
    assert y["present"] and y["strength"] == "strong"
    assert not by_name(ctx(1, {**BASE, "Mars": 5}))["Ruchaka Yoga"]["present"]  # 12th from Taurus


def test_kemadruma_formed_and_cancelled():
    # Moon alone in Cancer; every other classical planet (not Sun) 3rd/5th/6th/8th/9th/11th away.
    lons = {"Sun": 165, "Moon": 105, "Mars": 165, "Mercury": 225, "Jupiter": 345, "Venus": 45,
            "Saturn": 165, "Rahu": 20}
    assert by_name(ctx(0, lons))["Kemadruma Yoga"]["present"] is True
    lons["Venus"] = 75  # 12th from the Moon -> cancelled
    assert by_name(ctx(0, lons))["Kemadruma Yoga"]["present"] is False


def test_kaal_sarp():
    hemmed = {"Sun": 10, "Moon": 40, "Mars": 70, "Mercury": 100, "Jupiter": 130, "Venus": 150,
              "Saturn": 170, "Rahu": 0.5}
    y = kaal_sarp(ctx(0, hemmed))
    assert y["present"] and y["strength"] == "strong"
    assert kaal_sarp(ctx(0, {**hemmed, "Saturn": 190}))["present"] is False
    assert kaal_sarp(ctx(0, {**hemmed, "Sun": 1.0}))["strength"] == "moderate"  # within 1 deg of Rahu


@pytest.mark.parametrize("mars,lagna,expected", [(5, 0, True), (35, 0, True), (65, 0, False),
                                                 (185, 0, True), (215, 0, True), (335, 0, True)])
def test_mangal_dosha_from_lagna(mars, lagna, expected):
    lons = {**BASE, "Mars": mars, "Moon": 65}  # Moon in Gemini: only the lagna reference varies
    entry, manglik = mangal_dosha(ctx(lagna, lons))
    assert manglik["from_lagna"] is expected
    assert entry["present"] is (manglik["from_lagna"] or manglik["from_moon"])


def test_raja_yoga_conjunction_of_kendra_and_trikona_lords():
    # Lagna Aries: Saturn lords 10 (kendra), Sun lords 5 (trikona); both in Leo.
    y = by_name(ctx(0, {**BASE, "Saturn": 130, "Sun": 125}))["Raja Yoga"]
    assert y["present"] and "Y.RAJA.SATURN.CONJ.SUN" in y["factors"]


def test_viparita_raja_yoga():
    # Lagna Aries: Mercury lords 6 (Virgo); placed in Scorpio = 8th.
    y = by_name(ctx(0, {**BASE, "Mercury": 215}))["Viparita Raja Yoga"]
    assert y["present"] and "Y.VIPARITA.MERCURY.L6.H8" in y["factors"]


def test_every_yoga_has_contract_fields():
    for y in compute_yogas(ctx(0, BASE)):
        assert set(y) == {"name", "present", "strength", "description", "factors"}
        assert y["strength"] in ("weak", "moderate", "strong")
