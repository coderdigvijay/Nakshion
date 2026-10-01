"""Golden: Panchang vs Drik Panchang (https://www.drikpanchang.com/panchang/day-panchang.html),
retrieved 2026-10-01 via the public day-panchang page (geoname ids in the URL). Drik times are
rounded down to the minute; tolerance here is +-2 min for sunrise/sunset/Rahu Kaal and
+-2 min for element end times (names exact), per spec section 11.

Cases: Delhi 2026-10-01 (geoname 1261481), Mumbai 2026-03-03 (1275339), New York 2026-11-08
(5128581), London 2025-12-25 (2643743), Hyderabad 2025-08-15 (1269843). Coordinates are the ones
Drik prints (Mumbai 19.0728N 72.8825E, Hyderabad 17.3839N 78.4561E).
Tithi crossing midnight: New York Amavasya ends 02:01 Nov 9; Hyderabad Saptami 23:49;
Mumbai second karana Balava ends 04:54 Mar 4.
"""

from datetime import date, datetime

import pytest

from app.astrology.panchang import karana_name, panchang, tithi_name

CASES = {
    "delhi": (date(2026, 10, 1), 28.6139, 77.209, dict(
        sunrise="06:14", sunset="18:07", vara="Thursday", tithi=("Panchami", "Krishna", "12:35"),
        nak=("Rohini", "04:27"), yoga=("Siddhi", "21:18"), karana=("Taitila", "12:35"),
        rahu=("13:40", "15:09"))),
    "mumbai": (date(2026, 3, 3), 19.0728, 72.8825, dict(
        sunrise="06:56", sunset="18:45", vara="Tuesday", tithi=("Purnima", "Shukla", "17:07"),
        nak=("Magha", "07:31"), yoga=("Sukarma", "10:25"), karana=("Bava", "17:07"),
        rahu=("15:48", "17:16"))),
    "newyork": (date(2026, 11, 8), 40.7143, -74.006, dict(
        sunrise="06:35", sunset="16:44", vara="Sunday", tithi=("Amavasya", "Krishna", "02:01"),
        nak=("Swati", "20:54"), yoga=("Ayushman", "16:33"), karana=("Chatushpada", "13:26"),
        rahu=("15:28", "16:44"))),
    "london": (date(2025, 12, 25), 51.5085, -0.1257, dict(
        sunrise="08:05", sunset="15:56", vara="Thursday", tithi=("Panchami", "Shukla", "08:12"),
        nak=("Shatabhisha", "03:30"), yoga=("Vajra", "09:44"), karana=("Balava", "08:12"),
        rahu=("13:00", "13:58"))),
    "hyderabad": (date(2025, 8, 15), 17.3839, 78.4561, dict(
        sunrise="05:59", sunset="18:42", vara="Friday", tithi=("Saptami", "Krishna", "23:49"),
        nak=("Ashwini", "07:36"), yoga=("Ganda", "10:17"), karana=("Vishti", "12:58"),
        rahu=("10:45", "12:21"))),
}


def _min(hm: str) -> int:
    h, m = hm.split(":")
    return int(h) * 60 + int(m)


def _close(got: str, want: str, tol: int = 2) -> bool:
    d = abs(_min(got) - _min(want))
    return min(d, 1440 - d) <= tol


@pytest.mark.parametrize("cid", CASES)
def test_panchang_matches_drik(cid):
    day, lat, lon, exp = CASES[cid]
    p = panchang(day, lat, lon)
    assert p["vara"] == exp["vara"]
    assert _close(p["sunrise_local"], exp["sunrise"]) and _close(p["sunset_local"], exp["sunset"])
    t = exp["tithi"]
    assert (p["tithi"]["name"], p["tithi"]["paksha"]) == t[:2] and _close(p["tithi"]["end_local"], t[2])
    assert p["nakshatra"]["name"] == exp["nak"][0] and _close(p["nakshatra"]["end_local"], exp["nak"][1])
    assert p["yoga"]["name"] == exp["yoga"][0] and _close(p["yoga"]["end_local"], exp["yoga"][1])
    assert p["karana"]["name"] == exp["karana"][0] and _close(p["karana"]["end_local"], exp["karana"][1])
    assert _close(p["rahu_kaal"]["start_local"], exp["rahu"][0])
    assert _close(p["rahu_kaal"]["end_local"], exp["rahu"][1])


def test_tithi_ending_after_midnight_belongs_to_this_hindu_day():
    p = panchang(*CASES["newyork"][:3])
    end = datetime.fromisoformat(p["tithi"]["end"].replace("Z", "+00:00"))
    assert end.date().isoformat() == "2026-11-09" and p["tithi"]["name"] == "Amavasya"


def test_polar_day_and_night_have_no_sunrise_and_do_not_crash():
    for d, lat in [(date(2026, 6, 21), 78.22), (date(2026, 12, 21), 78.22), (date(2026, 6, 21), 69.65)]:
        p = panchang(d, lat, 15.65)
        assert p["sunrise_available"] is False and p["sunrise"] is None and p["rahu_kaal"] is None
        assert p["day_boundary"].startswith("local_06:00") and p["tithi"]["name"]


def test_date_line_zone_kiritimati():
    p = panchang(date(2000, 1, 1), 1.87, -157.4)
    assert p["timezone"] == "Pacific/Kiritimati" and p["vara"] == "Saturday"
    assert p["sunrise"].startswith("1999-12-31")  # +14: local morning is the previous UTC day


def test_names_tables():
    assert [tithi_name(n) for n in (1, 11, 15, 16, 30)] == ["Pratipada", "Ekadashi", "Purnima", "Pratipada", "Amavasya"]
    assert [karana_name(k) for k in (0, 1, 7, 8, 56, 57, 58, 59)] == [
        "Kimstughna", "Bava", "Vishti", "Bava", "Vishti", "Shakuni", "Chatushpada", "Naga"]
