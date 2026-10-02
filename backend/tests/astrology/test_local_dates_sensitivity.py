"""Calendar dates are in the birth zone (not UTC); near-cusp sensitivity flags.

SYNTHETIC fixture (no real individual): 1987-03-17 01:41 Asia/Kolkata at New Delhi's public city
coordinates. Local clock time 01:41 IST = 20:11 UTC of the previous day, so UTC and IST calendar
dates differ for any boundary that falls between 00:00 and 05:30 IST (the BUG-023 pattern). The
tropical Ascendant is Capricorn 0.14 deg, ~0.6 minute from the Sagittarius/Capricorn cusp (found
by scanning minutes for this place). Expected local dates are derived in the test from the
engine's own UTC instants via zoneinfo, never copied from a real chart.
"""

from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

import pytest

from app.astrology import (
    ENGINE_VERSION, compute_natal_chart, panchang, personal_day, refresh_time_dependent, sade_sati_period,
)

IST = ZoneInfo("Asia/Kolkata")
NOW = datetime(2026, 10, 2, tzinfo=timezone.utc)
KW = dict(latitude=28.6139, longitude=77.209, timezone="Asia/Kolkata")


@pytest.fixture(scope="module")
def chart():
    return compute_natal_chart(date_of_birth=date(1987, 3, 17), time_of_birth=time(1, 41),
                               has_exact_time=True, now_utc=NOW, **KW)


def test_dasha_dates_are_local_calendar_dates(chart):
    d = chart["vedic"]["dasha"]
    assert d["date_timezone"] == "Asia/Kolkata"
    differing = 0
    for md in d["timeline"]:
        for item in (md, *md["antar"]):
            for k in ("start", "end"):
                inst = datetime.fromisoformat(item[k + "_utc"].replace("Z", "+00:00"))
                assert item[k] == inst.astimezone(IST).date().isoformat()
                differing += item[k] != inst.date().isoformat()
    # The fixture is only meaningful if the UTC-date bug would have shown (it did for ~1/4).
    assert differing >= 20
    for key in ("maha_dasha", "antar_dasha"):
        inst = datetime.fromisoformat(d[key]["end_utc"].replace("Z", "+00:00"))
        assert d[key]["end"] == inst.astimezone(IST).date().isoformat()


def test_every_boundary_local_date_matches_its_utc_instant(chart):
    from zoneinfo import ZoneInfo

    ist = IST
    n = 0
    for md in chart["vedic"]["dasha"]["timeline"]:
        for item in [md, *md["antar"]]:
            for k in ("start", "end"):
                inst = datetime.fromisoformat(item[k + "_utc"].replace("Z", "+00:00"))
                assert item[k] == inst.astimezone(ist).date().isoformat()
                n += 1
    assert n == 180


def test_refresh_keeps_local_dates_and_instants(chart):
    out = refresh_time_dependent(chart, NOW)["vedic"]["dasha"]
    inst = datetime.fromisoformat(out["antar_dasha"]["end_utc"].replace("Z", "+00:00"))
    assert out["antar_dasha"]["end"] == inst.astimezone(IST).date().isoformat()


def test_offset_override_birth_uses_fixed_offset_dates():
    c = compute_natal_chart(date_of_birth=date(1987, 3, 17), time_of_birth=time(1, 41), has_exact_time=True,
                            utc_offset_override=330, now_utc=NOW, latitude=28.6139, longitude=77.209)
    md = c["vedic"]["dasha"]["maha_dasha"]
    inst = datetime.fromisoformat(md["start_utc"].replace("Z", "+00:00"))
    assert md["start"] == inst.astimezone(IST).date().isoformat()


def test_sade_sati_dates_use_requested_zone():
    from zoneinfo import ZoneInfo

    utc = sade_sati_period(0, NOW)
    kir = sade_sati_period(0, NOW, ZoneInfo("Pacific/Kiritimati"))  # +14 h
    assert utc["start"] <= kir["start"]
    assert (date.fromisoformat(kir["start"]) - date.fromisoformat(utc["start"])).days in (0, 1)


def test_panchang_end_local_date_next_day():
    p = panchang(date(2026, 11, 8), 40.7143, -74.006)  # tithi ends 02:01 next local day
    assert p["tithi"]["end_local_date"] == "2026-11-09" and p["tithi"]["end_local"] in ("02:01", "02:02")
    assert p["yoga"]["end_local_date"] == "2026-11-08"


def test_personal_day_window_dates_are_local(chart):
    r = personal_day(chart, date(2026, 10, 2), system="vedic", latitude=28.6139, longitude=77.209,
                     timezone="Asia/Kolkata")
    md = next(f for f in r["factors"] if f["id"].startswith("V.MD."))
    cur = chart["vedic"]["dasha"]["maha_dasha"]
    cur = refresh_time_dependent(chart, datetime(2026, 10, 2, 6, 30, tzinfo=timezone.utc))["vedic"]["dasha"]["maha_dasha"]
    assert md["window"] == [cur["start"], cur["end"]]


# ---------------------------------------------------------------- sensitivity
def test_sensitivity_flags_ascendant_cusp(chart):
    s = chart["metadata"]["sensitivity"]
    asc = next(n for n in s["near_cusp"] if n["point"] == "western_ascendant")
    assert (asc["from"], asc["to"], asc["flips_if_birth_time_is"]) == ("Capricorn", "Sagittarius", "earlier")
    assert 0.3 <= asc["minutes_to_boundary"] <= 1.0  # 0.14 deg at ~0.23 deg/min
    assert s["western_ascendant_near_sign_cusp_minutes"] == asc["minutes_to_boundary"]
    assert s["robust"] is False and s["window_minutes"] == 5.0


def test_sensitivity_flip_is_real(chart):
    """1.5 minutes earlier really does change the tropical Ascendant sign; 1.5 min later does not."""
    early = compute_natal_chart(date_of_birth=date(1987, 3, 17), time_of_birth=time(1, 39, 30),
                                has_exact_time=True, now_utc=NOW, **KW)
    late = compute_natal_chart(date_of_birth=date(1987, 3, 17), time_of_birth=time(1, 42, 30),
                               has_exact_time=True, now_utc=NOW, **KW)
    assert chart["rising_sign"]["sign"] == "Capricorn" == late["rising_sign"]["sign"]
    assert early["rising_sign"]["sign"] == "Sagittarius"


def test_sensitivity_robust_chart_and_unknown_time():
    c = compute_natal_chart(date_of_birth=date(1994, 7, 21), time_of_birth=time(14, 5), has_exact_time=True,
                            now_utc=NOW, latitude=19.076, longitude=72.8777, timezone="Asia/Kolkata")
    s = c["metadata"]["sensitivity"]
    assert s["robust"] is (not s["near_cusp"])
    for n in s["near_cusp"]:
        assert n["minutes_to_boundary"] <= 5.0
    u = compute_natal_chart(date_of_birth=date(1994, 7, 21), time_of_birth=None, has_exact_time=False,
                            now_utc=NOW, latitude=19.076, longitude=72.8777, timezone="Asia/Kolkata")
    assert u["metadata"]["sensitivity"] is None


def test_engine_version_bumped_for_local_dates():
    assert tuple(int(x) for x in ENGINE_VERSION.split(".")) >= (2, 1, 1)
