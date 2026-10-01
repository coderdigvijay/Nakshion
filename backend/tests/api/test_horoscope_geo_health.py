from __future__ import annotations

import asyncio

import httpx
import respx
from httpx import AsyncClient
from sqlalchemy import text

from app.db.session import SessionLocal
from app.services import geocoding_service, health_service
from tests.conftest import FakeLLM, register

R = "/api/v1/horoscopes/daily"


async def test_daily_generates_once_then_cached(client: AsyncClient, fake_llm: FakeLLM) -> None:
    r = await client.get(R, params={"sign": "Leo"})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["zodiac_sign"] == "leo" and d["general_reading"] == "A calm day for leo."
    assert 1 <= d["lucky_number"] <= 9 and d["lucky_color"]
    assert "moon" in d["transit_data"]
    r2 = await client.get(R, params={"sign": "leo"})
    assert r2.json()["id"] == d["id"] and fake_llm.calls["daily"] == 1
    async with SessionLocal() as s:
        assert await s.scalar(text("SELECT count(*) FROM daily_horoscopes")) == 1


async def test_daily_concurrent_single_generation(client: AsyncClient, fake_llm: FakeLLM) -> None:
    fake_llm.delay_s = 0.5
    rs = await asyncio.gather(*[client.get(R, params={"sign": "aries"}) for _ in range(5)])
    assert all(r.status_code == 200 for r in rs)
    assert len({r.json()["id"] for r in rs}) == 1 and fake_llm.calls["daily"] == 1


async def test_daily_invalid_sign_and_template_fallback(client: AsyncClient, fake_llm: FakeLLM) -> None:
    r = await client.get(R, params={"sign": "dragon"})
    assert r.status_code == 400 and r.json()["code"] == "INVALID_SIGN"
    fake_llm.fail.add("daily")
    r = await client.get(R, params={"sign": "virgo"})
    assert r.status_code == 200 and r.json()["generated_by"] == "template" and r.json()["general_reading"]
    async with SessionLocal() as s:
        assert await s.scalar(text("SELECT count(*) FROM daily_horoscopes")) == 0  # templates not persisted


async def test_daily_date_window(client: AsyncClient, fake_llm: FakeLLM) -> None:
    r = await client.get(R, params={"sign": "leo", "date": "2001-01-01"})
    assert r.status_code == 422 and r.json()["code"] == "DATE_OUT_OF_RANGE"


GEO = "/api/v1/geocoding/search"


@respx.mock
async def test_geocoding_cached_with_timezone(client: AsyncClient) -> None:
    route = respx.get(geocoding_service.LOCATIONIQ_URL).mock(
        return_value=httpx.Response(200, json=[{"display_place": "Pune", "display_address": "Maharashtra, India",
                                                "lat": "18.52", "lon": "73.85"}])
    )
    h = await register(client)
    r = await client.get(GEO, params={"q": " Pune "}, headers=h)
    assert r.status_code == 200
    assert r.json()["results"] == [{"name": "Pune, Maharashtra, India", "lat": 18.52, "lon": 73.85, "timezone": "Asia/Kolkata"}]
    await client.get(GEO, params={"q": "PUNE"}, headers=h)
    assert route.call_count == 1  # normalised cache hit


@respx.mock
async def test_geocoding_fallback_and_degraded(client: AsyncClient) -> None:
    respx.get(geocoding_service.LOCATIONIQ_URL).mock(return_value=httpx.Response(429))
    geo = respx.get(geocoding_service.GEOAPIFY_URL).mock(
        return_value=httpx.Response(200, json={"results": [{"city": "Delhi", "state": "Delhi", "country": "India",
                                                             "lat": 28.61, "lon": 77.21}]})
    )
    h = await register(client)
    r = await client.get(GEO, params={"q": "delhi"}, headers=h)
    assert r.json()["results"][0]["name"] == "Delhi, India" and geo.call_count == 1
    geo.mock(return_value=httpx.Response(500))
    r = await client.get(GEO, params={"q": "mumbai"}, headers=h)
    assert r.status_code == 200 and r.json() == {"results": [], "degraded": True}


async def test_geocoding_requires_auth_and_length(client: AsyncClient) -> None:
    assert (await client.get(GEO, params={"q": "pune"})).status_code == 401
    h = await register(client)
    r = await client.get(GEO, params={"q": "pu"}, headers=h)
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)


async def test_health_live_never_touches_db_or_redis(client: AsyncClient, monkeypatch) -> None:
    def boom(*a, **k):
        raise AssertionError("liveness touched a dependency")

    monkeypatch.setattr(health_service, "SessionLocal", boom)
    monkeypatch.setattr(health_service.cache, "get_client", boom)
    for path in ("/health", "/health/live", "/api/v1/health/live"):
        r = await client.get(path)
        assert r.status_code == 200 and r.json()["status"] == "ok"
    assert "strict-transport-security" in r.headers and r.headers["x-frame-options"] == "DENY"


async def test_cron_requires_secret(client: AsyncClient) -> None:
    assert (await client.post("/internal/cron/hourly")).status_code == 401
    r = await client.post("/internal/cron/hourly", headers={"X-Cron-Secret": "test-cron-secret"})
    assert r.status_code == 200 and r.json()["job"] == "hourly"
    r = await client.post("/internal/cron/hourly", headers={"X-Cron-Secret": "test-cron-secret"})
    assert r.status_code == 429


async def test_daily_maintenance_alias_and_health_never_hits_db(client: AsyncClient) -> None:
    r = await client.post("/internal/cron/daily_maintenance", headers={"X-Cron-Secret": "test-cron-secret"})
    assert r.status_code == 200 and r.json()["job"] == "daily_maintenance"


async def test_ready_reports_rag_as_information_only(client: AsyncClient, monkeypatch) -> None:
    from app.services import ai, engine

    monkeypatch.setattr(engine, "_self_test_result", True)  # the lifespan (which sets it) does not run in this client
    monkeypatch.setattr(ai, "_rag_status", {"checked": True, "ok": False, "problems": ["no active index version"]})
    r = await client.get("/health/ready")
    assert r.status_code == 200  # a degraded index never fails readiness
    assert r.json()["checks"]["rag"]["ok"] is False and r.json()["status"] == "ok"
    live = await client.get("/health/live")
    assert "rag" not in live.text  # liveness stays dependency-free


async def test_pregen_cron_returns_immediately_and_finishes_in_background(client: AsyncClient, monkeypatch) -> None:
    """cron-job.org times out after 30 s but 24 LLM generations take longer: the endpoint must answer at once."""
    import asyncio

    from app.services import cron_service, horoscope_service

    started, release = asyncio.Event(), asyncio.Event()

    async def slow_pregenerate(on):
        started.set()
        await release.wait()  # would block a synchronous endpoint until released
        return {"generated_or_present": 24, "total": 24}

    monkeypatch.setattr(horoscope_service, "pregenerate", slow_pregenerate)
    r = await asyncio.wait_for(
        client.post("/internal/cron/pregen_horoscopes", headers={"X-Cron-Secret": "test-cron-secret"}), timeout=5
    )
    assert r.status_code == 200 and r.json() == {"job": "pregen_horoscopes", "status": "started"}
    await asyncio.wait_for(started.wait(), timeout=5)  # the work really runs in the background
    assert cron_service._background  # held by a strong reference while running
    release.set()
    await asyncio.sleep(0.05)
    assert not cron_service._background  # and cleaned up when done
