"""Client IP behind reverse proxies, FAILING CLOSED.

Two trust models (pick one in production, see docs/deployment.md):
1. ``CLIENT_IP_HEADER`` (e.g. ``cf-connecting-ip``, ``true-client-ip``): an edge you control writes ONE value into that header.
   Only this header is trusted and X-Forwarded-For is ignored. A missing or malformed value is "unknown".
2. ``TRUSTED_PROXY_HOPS=N``: the client is the Nth entry from the RIGHT of X-Forwarded-For (what your own proxy appended).
   A header shorter than N, or an invalid entry, is "unknown" (never the socket peer: that is the proxy).

"unknown" is a single shared bucket with tighter auth limits (see core/deps.py), so a bypass attempt or a proxy
that sends nothing degrades to strict limits instead of silently disabling them. With neither setting (development
only; production refuses to boot) the socket peer is used.

uvicorn runs with --no-proxy-headers: its own handling would trust the forgeable left-most X-Forwarded-For (BUG-007).
"""
from __future__ import annotations

import ipaddress
import logging

from starlette.types import Scope

from app.core.config import settings

log = logging.getLogger("app.clientip")

UNKNOWN_IP = "unknown"
_DEBUG_LOGGED = 0
_DEBUG_MAX = 20
_WATCHED = ("x-real-ip", "true-client-ip", "cf-connecting-ip", "x-forwarded-proto", "forwarded", "x-forwarded-host")


def _valid(ip: str) -> str | None:
    try:
        return str(ipaddress.ip_address(ip.strip()))
    except ValueError:
        return None


def _header_values(scope: Scope, name: bytes) -> list[str]:
    return [v.decode("latin-1") for k, v in scope.get("headers", []) if k == name]


def ip_from_scope(scope: Scope, hops: int | None = None, header: str | None = None) -> str:
    hops = settings.TRUSTED_PROXY_HOPS if hops is None else hops
    header = settings.CLIENT_IP_HEADER if header is None else header
    if header:
        values = _header_values(scope, header.lower().encode())
        if len(values) != 1 or "," in values[0]:
            return UNKNOWN_IP  # absent, repeated or list-valued: not the single trusted value
        return _valid(values[0]) or UNKNOWN_IP
    if hops <= 0:
        client = scope.get("client")
        return client[0] if client else UNKNOWN_IP  # development only
    entries = [e.strip() for v in _header_values(scope, b"x-forwarded-for") for e in v.split(",") if e.strip()]
    if len(entries) < hops:
        return UNKNOWN_IP
    return _valid(entries[-hops]) or UNKNOWN_IP


def _mask(ip: str) -> str:
    """/24 for IPv4, /48 for IPv6: enough to tell ranges apart, not enough to identify a person."""
    try:
        addr = ipaddress.ip_address(ip.strip())
    except ValueError:
        return "invalid"
    prefix = 24 if addr.version == 4 else 48
    return str(ipaddress.ip_network(f"{addr}/{prefix}", strict=False))


def _kind(ip: str) -> str:
    try:
        a = ipaddress.ip_address(ip.strip())
    except ValueError:
        return "invalid"
    if a.is_loopback:
        return "loopback"
    if a.is_private or a.is_link_local or a.is_reserved:
        return "private"
    return "public"


def header_shape(scope: Scope) -> dict:
    """What the proxy chain sent, without addresses: counts, address classes and masked ranges."""
    entries = [e.strip() for v in _header_values(scope, b"x-forwarded-for") for e in v.split(",") if e.strip()]
    client = scope.get("client")
    return {
        "xff_header_count": len(_header_values(scope, b"x-forwarded-for")),
        "xff_entries": len(entries),
        "xff_kinds": [_kind(e) for e in entries],
        "xff_masked": [_mask(e) for e in entries],
        "peer_kind": _kind(client[0]) if client else "none",
        "peer_masked": _mask(client[0]) if client else "none",
        "headers_present": [h for h in _WATCHED if _header_values(scope, h.encode())],
        "configured_hops": settings.TRUSTED_PROXY_HOPS,
        "configured_header": settings.CLIENT_IP_HEADER or None,
        "derived_is_unknown": ip_from_scope(scope) == UNKNOWN_IP,
    }


def maybe_log_shape(scope: Scope) -> None:
    """One INFO line for each of the first 20 requests when LOG_CLIENT_IP_DEBUG=1 (default off)."""
    global _DEBUG_LOGGED
    if settings.LOG_CLIENT_IP_DEBUG and _DEBUG_LOGGED < _DEBUG_MAX:
        _DEBUG_LOGGED += 1
        log.info("client_ip_shape", extra={"n": _DEBUG_LOGGED, **header_shape(scope)})
