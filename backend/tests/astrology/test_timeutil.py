"""Time zone fixtures (spec 11 "Timezones"). Expected offsets are hand-built from the IANA tz
source (tzdata 2026d, `asia`, `northamerica`, `australasia` files):

  Asia/Kolkata:  5:21:10 MMT until 1906; 5:30 IST; +0630 1941 Oct - 1942 May 15;
                 IST 1942 May 15 - Sep; +0630 1942 Sep - 1945 Oct 15; IST after.
  Asia/Kathmandu: +0530 until 1986, +0545 after.
  America/New_York: 2021-03-14 02:00 -> 03:00 (gap); 2021-11-07 02:00 -> 01:00 (fold).
  Pacific/Apia: 2011-12-30 skipped entirely (moved west -> east of the date line).
  Pacific/Kiritimati: 1994-12-31 skipped (-10 -> +14).
"""

from datetime import date, datetime, time, timezone

import pytest

from app.astrology import AstroInputError, resolve_timezone
from app.astrology.timeutil import jd_from_utc, resolve_birth_time

KOLKATA = (22.5726, 88.3639)
NEW_YORK = (40.7128, -74.006)


def rt(d, t, lat, lon, tz=None, **kw):
    return resolve_birth_time(date_of_birth=d, time_of_birth=t, latitude=lat, longitude=lon,
                              timezone_name=tz, **kw)


@pytest.mark.parametrize("d,t,offset,conf", [
    (date(1943, 6, 15), time(6, 0), 390, "medium"),     # WWII War Time +06:30
    (date(1942, 7, 1), time(12, 0), 330, "medium"),     # gap in War Time (May 15 - Sep 1942)
    (date(1941, 12, 1), time(12, 0), 390, "medium"),
    (date(1945, 10, 20), time(12, 0), 330, "medium"),
    (date(1950, 1, 1), time(0, 0), 330, "medium"),      # pre-1970 -> medium
    (date(1994, 7, 21), time(14, 5), 330, "high"),
])
def test_india_historical_offsets(d, t, offset, conf):
    r = rt(d, t, *KOLKATA)
    assert r.timezone == "Asia/Kolkata"
    assert r.utc_offset_minutes == offset
    assert r.tz_confidence == conf


def test_india_pre_1906_madras_time_is_low_confidence():
    r = rt(date(1890, 6, 1), time(6, 0), *KOLKATA)
    assert r.utc_offset_minutes == pytest.approx(5 * 60 + 21 + 10 / 60)
    assert r.tz_confidence == "low"


def test_india_1943_utc_instant():
    r = rt(date(1943, 6, 15), time(6, 0), *KOLKATA)
    assert r.utc == datetime(1943, 6, 14, 23, 30, tzinfo=timezone.utc)


def test_us_dst_gap_rejected():
    with pytest.raises(AstroInputError) as e:
        rt(date(2021, 3, 14), time(2, 30), *NEW_YORK)
    assert e.value.code == "BIRTH_TIME_NONEXISTENT"


@pytest.mark.parametrize("fold,offset,utc_hour", [(0, -240, 5), (1, -300, 6)])
def test_us_dst_fold_flagged_and_fold_respected(fold, offset, utc_hour):
    r = rt(date(2021, 11, 7), time(1, 30), *NEW_YORK, dst_fold=fold)
    assert r.ambiguous_time is True
    assert r.utc_offset_minutes == offset
    assert r.utc == datetime(2021, 11, 7, utc_hour, 30, tzinfo=timezone.utc)


def test_unambiguous_time_not_flagged():
    assert rt(date(2021, 11, 7), time(3, 30), *NEW_YORK).ambiguous_time is False


@pytest.mark.parametrize("d,offset", [(date(1985, 1, 1), 330), (date(2000, 2, 29), 345)])
def test_nepal_offsets(d, offset):
    r = rt(d, time(0, 0), 27.7172, 85.324)
    assert r.timezone == "Asia/Kathmandu" and r.utc_offset_minutes == offset


@pytest.mark.parametrize("d,lat,lon", [
    (date(2011, 12, 30), -13.83, -171.76),   # Samoa skipped day
    (date(1994, 12, 31), 1.87, -157.4),      # Kiritimati skipped day
])
def test_date_line_skipped_days_rejected(d, lat, lon):
    with pytest.raises(AstroInputError) as e:
        rt(d, time(12, 0), lat, lon)
    assert e.value.code == "BIRTH_TIME_NONEXISTENT"


def test_kiritimati_plus_14_crosses_utc_date():
    r = rt(date(2000, 1, 1), time(0, 30), 1.87, -157.4)
    assert r.utc_offset_minutes == 840
    assert r.utc == datetime(1999, 12, 31, 10, 30, tzinfo=timezone.utc)


def test_override_replaces_zone_lookup():
    r = rt(date(1879, 3, 14), time(11, 30), 48.4, 9.9833, utc_offset_override=39 + 56 / 60)
    assert r.tz_source == "user_override"
    assert r.utc == datetime(1879, 3, 14, 10, 50, 4, tzinfo=timezone.utc)


def test_pre_1900_lmt_low_confidence():
    r = rt(date(1879, 3, 14), time(11, 30), 52.52, 13.405)
    assert r.timezone == "Europe/Berlin" and r.tz_confidence == "low"
    assert r.utc_offset_minutes == pytest.approx(53 + 28 / 60)


@pytest.mark.parametrize("lat,lon,zone", [
    (19.076, 72.8777, "Asia/Kolkata"), (27.7172, 85.324, "Asia/Kathmandu"),
    (-13.83, -171.76, "Pacific/Apia"), (78.22, 15.65, "Arctic/Longyearbyen"),
    (-17.7, 178.0, "Pacific/Fiji"), (0.0, -150.0, "Etc/GMT+10"),
])
def test_resolve_timezone(lat, lon, zone):
    assert resolve_timezone(lat, lon) == zone


@pytest.mark.parametrize("lat,lon", [(91, 0), (-90.1, 0), (0, 180.5), (float("nan"), 0)])
def test_invalid_location(lat, lon):
    with pytest.raises(AstroInputError) as e:
        rt(date(2000, 1, 1), time(0), lat, lon)
    assert e.value.code == "INVALID_LOCATION"


def test_invalid_timezone():
    with pytest.raises(AstroInputError) as e:
        rt(date(2000, 1, 1), time(0), 0, 0, tz="Mars/Olympus")
    assert e.value.code == "INVALID_TIMEZONE"


@pytest.mark.parametrize("d", [date(1799, 12, 31), date(1800, 1, 1), date(2400, 1, 1)])
def test_date_out_of_range(d):
    with pytest.raises(AstroInputError) as e:
        rt(d, time(0), 0, 179.9)
    assert e.value.code == "DATE_OUT_OF_RANGE"


@pytest.mark.parametrize("d,t,lat,lon", [
    (date(1800, 1, 2), time(0, 0), 0.0, 179.9),       # +12h east: earliest UT the files cover
    (date(2399, 12, 31), time(23, 59), 0.0, -179.9),  # -12h west: latest
])
def test_range_edges_compute_on_swieph(d, t, lat, lon):
    from app.astrology import compute_natal_chart

    chart = compute_natal_chart(date_of_birth=d, time_of_birth=t, has_exact_time=True,
                                latitude=lat, longitude=lon)
    assert chart["metadata"]["ephemeris"] == "swieph"


def test_leap_seconds_do_not_enter_jd():
    """UT for calc_ut is a continuous UT1-like scale; a leap second (1972-06-30 23:59:60 UTC)
    is not representable and must not shift the Julian day: 1 s apart -> exactly 1/86400 d."""
    a = jd_from_utc(datetime(1972, 6, 30, 23, 59, 59, tzinfo=timezone.utc))
    b = jd_from_utc(datetime(1972, 7, 1, 0, 0, 0, tzinfo=timezone.utc))
    assert b - a == pytest.approx(1 / 86400, abs=1e-9)
