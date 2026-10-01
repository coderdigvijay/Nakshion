"""Golden: ASC, MC and Placidus cusps vs an independent textbook implementation.

The reference here is written from Meeus, "Astronomical Algorithms" (2nd ed.): GMST eq. 12.4,
mean obliquity eq. 22.2, ASC/MC from RAMC, and Placidus by semi-arc iteration. It shares no
code with Swiss Ephemeris. It ignores nutation (equation of the equinoxes <= 0.005 deg, true vs
mean obliquity <= 0.003 deg), so agreement to well inside the 0.05 deg tolerance is expected.
"""

import math
from datetime import date, time

import pytest

from app.astrology import compute_natal_chart

D = math.radians
R = math.degrees


def gmst_deg(jd_ut: float) -> float:
    t = (jd_ut - 2451545.0) / 36525.0
    return (280.46061837 + 360.98564736629 * (jd_ut - 2451545.0)
            + 0.000387933 * t * t - t ** 3 / 38710000.0) % 360.0


def mean_obliquity(jd_ut: float) -> float:
    t = (jd_ut - 2451545.0) / 36525.0
    return 23.0 + 26.0 / 60 + 21.448 / 3600 - (46.8150 * t + 0.00059 * t * t - 0.001813 * t ** 3) / 3600


def ref_angles(jd_ut: float, lat: float, lon: float) -> tuple[float, float, float, float]:
    ramc = (gmst_deg(jd_ut) + lon) % 360.0
    eps = mean_obliquity(jd_ut)
    mc = R(math.atan2(math.sin(D(ramc)), math.cos(D(ramc)) * math.cos(D(eps)))) % 360.0
    asc = R(math.atan2(math.cos(D(ramc)),
                       -(math.sin(D(ramc)) * math.cos(D(eps)) + math.tan(D(lat)) * math.sin(D(eps))))) % 360.0
    return asc, mc, ramc, eps


def ref_placidus(jd_ut: float, lat: float, lon: float) -> list[float]:
    asc, mc, ramc, eps = ref_angles(jd_ut, lat, lon)

    def cusp(offset_sign: int, frac: float) -> float:
        # Cusps 11/12 (east, offset +) and 9/8 (west, offset -): RA - RAMC = +-frac * DSA.
        lam = (mc + offset_sign * frac * 90.0) % 360.0
        for _ in range(100):
            dec = math.asin(math.sin(D(eps)) * math.sin(D(lam)))
            ad = R(math.asin(max(-1.0, min(1.0, math.tan(D(lat)) * math.tan(dec)))))
            ra = (ramc + offset_sign * frac * (90.0 + ad)) % 360.0
            new = R(math.atan2(math.sin(D(ra)), math.cos(D(ra)) * math.cos(D(eps)))) % 360.0
            if abs(new - lam) < 1e-9:
                break
            lam = new
        return lam

    c11, c12 = cusp(+1, 1 / 3), cusp(+1, 2 / 3)
    c9, c8 = cusp(-1, 1 / 3), cusp(-1, 2 / 3)
    cusps = [asc, (c8 + 180) % 360, (c9 + 180) % 360, (mc + 180) % 360, (c11 + 180) % 360,
             (c12 + 180) % 360, (asc + 180) % 360, c8, c9, mc, c11, c12]
    return cusps


def _d(a, b):
    return abs((a - b + 180.0) % 360.0 - 180.0)


CASES = {
    "mumbai_1994": dict(date_of_birth=date(1994, 7, 21), time_of_birth=time(14, 5), latitude=19.076,
                        longitude=72.8777, timezone="Asia/Kolkata"),
    "sydney_1985": dict(date_of_birth=date(1985, 12, 25), time_of_birth=time(18, 0), latitude=-33.8688,
                        longitude=151.2093, timezone="Australia/Sydney"),
    "newyork_fold_2021": dict(date_of_birth=date(2021, 11, 7), time_of_birth=time(1, 30), latitude=40.7128,
                              longitude=-74.006, timezone="America/New_York"),
    "kiritimati_2000": dict(date_of_birth=date(2000, 1, 1), time_of_birth=time(0, 30), latitude=1.87,
                            longitude=-157.4, timezone="Pacific/Kiritimati"),
    "london_1962": dict(date_of_birth=date(1962, 8, 10), time_of_birth=time(23, 15), latitude=51.5074,
                        longitude=-0.1278, timezone="Europe/London"),
    "tromso_polar_1990": dict(date_of_birth=date(1990, 6, 21), time_of_birth=time(12, 0), latitude=69.6492,
                              longitude=18.9553, timezone="Europe/Oslo"),
}


@pytest.mark.parametrize("cid", CASES)
def test_asc_mc_match_reference(cid):
    chart = compute_natal_chart(has_exact_time=True, **CASES[cid])
    jd = chart["metadata"]["jd_ut"]
    asc, mc, _, _ = ref_angles(jd, CASES[cid]["latitude"], CASES[cid]["longitude"])
    assert _d(chart["rising_sign"]["longitude"], asc) <= 0.05
    assert _d(chart["mc"]["longitude"], mc) <= 0.05


@pytest.mark.parametrize("cid", [c for c in CASES if "polar" not in c])
def test_placidus_cusps_match_reference(cid):
    chart = compute_natal_chart(has_exact_time=True, **CASES[cid])
    assert chart["metadata"]["house_system"] == "placidus"
    ref = ref_placidus(chart["metadata"]["jd_ut"], CASES[cid]["latitude"], CASES[cid]["longitude"])
    for h, expected in zip(chart["houses"], ref):
        assert _d(h["longitude"], expected) <= 0.1, f"cusp {h['number']}: {h['longitude']} vs {expected}"


def test_einstein_published_chart():
    """Astro-Databank (astro.com), Einstein, Albert, Rodden rating AA: 1879-03-14 11:30 LMT Ulm
    (48N24, 9E59). Published: Sun 23Pi30, Moon 14Sa31, ASC 11Cn38. LMT for 9E59 = +0:39:56,
    passed as an override because IANA Europe/Berlin gives Berlin LMT (+0:53:28) for 1879."""
    chart = compute_natal_chart(date_of_birth=date(1879, 3, 14), time_of_birth=time(11, 30),
                                has_exact_time=True, latitude=48 + 24 / 60, longitude=9 + 59 / 60,
                                utc_offset_override=39 + 56 / 60)
    sun = next(p for p in chart["planets"] if p["name"] == "Sun")
    moon = next(p for p in chart["planets"] if p["name"] == "Moon")
    assert _d(sun["longitude"], 330 + 23 + 30 / 60) <= 0.05
    assert _d(moon["longitude"], 240 + 14 + 31 / 60) <= 0.05
    assert _d(chart["rising_sign"]["longitude"], 90 + 11 + 38 / 60) <= 0.05
    assert chart["metadata"]["tz_source"] == "user_override"
    assert chart["metadata"]["tz_confidence"] == "low"  # pre-1900


def test_polar_birth_falls_back_to_porphyry_and_records_it():
    chart = compute_natal_chart(has_exact_time=True, **CASES["tromso_polar_1990"])
    assert chart["metadata"]["house_system"] == "porphyry_fallback"
    assert len(chart["houses"]) == 12
    # Porphyry: cusp 1 = ASC, cusp 10 = MC, intermediate cusps trisect each quadrant.
    assert chart["houses"][0]["longitude"] == chart["rising_sign"]["longitude"]
    assert chart["houses"][9]["longitude"] == chart["mc"]["longitude"]


@pytest.mark.parametrize("lat", [66.5, 75.0, 78.22, 89.99, 90.0, -90.0, -70.0])
def test_extreme_latitudes_never_raise(lat):
    chart = compute_natal_chart(date_of_birth=date(1990, 12, 21), time_of_birth=time(12, 0),
                                has_exact_time=True, latitude=lat, longitude=15.0, timezone="UTC")
    assert chart["metadata"]["house_system"] == "porphyry_fallback"
    assert all(0 <= h["longitude"] < 360 for h in chart["houses"])


def test_just_below_polar_threshold_keeps_placidus():
    chart = compute_natal_chart(date_of_birth=date(1990, 6, 21), time_of_birth=time(12, 0),
                                has_exact_time=True, latitude=65.9, longitude=18.96, timezone="Europe/Stockholm")
    assert chart["metadata"]["house_system"] == "placidus"
