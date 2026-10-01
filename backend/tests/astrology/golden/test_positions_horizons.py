"""Golden: tropical planet longitudes vs NASA/JPL Horizons DE441 (independent of Swiss Ephemeris).

Fixture: fixtures/horizons_positions.json, generated offline by generate_horizons_fixtures.py
(source, settings and retrieval date are inside the file). Tolerance 0.01 deg for every body,
including the Moon (spec allows 0.02 for the Moon; observed max error is 1.2 arcsec).
"""

import json
from pathlib import Path

import pytest
import swisseph as swe

from app.astrology import ephemeris

FIXTURE = json.loads((Path(__file__).parent / "fixtures" / "horizons_positions.json").read_text())
TOL_DEG = 0.01
CASES = [(cid, body, case["jd"], case["time_scale"], lon)
         for cid, case in FIXTURE["cases"].items() for body, lon in case["longitudes"].items()]


def _diff(a: float, b: float) -> float:
    return abs((a - b + 180.0) % 360.0 - 180.0)


@pytest.mark.parametrize("cid,body,jd,scale,expected", CASES, ids=[f"{c[0]}-{c[1]}" for c in CASES])
def test_longitude_matches_horizons(cid, body, jd, scale, expected):
    if scale == "UT":
        got = ephemeris.calc(jd, body).longitude
    else:
        # Range-edge cases compare in TT: Horizons and SE extrapolate Delta-T differently in
        # 1800/2399 by minutes, which is a time-scale model difference, not a position error.
        ephemeris._ensure_path()
        xx, flag = swe.calc(jd, ephemeris.BODY_IDS[body], ephemeris.FLAGS)
        assert flag & swe.FLG_SWIEPH, f"Moshier fallback at range edge {cid}"
        got = xx[0]
    assert _diff(got, expected) <= TOL_DEG, f"{cid} {body}: got {got}, Horizons {expected}"


def test_fixture_provenance_present():
    assert "Horizons" in FIXTURE["source"] and FIXTURE["retrieved_at"]
