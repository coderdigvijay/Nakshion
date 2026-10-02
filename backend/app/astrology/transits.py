"""Transits and timing (spec section 6): event finder, Sade Sati, daily sky for sign
horoscopes (api-contract 7.1 `transit_data`), personal transits for a natal chart."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone, tzinfo
from typing import Callable

from . import ephemeris
from .data.signs import RASHIS, SIGNS, WESTERN_PLANETS, sign_index
from .mathutil import deg2, lon2, norm360, separation, sign_of, signed_diff
from .timeutil import jd_from_utc, require_aware
from .western import ASPECTS, Point, find_aspect, is_applying

MINUTE = 1.0 / 1440.0
# Personal transit orbs (spec 6.3), by transiting body.
TRANSIT_ORBS = {"Moon": 3.0, "Sun": 2.0, "Mercury": 2.0, "Venus": 2.0, "Mars": 2.0,
                "Jupiter": 2.0, "Saturn": 2.0, "Uranus": 1.5, "Neptune": 1.5, "Pluto": 1.5}
SEARCH_STEP = {"Moon": 2.0 / 24.0, "Sun": 1.0, "Mercury": 1.0, "Venus": 1.0, "Mars": 1.0}
SLOW_STEP = 3.0
NATAL_TARGETS = ("Sun", "Moon", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "ASC", "MC")
PTOLEMAIC = {"conjunction": 0.0, "sextile": 60.0, "square": 90.0, "trine": 120.0, "opposition": 180.0}
MOON_PHASES = ("new_moon", "waxing_crescent", "first_quarter", "waxing_gibbous",
               "full_moon", "waning_gibbous", "last_quarter", "waning_crescent")


def jd_to_datetime(jd: float) -> datetime:
    return datetime(2000, 1, 1, 12, tzinfo=timezone.utc) + timedelta(days=jd - 2451545.0)


def iso_minute(jd: float) -> str:
    dt = jd_to_datetime(jd) + timedelta(seconds=30)
    return dt.strftime("%Y-%m-%dT%H:%M:00Z")


def find_events(f: Callable[[float], float], t0: float, t1: float, step: float) -> list[float]:
    """Roots of a signed angular function on [t0, t1] (spec 6.2): sample at `step`, then bisect
    each sign change to 1 minute. Jumps across +-180 (wrap, not a root) are ignored."""
    roots = []
    a, fa = t0, f(t0)
    while a < t1:
        b = min(a + step, t1)
        fb = f(b)
        if fa == 0.0:
            roots.append(a)
        elif fa * fb < 0 and abs(fa) < 90.0 and abs(fb) < 90.0:
            lo, hi, flo = a, b, fa
            while hi - lo > MINUTE:
                mid = (lo + hi) / 2.0
                fm = f(mid)
                if flo * fm <= 0:
                    hi = mid
                else:
                    lo, flo = mid, fm
            roots.append((lo + hi) / 2.0)
        a, fa = b, fb
    return roots


def _lon(body: str, jd: float, sidereal: bool = False) -> float:
    lon = ephemeris.calc(jd, body).longitude
    return norm360(lon - ephemeris.ayanamsa_lahiri(jd)) if sidereal else lon


# --------------------------------------------------------------------------- Sade Sati

def _saturn_sign(jd: float) -> int:
    return sign_of(_lon("Saturn", jd, sidereal=True))[0]


def sade_sati_period(natal_moon_rashi: int, now_utc: datetime, tz: tzinfo | None = None) -> dict | None:
    """Start/end dates (YYYY-MM-DD, UTC) of the current Sade Sati, or of the next one if none
    is running. Period = Saturn (sidereal) in the 12th/1st/2nd sign from the natal Moon.
    Saturn's retrograde dips back out of the three signs for months; gaps shorter than 1.5 years
    are treated as inside one period (start = first ingress, end = last exit)."""
    targets = {(natal_moon_rashi + k) % 12 for k in (-1, 0, 1)}
    jd_now = jd_from_utc(require_aware(now_utc))
    step, merge_gap = 20.0, 550.0
    lo_jd, hi_jd = jd_now - 12 * 365.25, jd_now + 31 * 365.25  # a Saturn cycle is ~29.5 y
    inside = []
    t = lo_jd
    while t <= hi_jd:
        inside.append((t, _saturn_sign(t) in targets))
        t += step
    runs, cur = [], None
    for t, flag in inside:
        if flag:
            if cur is None:
                cur = [t, t]
            elif t - cur[1] <= merge_gap:
                cur[1] = t
            else:
                runs.append(cur)
                cur = [t, t]
    if cur:
        runs.append(cur)

    def refine(a: float, b: float, want_inside_at_b: bool) -> float:
        """Bisect an in/out boundary between a and b to < 1 day."""
        while b - a > 0.5:
            m = (a + b) / 2.0
            if (_saturn_sign(m) in targets) == want_inside_at_b:
                b = m
            else:
                a = m
        return b if want_inside_at_b else a

    def first_inside(t0: float) -> float:   # first inside instant at/after sample t0 (run start)
        prev = t0 - step
        return refine(prev, t0, True) if _saturn_sign(prev) not in targets else t0

    def last_inside(t1: float) -> float:
        nxt = t1 + step
        return refine(t1, nxt, False) if _saturn_sign(nxt) not in targets else t1

    for a, b in runs:
        if b < jd_now - 1.0:
            continue
        start, end = first_inside(a), last_inside(b)
        if a <= lo_jd + step:   # run began before the scan window: start unknown, extend back
            start = None
        fmt = lambda j: None if j is None else jd_to_datetime(j).astimezone(tz or timezone.utc).strftime("%Y-%m-%d")
        return {"start": fmt(start), "end": fmt(end), "running": start is None or start <= jd_now}
    return None


def sade_sati(natal_moon_rashi: int, now_utc: datetime, *, with_dates: bool = False,
              tz: tzinfo | None = None) -> dict:
    """Transiting sidereal Saturn in the 12th / 1st / 2nd sign from the natal Moon sign."""
    jd = jd_from_utc(require_aware(now_utc))
    saturn_sign = _saturn_sign(jd)
    rel = (saturn_sign - natal_moon_rashi) % 12 + 1
    phase = {12: "rising", 1: "peak", 2: "setting"}.get(rel, "none")
    out = {"active": phase != "none", "phase": phase, "saturn_rashi": RASHIS[saturn_sign],
           "computed_for": now_utc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    if with_dates:
        period = sade_sati_period(natal_moon_rashi, now_utc, tz)
        out["start"] = period["start"] if period else None
        out["end"] = period["end"] if period else None
    return out


# --------------------------------------------------------------------------- daily sky

def _positions(jd: float, sidereal: bool) -> dict[str, Point]:
    ay = ephemeris.ayanamsa_lahiri(jd) if sidereal else 0.0
    out = {}
    for name in WESTERN_PLANETS:
        p = ephemeris.calc(jd, name)
        out[name] = Point(name, norm360(p.longitude - ay), p.speed)
    return out


def _moon_phase_name(elongation: float) -> str:
    return MOON_PHASES[int(((elongation + 22.5) % 360.0) // 45.0)]


def _next_moon_ingress(jd: float, sidereal: bool) -> float:
    sign = sign_of(_lon("Moon", jd, sidereal))[0]
    boundary = (sign + 1) * 30.0
    roots = find_events(lambda t: signed_diff(_lon("Moon", t, sidereal), boundary),
                        jd, jd + 3.0, 2.0 / 24.0)
    return roots[0] if roots else jd + 3.0


def is_void_of_course(jd: float, sidereal: bool = False) -> bool:
    """No Ptolemaic aspect from the Moon to Sun..Saturn perfects before the Moon's ingress."""
    end = _next_moon_ingress(jd, sidereal)
    for body in ("Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn"):
        for angle in PTOLEMAIC.values():
            targets = (angle,) if angle in (0.0, 180.0) else (angle, -angle)
            for tgt in targets:
                f = (lambda t, b=body, g=tgt: signed_diff(
                    signed_diff(_lon("Moon", t, sidereal), _lon(b, t, sidereal)), g))
                if find_events(f, jd, end, 2.0 / 24.0):
                    return False
    return True


def _ingresses(jd0: float, jd1: float, sidereal: bool) -> list[dict]:
    out = []
    for name in WESTERN_PLANETS:
        s0, s1 = sign_of(_lon(name, jd0, sidereal))[0], sign_of(_lon(name, jd1, sidereal))[0]
        if s0 == s1:
            continue
        # A body can only cross one boundary within a day (the Moon moves < 16 deg/day).
        boundary = (s0 + 1) * 30.0 if (s1 - s0) % 12 == 1 else s0 * 30.0
        roots = find_events(lambda t, n=name: signed_diff(_lon(n, t, sidereal), boundary),
                            jd0, jd1, 1.0 / 24.0)
        names = RASHIS if sidereal else SIGNS
        out.append({"planet": name, "from": names[s0], "to": names[s1],
                    "at": iso_minute(roots[0]) if roots else None})
    return out


def sign_transit_data(sign: str, day: date, system: str = "western") -> dict:
    """`transit_data` for a sign horoscope (api-contract 7.1, spec 8.1/8.2).

    western: tropical positions, house 1 = the given Sun sign (solar whole-sign houses).
    vedic:   sidereal (Lahiri) positions, house 1 = the given Moon rashi.
    Positions and the Moon are taken at 00:00 UTC of `day` (= computed_for); aspects at
    12:00 UTC with a 1.5 deg orb (Moon 3 deg) so they hold for most of the day.
    """
    if system not in ("western", "vedic"):
        raise ValueError("system must be 'western' or 'vedic'")
    sidereal = system == "vedic"
    first = sign_index(sign)
    t0 = datetime.combine(day, time(0), tzinfo=timezone.utc)
    jd0 = jd_from_utc(t0)
    pos = _positions(jd0, sidereal)
    names = RASHIS if sidereal else SIGNS

    elong = norm360(pos["Moon"].lon - pos["Sun"].lon)
    moon_sign = sign_of(pos["Moon"].lon)[0]
    moon = {"sign": names[moon_sign], "phase": _moon_phase_name(elong),
            "illumination": round(ephemeris.moon_phase(jd0), 2),
            "void_of_course": is_void_of_course(jd0, sidereal)}

    positions = []
    for name, p in pos.items():
        idx, deg = sign_of(p.lon)
        positions.append({"planet": name, "sign": names[idx], "degree": deg2(deg),
                          "retrograde": p.speed < 0, "house": (idx - first) % 12 + 1})

    noon = _positions(jd0 + 0.5, sidereal)
    aspects = []
    bodies = list(noon.values())
    for i, a in enumerate(bodies):
        for b in bodies[i + 1:]:
            limit = 3.0 if "Moon" in (a.name, b.name) else 1.5
            sep = separation(a.lon, b.lon)
            for asp, ang in PTOLEMAIC.items():
                orb = abs(sep - ang)
                if orb <= limit:
                    aspects.append({"planet1": a.name, "planet2": b.name, "type": asp,
                                    "orb": round(orb, 2), "applying": is_applying(a, b, ang)})
    aspects.sort(key=lambda x: x["orb"])

    moon_house = (moon_sign - first) % 12 + 1
    highlighted = sorted({(sign_of(pos[n].lon)[0] - first) % 12 + 1
                          for n in ("Moon", "Sun", "Mercury", "Venus", "Mars")})
    return {
        "computed_for": t0.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "zodiac": "sidereal" if sidereal else "tropical",
        "ayanamsa": "lahiri" if sidereal else None,
        "basis_sign": names[first],
        "moon": moon,
        "positions": positions,
        "aspects_today": aspects,
        "ingresses_today": _ingresses(jd0, jd0 + 1.0, sidereal),
        "solar_house_focus": {"moon_house": moon_house, "highlighted_houses": highlighted},
    }


# --------------------------------------------------------------------------- personal

def _natal_points(chart: dict) -> dict[str, float]:
    pts = {p["name"]: p["longitude"] for p in chart["planets"] if p["name"] in NATAL_TARGETS}
    if not chart.get("metadata", {}).get("approximate_time"):
        if "longitude" in chart.get("rising_sign", {}):
            pts["ASC"] = chart["rising_sign"]["longitude"]
        if chart.get("mc") and "longitude" in chart["mc"]:
            pts["MC"] = chart["mc"]["longitude"]
    return pts


def _window(body: str, natal: float, angle: float, orb: float, jd: float) -> dict:
    step = SEARCH_STEP.get(body, SLOW_STEP)
    span = 3.0 if body == "Moon" else 30.0 if body in SEARCH_STEP else 400.0

    def exact(t: float) -> float:
        # Conjunction/opposition touch an extremum of the separation, so use a signed
        # difference there; other aspects cross separation == angle.
        d = signed_diff(_lon(body, t), natal)
        if angle == 0.0:
            return d
        if angle == 180.0:
            return signed_diff(d, 180.0)
        return abs(d) - angle

    def edge(t: float) -> float:
        return abs(separation(_lon(body, t), natal) - angle) - orb

    exacts = find_events(exact, jd - span, jd + span, step)
    exact_at = min(exacts, key=lambda r: abs(r - jd)) if exacts else None
    if exact_at is not None and abs(exact_at - jd) > (3.0 if body == "Moon" else 30.0):
        exact_at = None
    edges = find_events(edge, jd - span, jd + span, step)
    before = [r for r in edges if r <= jd]
    after = [r for r in edges if r > jd]
    return {"exact_at": iso_minute(exact_at) if exact_at else None,
            "window_start": iso_minute(max(before)) if before else None,
            "window_end": iso_minute(min(after)) if after else None}


def compute_transits(chart_data: dict, at_utc: datetime, *, with_windows: bool = True) -> dict:
    """Personal transit factors for one natal chart at `at_utc` (spec 6.3)."""
    jd = jd_from_utc(require_aware(at_utc, "at_utc"))
    pos = _positions(jd, sidereal=False)
    natal = _natal_points(chart_data)
    western = []
    for tname, tp in pos.items():
        for nname, nlon in natal.items():
            sep = separation(tp.lon, nlon)
            for asp, ang in PTOLEMAIC.items():
                orb = abs(sep - ang)
                if orb > TRANSIT_ORBS[tname]:
                    continue
                entry = {"transiting": tname, "natal": nname, "type": asp, "orb": round(orb, 2),
                         "applying": is_applying(tp, Point(nname, nlon, 0.0), ang)}
                if with_windows:
                    entry.update(_window(tname, nlon, ang, TRANSIT_ORBS[tname], jd))
                western.append(entry)
    western.sort(key=lambda x: x["orb"])

    vedic = chart_data.get("vedic") or {}
    out = {"computed_for": at_utc.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
           "western": western}
    if vedic:
        moon_rashi = sign_index(next(p["rashi"] for p in vedic["planets"] if p["english"] == "Moon"))
        lagna_rashi = sign_index(vedic["lagna"]["rashi"]) if vedic.get("lagna") else None
        ay = ephemeris.ayanamsa_lahiri(jd)
        sid = {n: norm360(p.lon - ay) for n, p in pos.items()}
        rahu = norm360(ephemeris.calc(jd, "MeanNode").longitude - ay)
        sid["Rahu"], sid["Ketu"] = rahu, norm360(rahu + 180.0)
        gochara = []
        for body in ("Jupiter", "Saturn", "Rahu", "Ketu"):
            s = sign_of(sid[body])[0]
            gochara.append({"planet": body, "rashi": RASHIS[s],
                            "house_from_moon": (s - moon_rashi) % 12 + 1,
                            "house_from_lagna": None if lagna_rashi is None else (s - lagna_rashi) % 12 + 1})
        out["vedic"] = {
            "gochara": gochara,
            "moon_transit_house": (sign_of(sid["Moon"])[0] - moon_rashi) % 12 + 1,
            "moon_transit_rashi": RASHIS[sign_of(sid["Moon"])[0]],
            "sade_sati": sade_sati(moon_rashi, at_utc),
            "lagna_basis": chart_data.get("metadata", {}).get("lagna_basis", "ascendant"),
            "houses_available": bool(vedic.get("lagna")),
        }
    return out
