from __future__ import annotations

from app.core.clientip import UNKNOWN_IP, header_shape, ip_from_scope


def _scope(peer: str, xff: list[str] | None = None, **headers: str) -> dict:
    h = [(b"x-forwarded-for", v.encode()) for v in (xff or [])]
    h += [(k.replace("_", "-").encode(), v.encode()) for k, v in headers.items()]
    return {"client": (peer, 1234), "headers": h}


def test_no_trusted_proxy_uses_socket_peer_in_development() -> None:
    assert ip_from_scope(_scope("10.0.0.5", ["1.2.3.4"]), hops=0, header="") == "10.0.0.5"


def test_one_hop_takes_rightmost_not_spoofed_left() -> None:
    assert ip_from_scope(_scope("10.0.0.5", ["6.6.6.6, 203.0.113.9"]), hops=1, header="") == "203.0.113.9"


def test_two_hops_and_split_headers() -> None:
    assert ip_from_scope(_scope("10.0.0.5", ["6.6.6.6", "203.0.113.9, 172.16.0.1"]), hops=2, header="") == "203.0.113.9"


def test_fail_closed_never_falls_back_to_the_proxy_peer() -> None:
    assert ip_from_scope(_scope("10.0.0.5"), hops=1, header="") == UNKNOWN_IP
    assert ip_from_scope(_scope("10.0.0.5", ["1.1.1.1"]), hops=2, header="") == UNKNOWN_IP
    assert ip_from_scope(_scope("10.0.0.5", ["not-an-ip"]), hops=1, header="") == UNKNOWN_IP


def test_configured_header_is_the_only_trusted_source() -> None:
    s = _scope("10.0.0.5", ["6.6.6.6"], cf_connecting_ip="198.51.100.7")
    assert ip_from_scope(s, hops=1, header="cf-connecting-ip") == "198.51.100.7"  # XFF ignored
    assert ip_from_scope(_scope("10.0.0.5", ["6.6.6.6"]), hops=1, header="cf-connecting-ip") == UNKNOWN_IP  # missing
    assert ip_from_scope(_scope("10.0.0.5", cf_connecting_ip="1.1.1.1, 2.2.2.2"), header="cf-connecting-ip") == UNKNOWN_IP
    assert ip_from_scope(_scope("10.0.0.5", cf_connecting_ip="garbage"), header="cf-connecting-ip") == UNKNOWN_IP
    dup = {"client": ("10.0.0.5", 1), "headers": [(b"cf-connecting-ip", b"1.1.1.1"), (b"cf-connecting-ip", b"2.2.2.2")]}
    assert ip_from_scope(dup, header="cf-connecting-ip") == UNKNOWN_IP  # repeated header: attacker-influenced


def test_diagnostic_shape_masks_addresses_and_lists_headers() -> None:
    shape = header_shape(_scope("10.1.2.3", ["93.184.216.34, 10.9.9.9"], x_real_ip="1.1.1.1", x_forwarded_proto="https"))
    assert shape["xff_entries"] == 2 and shape["xff_kinds"] == ["public", "private"]
    assert shape["xff_masked"] == ["93.184.216.0/24", "10.9.9.0/24"] and shape["peer_masked"] == "10.1.2.0/24"
    assert set(shape["headers_present"]) == {"x-real-ip", "x-forwarded-proto"}
    assert "93.184.216.34" not in str(shape) and "10.9.9.9" not in str(shape)  # full addresses never leave
