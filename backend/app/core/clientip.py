"""Client IP behind trusted reverse proxies (Render).

uvicorn's own --proxy-headers takes the LEFT-most X-Forwarded-For entry when every peer is trusted,
which a client can forge. We therefore run uvicorn with --no-proxy-headers and derive the IP here:
with TRUSTED_PROXY_HOPS=N, the client is the Nth entry from the right (appended by our own proxy).
"""
from __future__ import annotations

import ipaddress
from collections.abc import Iterable

from starlette.types import Scope

from app.core.config import settings


def _valid(ip: str) -> str | None:
    try:
        return str(ipaddress.ip_address(ip.strip()))
    except ValueError:
        return None


def ip_from_scope(scope: Scope, hops: int | None = None) -> str:
    hops = settings.TRUSTED_PROXY_HOPS if hops is None else hops
    client = scope.get("client")
    peer = client[0] if client else "unknown"
    if hops <= 0:
        return peer
    values: list[str] = []
    for k, v in scope.get("headers", []):
        if k == b"x-forwarded-for":
            values.extend(part for part in v.decode("latin-1").split(","))
    entries: Iterable[str] = [e for e in (x.strip() for x in values) if e]
    entries = list(entries)
    if len(entries) < hops:
        return peer  # header missing or shorter than the proxy chain: don't trust it
    return _valid(entries[-hops]) or peer
