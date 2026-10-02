"""Natal chart orchestration -> `chart_data` (spec section 9)."""

from __future__ import annotations

import copy
from datetime import date, datetime, time, timedelta, timezone

import swisseph as swe

from . import dasha, ephemeris, transits
from .data.nakshatras import NAKSHATRAS
from .data.signs import CLASSICAL, OUTER, RASHIS, SIGNS, VEDIC_ORDER, WESTERN_PLANETS, sign_index
from .mathutil import deg2, lon2, norm360, sign_of
from .timeutil import ResolvedTime, require_aware, jd_from_utc, resolve_birth_time, to_utc_lenient
from .vedic import (
    Graha, d9, d10, functional_nature, graha_drishti, house_from, house_lords, lagna_entry,
    nakshatra_of, planet_entry,
)
from .sensitivity import sensitivity
from .version import ENGINE_VERSION
from .western import (
    Point, aspects_between, compute_houses, house_of, sign_data, western_summary,
)
from .yogas import LAGNA_DEPENDENT, YogaContext, compute_yogas, kaal_sarp, mangal_dosha

NODE_TYPE_WESTERN = "true"
NODE_TYPE_VEDIC = "mean"


def _probe_day(rt: ResolvedTime, dob: date, override: float | None) -> dict[str, dict]:
    """Per body, the tropical sign, sidereal rashi and nakshatra at local 00:00 and 23:59.
    Used on unknown-time charts: any change across the day means the placement is ambiguous.
    The sidereal node is the mean node (Rahu); the tropical one is the true node."""
    out: dict[str, dict] = {}
    for t in (time(0, 0), time(23, 59)):
        naive = datetime.combine(dob, t)
        if override is not None:
            utc = (naive - timedelta(minutes=override)).replace(tzinfo=timezone.utc)
        else:
            utc = to_utc_lenient(naive, rt.timezone)
        jd = jd_from_utc(utc)
        ay = ephemeris.ayanamsa_lahiri(jd)
        for name in WESTERN_PLANETS + ("North Node",):
            trop = ephemeris.calc(jd, "TrueNode" if name == "North Node" else name).longitude
            sid_src = ephemeris.calc(jd, "MeanNode" if name == "North Node" else name).longitude
            sid = norm360(sid_src - ay)
            e = out.setdefault(name, {"trop": [], "rashi": [], "nak": [], "sidlon": []})
            e["sidlon"].append(sid)
            e["trop"].append(sign_of(trop)[0])
            e["rashi"].append(sign_of(sid)[0])
            e["nak"].append(nakshatra_of(sid)[0])
    return out


def _num(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _validate_types(dob, tob, exact, lat, lon, tz, fold, override, now) -> None:
    from .errors import AstroInputError

    def bad(msg: str):
        raise AstroInputError("INVALID_INPUT", msg)

    if type(dob) is not date:  # datetime is a date subclass: reject it explicitly
        bad("date_of_birth must be a datetime.date")
    if tob is not None and (not isinstance(tob, time) or tob.tzinfo is not None):
        bad("time_of_birth must be a naive datetime.time (local wall time) or None")
    if not isinstance(exact, bool):
        bad("has_exact_time must be a bool")
    if not _num(lat) or not _num(lon):
        raise AstroInputError("INVALID_LOCATION", "latitude/longitude must be numbers")
    if tz is not None and not isinstance(tz, str):
        bad("timezone must be an IANA name string or None")
    if not isinstance(fold, int) or isinstance(fold, bool):
        bad("dst_fold must be 0 or 1")
    if override is not None and not _num(override):
        bad("utc_offset_override must be a number of minutes")
    if now is not None and (not isinstance(now, datetime) or now.tzinfo is None):
        bad("now_utc must be a timezone-aware datetime")


def _birth_tzinfo(zone_name: str | None, offset_minutes: float, tz_source: str):
    """Zone used to turn dasha / Sade Sati instants into the calendar dates users see."""
    if tz_source == "zoneinfo" and zone_name:
        from zoneinfo import ZoneInfo

        return ZoneInfo(zone_name)
    return timezone(timedelta(minutes=offset_minutes))


def _offset_value(minutes: float) -> float | int:
    return int(minutes) if float(minutes).is_integer() else round(minutes, 4)


def compute_natal_chart(
    *,
    date_of_birth: date,
    time_of_birth: time | None,
    has_exact_time: bool,
    latitude: float,
    longitude: float,
    timezone: str | None = None,
    dst_fold: int = 0,
    utc_offset_override: float | None = None,
    now_utc: datetime | None = None,
) -> dict:
    """Compute the full chart_data. Raises AstroInputError (.code) or EphemerisUnavailableError.

    `now_utc` only affects the time-dependent snapshot (current dasha, Sade Sati), which the
    service recomputes on read with `refresh_time_dependent`.
    """
    _validate_types(date_of_birth, time_of_birth, has_exact_time, latitude, longitude, timezone,
                    dst_fold, utc_offset_override, now_utc)
    now_utc = now_utc or datetime.now(tz=_utc())
    time_unknown = time_of_birth is None
    rt = resolve_birth_time(
        date_of_birth=date_of_birth, time_of_birth=time_of_birth, latitude=latitude,
        longitude=longitude, timezone_name=timezone, dst_fold=dst_fold,
        utc_offset_override=utc_offset_override,
    )
    jd = rt.jd_ut
    trop = {name: ephemeris.calc(jd, name) for name in WESTERN_PLANETS}
    true_node = ephemeris.calc(jd, "TrueNode")
    mean_node = ephemeris.calc(jd, "MeanNode")
    ayan = ephemeris.ayanamsa_lahiri(jd)
    hr = None if time_unknown else compute_houses(jd, latitude, longitude)
    angles_approx = (not time_unknown) and not has_exact_time

    probes: dict[str, dict] = {}
    if time_unknown:
        probes = _probe_day(rt, date_of_birth, utc_offset_override)

    def changed(body: str, key: str) -> bool:
        return bool(probes) and probes[body][key][0] != probes[body][key][1]

    trop_change = changed("Moon", "trop")
    rashi_change = changed("Moon", "rashi")
    moon_changes = changed("Moon", "nak")
    trop_candidates = list(dict.fromkeys(SIGNS[i] for i in probes["Moon"]["trop"])) if probes else []
    nak_candidates = list(dict.fromkeys(NAKSHATRAS[i].name for i in probes["Moon"]["nak"])) if probes else []
    sun_changes = changed("Sun", "trop")

    # ------------------------------------------------------------------ Western (tropical)
    points = {name: Point(name, p.longitude, p.speed) for name, p in trop.items()}
    points["North Node"] = Point("North Node", true_node.longitude, true_node.speed)
    south = norm360(true_node.longitude + 180.0)
    sun_sign_idx = sign_of(trop["Sun"].longitude)[0]

    def w_house(lon: float) -> int | None:
        """Placidus/Porphyry house; None when the birth time is unknown (no houses at all)."""
        return house_of(lon, hr.cusps) if hr else None

    w_planets = []
    for name in WESTERN_PLANETS + ("North Node", "South Node"):
        if name == "South Node":
            lon, speed = south, true_node.speed
        else:
            lon, speed = points[name].lon, points[name].speed
        idx, deg = sign_of(lon)
        retro = False if name in ("Sun", "Moon") else speed < 0
        entry = {"name": name, "sign": SIGNS[idx], "degree": deg2(deg), "house": w_house(lon),
                 "retrograde": retro, "longitude": lon2(lon), "speed": round(speed, 4)}
        if name == "North Node":
            # speed of the TRUE node can be positive; `retrograde` follows the speed sign. The
            # classical "nodes always move backward" convention lives in `mean_node_retrograde`.
            entry["retrograde"] = speed < 0
        if "Node" in name:
            entry["mean_node_retrograde"] = True
        if time_unknown:
            src = "North Node" if "Node" in name else name
            entry["approximate"] = changed(src, "trop")
            if entry["approximate"]:
                entry["candidates"] = list(dict.fromkeys(SIGNS[i] for i in probes[src]["trop"]
                                                         if name != "South Node")) \
                    if name != "South Node" else [SIGNS[(i + 6) % 12] for i in dict.fromkeys(probes[src]["trop"])]
        w_planets.append(entry)
    w_house_of = {p["name"]: p["house"] for p in w_planets if p["house"] is not None}

    if hr:
        houses = [dict(number=i + 1, **{k: v for k, v in sign_data(c).items() if k in ("sign", "degree")},
                       longitude=lon2(c)) for i, c in enumerate(hr.cusps)]
        if angles_approx:
            for h in houses:
                h["approximate"] = True
        rising = sign_data(hr.asc, approximate=angles_approx, include_longitude=True)
        mc = sign_data(hr.mc, approximate=angles_approx, include_longitude=True)
        aspect_points = list(points.values()) + [Point("ASC", hr.asc, hr.asc_speed),
                                                 Point("MC", hr.mc, hr.mc_speed)]
        house_system = hr.system
    else:
        houses = []  # unknown birth time: no houses (accuracy rules section 6)
        rising = {"sign": "Unknown", "degree": 0, "approximate": True}
        mc = None
        aspect_points = list(points.values())
        house_system = "none"

    sun_data = sign_data(trop["Sun"].longitude, house=w_house_of.get("Sun"), approximate=sun_changes)
    if time_unknown:
        sun_data["candidates"] = list(dict.fromkeys(SIGNS[i] for i in probes["Sun"]["trop"]))
    moon_data = sign_data(trop["Moon"].longitude, house=w_house_of.get("Moon"), approximate=trop_change)
    if time_unknown:
        moon_data["candidates"] = trop_candidates
    if angles_approx:
        sun_data["approximate_house"] = moon_data["approximate_house"] = True

    # ------------------------------------------------------------------ Vedic (sidereal)
    def sid(lon: float) -> float:
        return norm360(lon - ayan)

    grahas: dict[str, Graha] = {}
    for name in CLASSICAL + OUTER:
        p = trop[name]
        grahas[name] = Graha(name, sid(p.longitude), p.speed,
                             False if name in ("Sun", "Moon") else p.speed < 0)
    rahu = sid(mean_node.longitude)
    grahas["Rahu"] = Graha("Rahu", rahu, mean_node.speed, True)
    grahas["Ketu"] = Graha("Ketu", norm360(rahu + 180.0), mean_node.speed, True)
    signs = {n: sign_of(g.lon)[0] for n, g in grahas.items()}
    moon_sid = grahas["Moon"].lon
    sun_sid = grahas["Sun"].lon

    if hr:
        lagna_lon = sid(hr.asc)
        lagna_sign = sign_of(lagna_lon)[0]
        basis = "ascendant"
    else:
        lagna_lon = None
        lagna_sign = None   # unknown birth time: no lagna, no houses
        basis = "none"
    lagna = lagna_entry(lagna_lon, lagna_sign, basis=basis, moon_lon=moon_sid) if hr else None
    if lagna is not None and angles_approx:
        lagna["approximate"] = True

    def v_house(sign_idx: int) -> int | None:
        return None if lagna_sign is None else house_from(sign_idx, lagna_sign)

    v_planets = [planet_entry(grahas[n], house=v_house(signs[n]), sun_lon=sun_sid)
                 for n in VEDIC_ORDER]
    if time_unknown:
        for vp in v_planets:
            src = "North Node" if vp["english"] in ("Rahu", "Ketu") else vp["english"]
            vp["approximate"] = changed(src, "rashi")
            vp["nakshatra_approximate"] = changed(src, "nak")
            if vp["approximate"]:
                shift = 6 if vp["english"] == "Ketu" else 0
                vp["candidates"] = [RASHIS[(i + shift) % 12]
                                    for i in dict.fromkeys(probes[src]["rashi"])]
    by_name = {p["english"]: p for p in v_planets}

    nk_idx, nk_pada = nakshatra_of(moon_sid)
    nk = NAKSHATRAS[nk_idx]
    moon_nak = {"name": nk.name, "pada": nk_pada, "lord": nk.lord, "deity": nk.deity,
                "symbol": nk.symbol, "nature": nk.nature, "gana": nk.gana, "nadi": nk.nadi,
                "yoni": nk.yoni, "approximate": moon_changes}
    if time_unknown:
        moon_nak["candidates"] = nak_candidates
        moon_nak["rashi_changes"] = rashi_change

    ctx = YogaContext(by_name, signs, {n: g.lon for n, g in grahas.items()}, lagna_sign)
    yogas = compute_yogas(ctx)
    yogas.append(kaal_sarp(ctx))
    mangal_entry, manglik = mangal_dosha(ctx)
    yogas.append(mangal_entry)
    if time_unknown:
        for y in yogas:
            y["approximate"] = True  # computed for local noon; Moon/sign placements may differ
        manglik["approximate"] = True

    waxing = norm360(moon_sid - sun_sid) < 180.0
    if lagna_sign is None:
        benefics, malefics, yogakaraka = [], [], None   # functional nature is lagna-based
    else:
        benefics, malefics, yogakaraka = functional_nature(lagna_sign, waxing)

    def varga(fn) -> dict:
        vl_sign = fn(lagna_lon)[0]
        planets = []
        for n in VEDIC_ORDER:
            vs, vd = fn(grahas[n].lon)
            planets.append(planet_entry(grahas[n], house=house_from(vs, vl_sign), sun_lon=sun_sid,
                                        rashi_idx=vs, degree=vd))
        return {"lagna": {"rashi": RASHIS[vl_sign], "rashi_english": SIGNS[vl_sign], "basis": basis},
                "planets": planets}

    birth_utc = rt.utc
    date_tz = _birth_tzinfo(rt.timezone, rt.utc_offset_minutes, rt.tz_source)
    vedic = {
        # Reported as the MEAN Lahiri value (published/JH convention, J2000 = 23.8571). The
        # sidereal longitudes subtract the TRUE value from the apparent (true-equinox) tropical
        # longitude, which is identical to mean tropical - mean ayanamsa and to
        # `swetest -sid1` output, so nutation cancels and positions match JH.
        "ayanamsa_value": round(ephemeris.ayanamsa_lahiri_mean(jd), 4),
        "ayanamsa_true_value": round(ayan, 4),
        "ayanamsa": "lahiri",
        "house_system": "whole_sign",
        "lagna": lagna,
        "planets": v_planets,
        "moon_nakshatra": moon_nak,
        "dasha": dasha.compute(moon_sid, birth_utc, now_utc, approximate=time_unknown,
                               moon_range=probes["Moon"]["sidlon"] if probes else None,
                               tz=date_tz, tz_name=rt.timezone or f"UTC{rt.utc_offset_minutes:+g}min"),
        "yogas": yogas,
        "manglik": manglik,
        "house_lords": [] if lagna_sign is None else house_lords(lagna_sign, signs),
        "functional_benefics": benefics,
        "functional_malefics": malefics,
        "yogakaraka": yogakaraka,
        "sade_sati": transits.sade_sati(signs["Moon"], now_utc),
        "aspects": graha_drishti(signs, lagna_sign),
    }
    vedic["houses_available"] = hr is not None
    if hr is not None:  # divisional charts need the exact birth time; omitted otherwise
        vedic["navamsa_d9"] = varga(d9)
        vedic["dashamsa_d10"] = varga(d10)
    else:
        vedic["moon_range_sidereal"] = [round(x, 4) for x in probes["Moon"]["sidlon"]]
        vedic["suppressed"] = {
            "reason": "birth time unknown (accuracy rules section 6)",
            "items": ["lagna", "houses", "house_lords", "functional_nature", "yogakaraka",
                      "navamsa_d9", "dashamsa_d10", *LAGNA_DEPENDENT],
        }

    metadata = {
        "house_system": house_system,
        "approximate_time": time_unknown,
        "engine_version": ENGINE_VERSION,
        "ephemeris": "swieph",
        "swe_version": swe.version,
        "zodiac_western": "tropical",
        "ayanamsa": "lahiri",
        "ayanamsa_value_convention": "mean",
        "sidereal_longitude_basis": "apparent_tropical_minus_true_ayanamsa (== mean - mean; swetest -sid1)",
        "node_type_western": NODE_TYPE_WESTERN,
        "node_type_vedic": NODE_TYPE_VEDIC,
        "vedic_house_system": "whole_sign",
        "utc_datetime": birth_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "local_datetime_used": rt.local.isoformat(),
        "jd_ut": round(jd, 6),
        "timezone": rt.timezone,
        "utc_offset_minutes": _offset_value(rt.utc_offset_minutes),
        "tz_source": rt.tz_source,
        "tz_confidence": rt.tz_confidence,
        "ambiguous_time": rt.ambiguous_time,
        "dst_fold": dst_fold,
        "lagna_basis": basis,
        "houses_available": hr is not None,
        "has_exact_time": has_exact_time and not time_unknown,
        "snapshot_at": now_utc.astimezone(_utc()).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    metadata["sensitivity"] = None if time_unknown else sensitivity(jd, latitude, longitude)
    if time_unknown:
        metadata["time_basis"] = "local_noon"
        metadata["suppressed_when_time_unknown"] = [
            "houses", "ascendant", "midheaven", "planet house numbers", "lagna", "vedic houses",
            "lagna-based yogas", "divisional charts (D9/D10)"]

    chart = {
        "sun_sign": sun_data,
        "moon_sign": moon_data,
        "rising_sign": rising,
        "planets": w_planets,
        "houses": houses,
        "aspects": aspects_between(aspect_points),
        "metadata": metadata,
        "vedic": vedic,
        "western_summary": western_summary(points, hr.asc if hr else None,
                                           w_house_of if hr else {}),
    }
    if mc is not None:
        chart["mc"] = mc
    return chart


def _utc():
    return timezone.utc


def refresh_time_dependent(chart_data: dict, now_utc: datetime) -> dict:
    """Return a copy with `vedic.dasha` current pointers and `vedic.sade_sati` for `now_utc`
    (spec 5.2 / 5.6: stored values are a snapshot; recompute on read). Needs the ephemeris
    only for transiting Saturn."""
    require_aware(now_utc)
    out = copy.deepcopy(chart_data)
    vedic = out.get("vedic")
    if not vedic:
        return out
    meta = out["metadata"]
    birth_utc = datetime.strptime(meta["utc_datetime"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_utc())
    d = vedic["dasha"]
    moon = d.get("moon_longitude")
    if moon is None:  # older snapshot: fall back to the (2-dp) planet longitude
        moon = next(p["longitude"] for p in vedic["planets"] if p["english"] == "Moon")
    date_tz = _birth_tzinfo(meta.get("timezone"), meta.get("utc_offset_minutes", 0), meta.get("tz_source", "user_override"))
    d.update(dasha.current(moon, birth_utc, now_utc, d.get("year_days", 365.25), date_tz))
    if d.get("approximate"):  # unknown birth time: pointers stay flagged, candidates refreshed
        dasha.mark_approximate(d, d.get("moon_range"), birth_utc, now_utc, d.get("year_days", 365.25), date_tz)
    moon_rashi = sign_index(next(p["rashi"] for p in vedic["planets"] if p["english"] == "Moon"))
    vedic["sade_sati"] = transits.sade_sati(moon_rashi, now_utc, with_dates=True, tz=date_tz)
    meta["snapshot_at"] = now_utc.astimezone(_utc()).strftime("%Y-%m-%dT%H:%M:%SZ")
    return out
