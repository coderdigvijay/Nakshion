"""Panchang (spec 5.7): tithi, paksha, nakshatra, yoga, karana, vara, sunrise/sunset, Rahu Kaal.

Conventions (all pinned in tests):
- Day boundary: local sunrise (Hindu civil day). Sunrise/sunset = Sun's UPPER LIMB with
  refraction (swe.rise_trans, 1013.25 hPa, 15 C, sea level). DEVIATION from spec 5.7 (disc
  centre): Drik Panchang, the golden reference, uses the upper limb; disc centre was 1-3 min
  late at sunrise (London 08:08 vs Drik 08:05) and would break the +-2 min gate.
- Element values are those at sunrise; end times are root-found to 1 minute.
- Polar day/night (no sunrise): the boundary falls back to local 06:00, and `sunrise_available`
  is False; Rahu Kaal is then None.
- Tithi/karana use the elongation (Moon - Sun, ayanamsa cancels); nakshatra and yoga use the
  sidereal (Lahiri) longitudes.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from . import ephemeris
from .data.nakshatras import NAKSHATRAS
from .mathutil import norm360, signed_diff
from .timeutil import jd_from_utc, resolve_timezone, validate_location
from .transits import find_events, iso_minute, jd_to_datetime
from .vedic import nakshatra_of

TITHIS = ("Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami",
          "Ashtami", "Navami", "Dashami", "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi")
YOGAS = ("Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda", "Sukarma",
         "Dhriti", "Shula", "Ganda", "Vriddhi", "Dhruva", "Vyaghata", "Harshana", "Vajra",
         "Siddhi", "Vyatipata", "Variyana", "Parigha", "Shiva", "Siddha", "Sadhya", "Shubha",
         "Shukla", "Brahma", "Indra", "Vaidhriti")
REPEATING_KARANAS = ("Bava", "Balava", "Kaulava", "Taitila", "Garaja", "Vanija", "Vishti")
VARAS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
# Rahu Kaal: part (1..8) of the sunrise-sunset span, by Python weekday (Mon=0). Spec 5.7.
RAHU_PART = {0: 2, 1: 7, 2: 5, 3: 6, 4: 4, 5: 3, 6: 8}


def tithi_name(n: int) -> str:
    """n = 1..30."""
    if n == 15:
        return "Purnima"
    if n == 30:
        return "Amavasya"
    return TITHIS[(n - 1) % 15]


def karana_name(k: int) -> str:
    """k = 0..59 half-tithi index (spec 5.7)."""
    if k == 0:
        return "Kimstughna"
    if k >= 57:
        return ("Shakuni", "Chatushpada", "Naga")[k - 57]
    return REPEATING_KARANAS[(k - 1) % 7]


def _sun_moon(jd: float) -> tuple[float, float]:
    return ephemeris.calc(jd, "Sun").longitude, ephemeris.calc(jd, "Moon").longitude


def _state(jd: float) -> dict:
    sun, moon = _sun_moon(jd)
    ay = ephemeris.ayanamsa_lahiri(jd)
    elong = norm360(moon - sun)
    msid, ssid = norm360(moon - ay), norm360(sun - ay)
    return {"tithi": int(elong // 12.0) + 1, "karana": int(elong // 6.0),
            "nak": nakshatra_of(msid)[0], "pada": nakshatra_of(msid)[1],
            "yoga": int(norm360(msid + ssid) * 27.0 // 360.0)}


def _end_of(jd: float, expr, boundary_fn) -> float | None:
    """First time after `jd` the quantity `expr` reaches the next boundary (root-found)."""
    horizon = jd + 2.0  # the longest element (tithi ~26 h, nakshatra ~27 h, yoga ~ 1.1 d) fits
    roots = find_events(boundary_fn, jd, horizon, 1.0 / 24.0)
    return roots[0] if roots else None


def _end_times(jd: float, st: dict) -> dict:
    def moon_sun_diff(t, target):  # elongation - target, wrapped
        s, m = _sun_moon(t)
        return signed_diff(m - s, target)

    def sidereal_sum_diff(t, target):  # (moon+sun sidereal) - target; the 2*ayanamsa is NOT cancelled
        s, m = _sun_moon(t)
        ay = ephemeris.ayanamsa_lahiri(t)
        return signed_diff(m + s - 2 * ay, target)

    def moon_sid_diff(t, target):
        return signed_diff(ephemeris.calc(t, "Moon").longitude - ephemeris.ayanamsa_lahiri(t), target)

    t_end = _end_of(jd, None, lambda t: moon_sun_diff(t, (st["tithi"] % 30) * 12.0))
    k_end = _end_of(jd, None, lambda t: moon_sun_diff(t, ((st["karana"] + 1) % 60) * 6.0))
    n_end = _end_of(jd, None, lambda t: moon_sid_diff(t, ((st["nak"] + 1) % 27) * (40.0 / 3.0)))
    y_end = _end_of(jd, None, lambda t: sidereal_sum_diff(t, ((st["yoga"] + 1) % 27) * (40.0 / 3.0)))
    return {"tithi": t_end, "karana": k_end, "nakshatra": n_end, "yoga": y_end}


def _local_midnight_utc(day: date, zone: ZoneInfo) -> datetime:
    return datetime.combine(day, time(0), tzinfo=zone).astimezone(timezone.utc)


def panchang(day: date, latitude: float, longitude: float, timezone_name: str | None = None) -> dict:
    """Panchang for the local civil `day` at a place. Times are ISO-8601 UTC ("...Z")
    plus local "HH:MM" strings in `timezone`."""
    validate_location(latitude, longitude)
    tzname = timezone_name or resolve_timezone(latitude, longitude)
    zone = ZoneInfo(tzname)
    start_utc = _local_midnight_utc(day, zone)
    jd0 = jd_from_utc(start_utc)
    rise = ephemeris.sun_rise_set(jd0, latitude, longitude, rise=True)
    # Guard: the first sunrise after local midnight must still fall on this local date.
    if rise is not None and jd_to_datetime(rise).astimezone(zone).date() != day:
        rise = None
    sunrise_available = rise is not None
    if rise is None:
        boundary = datetime.combine(day, time(6, 0), tzinfo=zone).astimezone(timezone.utc)
        jd_b = jd_from_utc(boundary)
        sset = None
    else:
        jd_b = rise
        sset = ephemeris.sun_rise_set(rise, latitude, longitude, rise=False)

    st = _state(jd_b)
    ends = _end_times(jd_b, st)

    def local_hm(jd: float | None) -> str | None:
        if jd is None:
            return None
        return (jd_to_datetime(jd) + timedelta(seconds=30)).astimezone(zone).strftime("%H:%M")

    def local_date(jd: float | None) -> str | None:
        if jd is None:
            return None
        return (jd_to_datetime(jd) + timedelta(seconds=30)).astimezone(zone).date().isoformat()

    def stamp(jd):
        return iso_minute(jd) if jd is not None else None

    nxt = _state(ends["tithi"] + 1.0 / 1440.0) if ends["tithi"] else None
    vara_idx = day.weekday()
    rahu = None
    if rise is not None and sset is not None:
        part = (sset - rise) / 8.0
        n = RAHU_PART[vara_idx]
        rahu = {"start": stamp(rise + part * (n - 1)), "end": stamp(rise + part * n),
                "start_local": local_hm(rise + part * (n - 1)), "end_local": local_hm(rise + part * n)}
    paksha = "Shukla" if st["tithi"] <= 15 else "Krishna"
    return {
        "date": day.isoformat(), "timezone": tzname, "latitude": latitude, "longitude": longitude,
        "sunrise": stamp(rise), "sunset": stamp(sset),
        "sunrise_local": local_hm(rise), "sunset_local": local_hm(sset),
        "sunrise_available": sunrise_available,
        "day_boundary": "sunrise" if sunrise_available else "local_06:00 (no sunrise)",
        "vara": VARAS[vara_idx],
        "tithi": {"number": st["tithi"], "name": tithi_name(st["tithi"]), "paksha": paksha,
                  "end": stamp(ends["tithi"]), "end_local": local_hm(ends["tithi"]), "end_local_date": local_date(ends["tithi"]),
                  "next": tithi_name(nxt["tithi"]) if nxt else None},
        "nakshatra": {"name": NAKSHATRAS[st["nak"]].name, "pada": st["pada"],
                      "lord": NAKSHATRAS[st["nak"]].lord,
                      "end": stamp(ends["nakshatra"]), "end_local": local_hm(ends["nakshatra"]),
                      "end_local_date": local_date(ends["nakshatra"])},
        "yoga": {"number": st["yoga"] + 1, "name": YOGAS[st["yoga"]],
                 "end": stamp(ends["yoga"]), "end_local": local_hm(ends["yoga"]),
                 "end_local_date": local_date(ends["yoga"])},
        "karana": {"number": st["karana"], "name": karana_name(st["karana"]),
                   "end": stamp(ends["karana"]), "end_local": local_hm(ends["karana"]),
                   "end_local_date": local_date(ends["karana"])},
        "rahu_kaal": rahu,
        "conventions": {"sunrise": "Sun upper limb, refraction 1013.25 hPa/15C, sea level (Drik convention)",
                        "zodiac": "sidereal Lahiri (nakshatra, yoga)", "elements_at": "sunrise"},
    }
