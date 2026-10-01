from __future__ import annotations

from app.schemas.common import OutModel


class GeocodingResult(OutModel):
    name: str
    lat: float
    lon: float
    timezone: str | None = None


class GeocodingOut(OutModel):
    results: list[GeocodingResult]
    degraded: bool = False
