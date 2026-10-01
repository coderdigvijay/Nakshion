"""Independent QA attacks on the astrology engine. xfail(strict) tests document confirmed defects."""
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, time, timezone

import pytest
import swisseph as swe

from app.astrology import AstroInputError, compute_natal_chart as C

NOW = datetime(2026, 10, 1, tzinfo=timezone.utc)


def chart(d, tm=time(10, 30), lat=28.6, lon=77.2, **kw):
    return C(date_of_birth=d, time_of_birth=tm, has_exact_time=tm is not None,
             latitude=lat, longitude=lon, now_utc=kw.pop("now_utc", NOW), **kw)


def test_einstein_matches_astro_com():
    c = chart(date(1879, 3, 14), time(11, 30), 48.4, 10.0, utc_offset_override=40)
    assert (c["sun_sign"]["sign"], round(c["sun_sign"]["degree"])) == ("Pisces", 24)
    assert abs(c["moon_sign"]["degree"] - 14.53) < 0.05 and c["moon_sign"]["sign"] == "Sagittarius"
    assert c["rising_sign"]["sign"] == "Cancer"


def test_threads_with_hostile_global_swe_state_match_serial():
    inputs = [dict(d=date(1950 + i, 1 + i % 12, 1 + i % 28), tm=time(i % 24, i % 60),
                   lat=-50 + i * 1.5, lon=-170 + i * 5.5) for i in range(24)]
    serial = [json.dumps(chart(**i), sort_keys=True) for i in inputs]
    stop = threading.Event()

    def meddle():
        k = 0
        while not stop.is_set():
            swe.set_sid_mode(swe.SIDM_KRISHNAMURTI + k % 3)
            k += 1

    t = threading.Thread(target=meddle)
    t.start()
    try:
        with ThreadPoolExecutor(12) as ex:
            par = list(ex.map(lambda i: json.dumps(chart(**i), sort_keys=True), inputs * 2))
    finally:
        stop.set()
        t.join()
    assert par == serial * 2


def test_unknown_time_sun_ingress_day_is_flagged_approximate():
    # Sun enters Aries 2000-03-20 07:35 UT (13:05 IST): the Delhi birth day spans two signs.
    c = chart(date(2000, 3, 20), None)
    assert c["sun_sign"]["approximate"] is True


def test_north_node_retrograde_flag_matches_speed():
    for y in range(1950, 2030):
        n = next(p for p in chart(date(y, 3, 3), time(12), 0, 0)["planets"] if p["name"] == "North Node")
        assert (n["speed"] < 0) == n["retrograde"]


def test_bad_types_raise_astro_input_error():
    for kw in ({"now_utc": datetime(2026, 10, 1)}, {"lat": "28.6"}, {"d": "1990-05-01"}):
        args = dict(d=date(1990, 5, 1)); args.update(kw)
        try:
            chart(**args)
        except AstroInputError:
            continue
        except Exception:
            pytest.fail(f"raw exception for {kw}")
