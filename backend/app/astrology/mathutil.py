"""Angle helpers. One place for sign/degree normalisation (accuracy rules section 7)."""

from __future__ import annotations

import math


def norm360(x: float) -> float:
    r = math.fmod(x, 360.0)
    if r < 0:
        r += 360.0
    return 0.0 if r >= 360.0 else r


def sign_of(lon: float) -> tuple[int, float]:
    lon = norm360(lon)
    idx = int(lon // 30.0) % 12
    return idx, lon - idx * 30.0


def separation(a: float, b: float) -> float:
    """Shortest angular distance on the circle, 0..180."""
    d = abs(norm360(a) - norm360(b))
    return 360.0 - d if d > 180.0 else d


def signed_diff(a: float, b: float) -> float:
    """a - b wrapped into (-180, 180]."""
    d = norm360(a - b)
    return d - 360.0 if d > 180.0 else d


def deg2(x: float) -> float:
    """Round a within-sign degree to 2 dp without ever showing 30.00 (would read as next sign)."""
    r = round(x, 2)
    return 29.99 if r >= 30.0 else r


def lon2(x: float) -> float:
    r = round(norm360(x), 2)
    return 0.0 if r >= 360.0 else r
