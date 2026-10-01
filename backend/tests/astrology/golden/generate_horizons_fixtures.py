"""Offline generator for the planet-position golden fixtures.

NOT run in CI (it calls the network). Run by hand when the case list changes:

    backend/venv/bin/python backend/tests/astrology/golden/generate_horizons_fixtures.py

Source: NASA/JPL Horizons API (https://ssd.jpl.nasa.gov/api/horizons.api), ephemeris DE441,
observer table quantity 31 = observer-centred ecliptic-of-date longitude/latitude of the
target's *apparent* position (light-time, aberration, deflection). That is the same frame as
Swiss Ephemeris' default `calc_ut` output (apparent, true equinox of date), but computed by an
independent code base, so it satisfies the "never from the code under test" rule
(.claude/astrology_accuracy_rules.md section 9).

Each case is a UT instant (or TT for the ephemeris-range-edge cases, where Horizons' and Swiss
Ephemeris' Delta-T extrapolations legitimately differ by minutes).
"""

from __future__ import annotations

import json
import subprocess
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).parent / "fixtures" / "horizons_positions.json"

BODIES = {
    "Sun": "10", "Moon": "301", "Mercury": "199", "Venus": "299",
    # Mars..Pluto: system barycentres. Horizons' body-centre series for the gas giants end at
    # A.D. 2200 (satellite ephemerides); the barycentre offset is < 0.0003 deg geocentric.
    "Mars": "4", "Jupiter": "5", "Saturn": "6", "Uranus": "7", "Neptune": "8", "Pluto": "9",
}

# id -> (julian day, time scale, description)
CASES = {
    "modern_1994": (2449554.857638889, "UT", "1994-07-21 08:35 UT (spec section 9 example instant)"),
    "einstein_1879": (2407422.951435185, "UT", "1879-03-14 10:50:04 UT = 11:30 LMT Ulm (+0:39:56)"),
    "gandhi_1869": (2403972.605972222, "UT", "1869-10-02 02:32:36 UT = 07:11 LMT Porbandar (+4:38:24)"),
    "india_wartime_1943": (2430890.479166667, "UT", "1943-06-14 23:30 UT = 1943-06-15 06:00 IST war time (+6:30)"),
    "sydney_1985": (2446424.791666667, "UT", "1985-12-25 07:00 UT = 18:00 AEDT Sydney"),
    "tromso_1990": (2448063.916666667, "UT", "1990-06-21 10:00 UT = 12:00 CEST Tromso (69.65N)"),
    "ny_fold_2021": (2459525.729166667, "UT", "2021-11-07 05:30 UT = 01:30 EDT (fold=0) New York"),
    "kiritimati_1999": (2451543.9375, "UT", "1999-12-31 10:30 UT = 2000-01-01 00:30 +14 Kiritimati"),
    "eclipse_2025": (2460763.956944444, "UT", "2025-03-29 10:58 UT"),
    "today_2026": (2461314.5, "UT", "2026-10-01 00:00 UT"),
    "edge_1800_tt": (2378511.0, "TT", "1800-01-15 12:00 TT (ephemeris range floor)"),
    "edge_2399_tt": (2597428.0, "TT", "2399-06-01 12:00 TT (ephemeris range ceiling)"),
}


def fetch(body_id: str, jds: list[float], scale: str) -> list[tuple[float, float]]:
    params = {
        "format": "text", "COMMAND": f"'{body_id}'", "OBJ_DATA": "'NO'", "MAKE_EPHEM": "'YES'",
        "EPHEM_TYPE": "'OBSERVER'", "CENTER": "'500@399'", "QUANTITIES": "'31'",
        "TLIST_TYPE": "'JD'", "TIME_TYPE": f"'{scale}'", "CSV_FORMAT": "'YES'",
        "ANG_FORMAT": "'DEG'", "EXTRA_PREC": "'YES'",
        "TLIST": " ".join(f"'{jd:.9f}'" for jd in jds),
    }
    url = "https://ssd.jpl.nasa.gov/api/horizons.api?" + urllib.parse.urlencode(params)
    # curl uses the OS trust store (works behind TLS-inspecting proxies); verification stays on.
    text = subprocess.run(["curl", "-sSf", "--max-time", "60", url], check=True,
                          capture_output=True, text=True).stdout
    if "$$SOE" not in text:
        raise RuntimeError(f"Horizons error for body {body_id}:\n{text[-1500:]}")
    rows = text.split("$$SOE")[1].split("$$EOE")[0].strip().splitlines()
    out = []
    for row in rows:
        cols = [c.strip() for c in row.split(",")]
        out.append((float(cols[3]), float(cols[4])))
    if len(out) != len(jds):
        raise RuntimeError(f"Horizons returned {len(out)} rows for {len(jds)} epochs:\n{text}")
    return out


def main() -> None:
    result: dict = {
        "source": "NASA/JPL Horizons API, DE441, QUANTITIES=31 (apparent geocentric ecliptic-of-date)",
        "source_settings": "CENTER=500@399, EXTRA_PREC=YES, ANG_FORMAT=DEG",
        "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "cases": {},
    }
    for cid, (jd, scale, desc) in CASES.items():
        result["cases"][cid] = {"jd": jd, "time_scale": scale, "description": desc, "longitudes": {}}
    for scale in ("UT", "TT"):
        # Horizons returns rows in chronological order, not request order: sort first.
        ids = sorted((cid for cid, c in CASES.items() if c[1] == scale), key=lambda c: CASES[c][0])
        jds = [CASES[cid][0] for cid in ids]
        for name, hid in BODIES.items():
            for cid, (lon, _lat) in zip(ids, fetch(hid, jds, scale)):
                result["cases"][cid]["longitudes"][name] = lon
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
