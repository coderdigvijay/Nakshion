from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import FakeLLM, create_chart, register

C = "/api/v1/charts"


async def test_transits_dasha_and_idor(client: AsyncClient) -> None:
    h = await register(client)
    chart = await create_chart(client, h)
    r = await client.get(f"{C}/{chart['id']}/transits", params={"from": "2026-10-01", "days": 30}, headers=h)
    assert r.status_code == 200, r.text
    t = r.json()
    assert t["days"] == 30 and t["from"] == "2026-10-01" and isinstance(t["western"], list) and "gochara" in t["vedic"]
    assert (await client.get(f"{C}/{chart['id']}/transits", params={"days": 91}, headers=h)).status_code == 422
    d = (await client.get(f"{C}/{chart['id']}/dasha", headers=h)).json()
    assert len(d["timeline"]) == 9 and d["timeline"][0]["antar"] and d["current"]["maha_dasha"]["current"]
    assert (await client.get(f"{C}/{chart['id']}/dasha", params={"levels": 3}, headers=h)).status_code == 422
    h2 = await register(client, email="eve@example.com")
    for sub in ("transits", "dasha"):
        assert (await client.get(f"{C}/{chart['id']}/{sub}", headers=h2)).status_code == 404
        assert (await client.get(f"{C}/{chart['id']}/{sub}")).status_code == 401


async def test_transits_cache_invalidated_on_chart_update(client: AsyncClient, redis_client) -> None:
    h = await register(client)
    chart = await create_chart(client, h)
    await client.get(f"{C}/{chart['id']}/transits", params={"from": "2026-10-01", "days": 5}, headers=h)
    assert await redis_client.exists(f"transits:{chart['id']}:2026-10-01:5") == 1
    from tests.conftest import CHART

    await client.put(f"{C}/{chart['id']}", json={**CHART, "time_of_birth": "20:05"}, headers=h)
    assert await redis_client.exists(f"transits:{chart['id']}:2026-10-01:5") == 0


async def test_panchang_public_cached_and_validated(client: AsyncClient, redis_client) -> None:
    r = await client.get("/api/v1/panchang", params={"date": "2026-10-01", "lat": 18.5204, "lon": 73.8567})
    assert r.status_code == 200, r.text
    p = r.json()
    assert p["timezone"] == "Asia/Kolkata" and p["tithi"] and p["nakshatra"] and p["rahu_kaal"]
    assert await redis_client.exists("panchang:2026-10-01:18.5:73.9") == 1
    assert (await client.get("/api/v1/panchang", params={"date": "1800-01-01", "lat": 18, "lon": 73})).status_code == 422
    assert (await client.get("/api/v1/panchang", params={"date": "2026-10-01", "lat": 99, "lon": 73})).status_code == 422
    assert (await client.get("/api/v1/panchang", params={"date": "2026-10-01", "lat": 0, "lon": 0})).status_code == 422


async def test_personal_reading_real_engine(client: AsyncClient, fake_llm: FakeLLM) -> None:
    h = await register(client)
    await create_chart(client, h)
    r = await client.get("/api/v1/horoscopes/personal/today", headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert set(d["areas"]) == {"love", "career", "wellness", "money"}
    assert all(1 <= a["score"] <= 5 and a["text"] for a in d["areas"].values())
    assert d["key_factors"] and d["lucky"]["number"] and "rahu_kaal" in d["timing"]
    assert d["generated_by"] == "template"  # fake LLM module has no personal generator
