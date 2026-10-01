from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal
from app.services import cache
from tests.conftest import CHART, create_chart, register

C = "/api/v1/charts"


async def test_create_resolves_timezone_server_side(client: AsyncClient) -> None:
    h = await register(client)
    chart = await create_chart(client, h, timezone="America/New_York", is_primary=False)
    assert chart["timezone"] == "Asia/Kolkata"  # client hint ignored (G-05)
    assert chart["is_primary"] is True  # first chart is always primary
    assert chart["relationship_label"] == "self"
    assert chart["time_of_birth"] == "14:05"
    assert isinstance(chart["latitude"], float)
    cd = chart["chart_data"]
    assert {"sun_sign", "moon_sign", "rising_sign", "planets", "houses", "aspects", "vedic"} <= set(cd)
    assert cd["metadata"]["timezone"] == "Asia/Kolkata"


async def test_both_slash_spellings_no_redirect(client: AsyncClient) -> None:
    h = await register(client)
    await create_chart(client, h)
    a = await client.get(f"{C}/", headers=h)
    b = await client.get(C, headers=h)
    assert a.status_code == b.status_code == 200 and len(a.json()) == 1


async def test_list_order_primary_first(client: AsyncClient) -> None:
    h = await register(client)
    first = await create_chart(client, h, name="Me")
    second = await create_chart(client, h, name="Partner", is_primary=False)
    third = await create_chart(client, h, name="New primary", is_primary=True)
    names = [c["name"] for c in (await client.get(C, headers=h)).json()]
    assert names == ["New primary", "Me", "Partner"]
    primaries = [c for c in (await client.get(C, headers=h)).json() if c["is_primary"]]
    assert len(primaries) == 1 and primaries[0]["id"] == third["id"]
    assert first["id"] != second["id"]


async def test_unknown_time_and_validation_codes(client: AsyncClient) -> None:
    h = await register(client)
    c = await create_chart(client, h, time_of_birth=None, has_exact_time=True)
    assert c["has_exact_time"] is False and c["time_of_birth"] is None
    assert c["chart_data"]["metadata"]["approximate_time"] is True
    r = await client.post(C, json={**CHART, "date_of_birth": "2021-03-14", "time_of_birth": "02:30",
                                   "latitude": 40.71, "longitude": -74.0}, headers=h)
    assert r.status_code == 422 and r.json()["code"] == "BIRTH_TIME_NONEXISTENT"
    assert "America/New_York" in r.json()["detail"]
    r = await client.post(C, json={**CHART, "date_of_birth": "2999-01-01"}, headers=h)
    assert r.status_code == 422 and r.json()["code"] == "DATE_OUT_OF_RANGE"
    r = await client.post(C, json={**CHART, "date_of_birth": "1700-01-01"}, headers=h)
    assert r.status_code == 422 and r.json()["code"] == "DATE_OUT_OF_RANGE"
    r = await client.post(C, json={**CHART, "latitude": 0, "longitude": 0}, headers=h)
    assert r.status_code == 422 and r.json()["code"] == "INVALID_LOCATION"
    r = await client.post(C, json={**CHART, "latitude": 91}, headers=h)
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)
    r = await client.post(C, json={**CHART, "chart_data": {}}, headers=h)
    assert r.status_code == 422  # not client-writable


async def test_idor_returns_404(client: AsyncClient) -> None:
    h1 = await register(client)
    chart = await create_chart(client, h1)
    h2 = await register(client, email="eve@example.com")
    for method, url in (("GET", f"{C}/{chart['id']}"), ("DELETE", f"{C}/{chart['id']}"),
                        ("POST", f"{C}/{chart['id']}/primary")):
        r = await client.request(method, url, headers=h2)
        assert r.status_code == 404, (method, url)
    r = await client.put(f"{C}/{chart['id']}", json=CHART, headers=h2)
    assert r.status_code == 404
    assert (await client.get(f"{C}/{chart['id']}")).status_code == 401


async def test_concurrent_primary_creates_keep_one_primary(client: AsyncClient) -> None:
    h = await register(client)
    await create_chart(client, h, name="base")
    rs = await asyncio.gather(*[client.post(C, json={**CHART, "name": f"p{i}"}, headers=h) for i in range(4)])
    assert all(r.status_code in (201, 409) for r in rs), [r.text for r in rs]
    async with SessionLocal() as s:
        n = await s.scalar(text("SELECT count(*) FROM birth_charts WHERE is_primary"))
    assert n == 1


async def test_chart_limit(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "CHART_LIMIT_FREE", 2)
    h = await register(client)
    await create_chart(client, h, name="a")
    await create_chart(client, h, name="b")
    r = await client.post(C, json={**CHART, "name": "c"}, headers=h)
    assert r.status_code == 403 and r.json()["code"] == "CHART_LIMIT_REACHED"


async def test_concurrent_creates_respect_limit(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "CHART_LIMIT_FREE", 3)
    h = await register(client)
    rs = await asyncio.gather(*[client.post(C, json={**CHART, "name": f"c{i}", "is_primary": False}, headers=h) for i in range(6)])
    assert sum(r.status_code == 201 for r in rs) == 3
    assert {r.status_code for r in rs} <= {201, 403}


async def test_update_recomputes_and_invalidates(client: AsyncClient, redis_client) -> None:
    h = await register(client)
    chart = await create_chart(client, h)
    await redis_client.set(f"chart_summary:{chart['id']}", "x")
    await redis_client.set(f"factors:{chart['id']}:1.0.0", "x")
    me = (await client.get("/api/v1/users/me", headers=h)).json()
    await redis_client.set(f"daily_personal:{me['id']}:2026-10-01", "x")
    r = await client.put(f"{C}/{chart['id']}", json={**CHART, "time_of_birth": "20:05:00"}, headers=h)
    assert r.status_code == 200 and r.json()["time_of_birth"] == "20:05"
    assert r.json()["chart_data"]["rising_sign"] != chart["chart_data"]["rising_sign"]
    assert await redis_client.exists(f"chart_summary:{chart['id']}", f"factors:{chart['id']}:1.0.0",
                                     f"daily_personal:{me['id']}:2026-10-01") == 0


async def test_delete_primary_promotes_and_keeps_conversations(client: AsyncClient) -> None:
    h = await register(client)
    first = await create_chart(client, h, name="Me")
    other = await create_chart(client, h, name="Me too", is_primary=False, relationship="self")
    conv = (await client.post("/api/v1/chat/conversations", json={}, headers=h)).json()
    assert conv["chart_id"] == first["id"]
    assert (await client.delete(f"{C}/{first['id']}", headers=h)).status_code == 204
    charts = (await client.get(C, headers=h)).json()
    assert [c["id"] for c in charts if c["is_primary"]] == [other["id"]]
    detail = (await client.get(f"/api/v1/chat/conversations/{conv['id']}", headers=h)).json()
    assert detail["conversation"]["chart_id"] is None  # ON DELETE SET NULL


async def test_set_primary(client: AsyncClient) -> None:
    h = await register(client)
    await create_chart(client, h, name="Me")
    other = await create_chart(client, h, name="Me too", is_primary=False, relationship="self")
    r = await client.post(f"{C}/{other['id']}/primary", headers=h)
    assert r.status_code == 200 and r.json()["is_primary"] is True
    assert (await client.get(C, headers=h)).json()[0]["id"] == other["id"]


async def test_cache_down_does_not_fail_writes(client: AsyncClient) -> None:
    class Broken:
        def __getattr__(self, name):
            raise ConnectionError("redis down")

    h = await register(client)
    chart = await create_chart(client, h)
    cache.set_client(Broken())  # type: ignore[arg-type]
    r = await client.put(f"{C}/{chart['id']}", json={**CHART, "name": "Renamed"}, headers=h)
    assert r.status_code == 200 and r.json()["name"] == "Renamed"
