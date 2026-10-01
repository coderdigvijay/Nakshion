from __future__ import annotations

from app.core.clientip import ip_from_scope


def _scope(peer: str, xff: list[str] | None = None) -> dict:
    headers = [(b"x-forwarded-for", v.encode()) for v in (xff or [])]
    return {"client": (peer, 1234), "headers": headers}


def test_no_trusted_proxy_ignores_header() -> None:
    assert ip_from_scope(_scope("10.0.0.5", ["1.2.3.4"]), hops=0) == "10.0.0.5"


def test_one_hop_takes_rightmost_not_spoofed_left() -> None:
    # client forged "6.6.6.6"; Render appended the real peer 203.0.113.9
    assert ip_from_scope(_scope("10.0.0.5", ["6.6.6.6, 203.0.113.9"]), hops=1) == "203.0.113.9"


def test_two_hops_and_split_headers() -> None:
    assert ip_from_scope(_scope("10.0.0.5", ["6.6.6.6", "203.0.113.9, 172.16.0.1"]), hops=2) == "203.0.113.9"


def test_missing_short_or_garbage_header_falls_back_to_peer() -> None:
    assert ip_from_scope(_scope("10.0.0.5"), hops=1) == "10.0.0.5"
    assert ip_from_scope(_scope("10.0.0.5", ["1.1.1.1"]), hops=2) == "10.0.0.5"
    assert ip_from_scope(_scope("10.0.0.5", ["not-an-ip"]), hops=1) == "10.0.0.5"
