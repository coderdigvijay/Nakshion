"""Place autocomplete: LocationIQ primary, Geoapify fallback, Redis-cached 30 days (api-contract G1).

- Query normalised (NFKC, lower, collapsed whitespace) and hashed for the key: geo:q:{sha1}.
- Global token bucket of 2 req/s toward LocationIQ (free-tier limit); wait up to 1 s, then fall back.
- Every result's timezone comes from the same server-side resolver charts use.
- Both providers failing -> 200 {results: [], degraded: true}; degraded results are not cached.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import time
import unicodedata
from typing import Any

import httpx

from app.core.config import settings
from app.schemas.geocoding import GeocodingOut, GeocodingResult
from app.services import cache, engine

log = logging.getLogger("app.geocoding")

LOCATIONIQ_URL = "https://api.locationiq.com/v1/autocomplete"
GEOAPIFY_URL = "https://api.geoapify.com/v1/geocode/autocomplete"
TTL_S = 30 * 86400
EMPTY_TTL_S = 86400
TIMEOUT_S = 3.0


class _TokenBucket:
    def __init__(self, rate: float, capacity: float) -> None:
        self.rate, self.capacity = rate, capacity
        self.tokens, self.updated = capacity, time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, max_wait: float) -> bool:
        deadline = time.monotonic() + max_wait
        while True:
            async with self._lock:
                now = time.monotonic()
                self.tokens = min(self.capacity, self.tokens + (now - self.updated) * self.rate)
                self.updated = now
                if self.tokens >= 1:
                    self.tokens -= 1
                    return True
                wait = (1 - self.tokens) / self.rate
            if time.monotonic() + wait > deadline:
                return False
            await asyncio.sleep(wait)


locationiq_bucket = _TokenBucket(rate=2.0, capacity=2.0)


class ProviderError(Exception):
    pass


def normalise(q: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", q).lower().split())


def _key(nq: str) -> str:
    return f"geo:q:{hashlib.sha1(nq.encode()).hexdigest()}"  # noqa: S324 - cache key only


async def _locationiq(client: httpx.AsyncClient, q: str) -> list[tuple[str, float, float]]:
    if not settings.LOCATIONIQ_API_KEY:
        raise ProviderError("no key")
    if not await locationiq_bucket.acquire(max_wait=1.0):
        raise ProviderError("bucket empty")
    resp = await client.get(
        LOCATIONIQ_URL,
        params={
            "key": settings.LOCATIONIQ_API_KEY,
            "q": q,
            "limit": 5,
            "tag": "place:city,place:town,place:village,place:hamlet",
            "dedupe": 1,
            "normalizecity": 1,
        },
    )
    if resp.status_code == 404:  # LocationIQ returns 404 for "no results"
        return []
    if resp.status_code != 200:
        raise ProviderError(f"status {resp.status_code}")
    out = []
    for item in resp.json() or []:
        place = (item.get("display_place") or "").strip()
        addr = (item.get("display_address") or "").strip()
        name = ", ".join(p for p in (place, addr) if p) or item.get("display_name", "")
        out.append((name, float(item["lat"]), float(item["lon"])))
    return out


async def _geoapify(client: httpx.AsyncClient, q: str) -> list[tuple[str, float, float]]:
    if not settings.GEOAPIFY_API_KEY or settings.GEOCODER_FALLBACK != "geoapify":
        raise ProviderError("fallback disabled")
    resp = await client.get(
        GEOAPIFY_URL,
        params={"text": q, "type": "city", "limit": 5, "format": "json", "apiKey": settings.GEOAPIFY_API_KEY},
    )
    if resp.status_code != 200:
        raise ProviderError(f"status {resp.status_code}")
    out = []
    for item in (resp.json() or {}).get("results", []):
        parts = [item.get("city") or item.get("name"), item.get("state"), item.get("country")]
        name = ", ".join(dict.fromkeys(p for p in parts if p)) or item.get("formatted", "")
        out.append((name, float(item["lat"]), float(item["lon"])))
    return out


async def _with_timezones(rows: list[tuple[str, float, float]]) -> list[dict[str, Any]]:
    results = []
    for name, lat, lon in rows[:5]:
        tz = await engine.resolve_timezone(lat, lon)
        results.append({"name": name, "lat": lat, "lon": lon, "timezone": tz})
    return results


async def search(q: str) -> GeocodingOut:
    nq = normalise(q)
    key = _key(nq)
    cached = await cache.get_json(key)
    if isinstance(cached, list):
        return GeocodingOut(results=[GeocodingResult(**r) for r in cached])

    rows: list[tuple[str, float, float]] | None = None
    async with httpx.AsyncClient(timeout=TIMEOUT_S) as client:
        for provider in (_locationiq, _geoapify):
            try:
                rows = await provider(client, nq)
                break
            except (ProviderError, httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
                log.warning("geocoder_failed", extra={"provider": provider.__name__.strip("_"), "err": type(exc).__name__})
    if rows is None:
        log.error("geocoding_degraded")
        return GeocodingOut(results=[], degraded=True)
    results = await _with_timezones(rows)
    await cache.set_json(key, results, TTL_S if results else EMPTY_TTL_S)
    return GeocodingOut(results=[GeocodingResult(**r) for r in results])
