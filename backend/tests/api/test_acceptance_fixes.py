from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.db.session import SessionLocal
from app.services import engine
from tests.conftest import CHART, FakeLLM, create_chart, register

A = "/api/v1"
P = f"{A}/horoscopes/personal/today"


@pytest.fixture
def counting_engine(monkeypatch: pytest.MonkeyPatch) -> dict:
    calls = {"n": 0, "birth_times": []}
    real = engine.personal_day

    async def wrapped(chart_data, on, **kw):
        calls["n"] += 1
        calls["birth_times"].append(chart_data["metadata"].get("utc_datetime"))
        return await real(chart_data, on, **kw)

    monkeypatch.setattr(engine, "personal_day", wrapped)
    return calls


# ---------------------------------------------------------------- D1 stale personal reading after a chart edit
async def test_edit_primary_chart_regenerates_personal_reading(client: AsyncClient, fake_llm: FakeLLM, counting_engine: dict) -> None:
    h = await register(client)
    chart = await create_chart(client, h)
    first = (await client.get(P, headers=h)).json()
    assert counting_engine["n"] == 1
    r = await client.put(f"{A}/charts/{chart['id']}", json={**CHART, "time_of_birth": "21:40"}, headers=h)
    assert r.status_code == 200
    async with SessionLocal() as s:  # the row about the OLD chart is gone
        assert await s.scalar(text("SELECT count(*) FROM personal_readings")) == 0
    second = (await client.get(P, headers=h)).json()
    assert counting_engine["n"] == 2 and counting_engine["birth_times"][0] != counting_engine["birth_times"][1]
    assert second["chart_id"] == first["chart_id"]


async def test_stale_row_from_older_engine_or_before_edit_is_not_served(client: AsyncClient, fake_llm: FakeLLM, counting_engine: dict, redis_client) -> None:
    h = await register(client)
    await create_chart(client, h)
    await client.get(P, headers=h)
    async with SessionLocal() as s:  # simulate an engine bump: stored reading carries an older version
        await s.execute(text("UPDATE personal_readings SET reading = jsonb_set(reading, '{engine_version}', '\"0.0.1\"')"))
        await s.commit()
    await redis_client.flushall()
    await client.get(P, headers=h)
    assert counting_engine["n"] == 2
    async with SessionLocal() as s:  # a row older than the chart's last edit is also refused
        await s.execute(text("UPDATE birth_charts SET updated_at = now() + interval '1 minute'"))
        await s.commit()
    await redis_client.flushall()
    await client.get(P, headers=h)
    assert counting_engine["n"] == 3


async def test_delete_chart_removes_its_readings(client: AsyncClient, fake_llm: FakeLLM, counting_engine: dict) -> None:
    h = await register(client)
    chart = await create_chart(client, h)
    await client.get(P, headers=h)
    await client.delete(f"{A}/charts/{chart['id']}", headers=h)
    async with SessionLocal() as s:
        assert await s.scalar(text("SELECT count(*) FROM personal_readings")) == 0


# ---------------------------------------------------------------- D2 never mix systems; 503 + Retry-After
async def test_engine_failure_is_503_with_retry_after_and_no_cross_system_fallback(
    client: AsyncClient, fake_llm: FakeLLM, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.core.errors import UpstreamUnavailable

    async def down(*a, **k):
        raise UpstreamUnavailable("engine down")

    monkeypatch.setattr(engine, "personal_day", down)
    h = await register(client)
    await create_chart(client, h)
    r = await client.get(P, headers=h)
    assert r.status_code == 503 and r.json()["code"] == "PERSONAL_READING_UNAVAILABLE"
    assert r.headers["retry-after"] == "30" and "engine down" not in r.text
    async with SessionLocal() as s:  # nothing generic was stored either
        assert await s.scalar(text("SELECT count(*) FROM personal_readings")) == 0
        assert await s.scalar(text("SELECT count(*) FROM daily_horoscopes")) == 0


async def test_llm_failure_keeps_the_users_own_system(client: AsyncClient, fake_llm: FakeLLM) -> None:
    h = await register(client)
    await create_chart(client, h)
    for system in ("vedic", "western"):
        await client.put(f"{A}/users/me", json={"astrology_system": system}, headers=h)
        d = (await client.get(P, headers=h)).json()
        assert d["system"] == system and d["generated_by"] == "template"  # template in the SAME system


def test_every_503_carries_retry_after() -> None:
    from app.core.errors import AIUnavailable, UpstreamUnavailable

    assert UpstreamUnavailable().headers["Retry-After"] == "10"
    assert AIUnavailable().headers["Retry-After"] == "10"


# ---------------------------------------------------------------- D8 saved people can never be primary
async def test_saved_person_cannot_be_primary(client: AsyncClient) -> None:
    h = await register(client)
    me = await create_chart(client, h, name="Me")
    r = await client.post(f"{A}/charts", json={**CHART, "name": "Friend", "is_primary": True, "relationship": "friend"}, headers=h)
    assert r.status_code == 422 and r.json()["code"] == "PRIMARY_MUST_BE_SELF"
    assert r.json()["detail"] == "Only your own chart can be your primary chart."
    friend = await create_chart(client, h, name="Friend", is_primary=False, relationship="friend")
    assert friend["is_primary"] is False and friend["relationship_label"] == "friend"
    r = await client.post(f"{A}/charts/{friend['id']}/primary", headers=h)
    assert r.status_code == 422 and r.json()["code"] == "PRIMARY_MUST_BE_SELF"
    r = await client.put(f"{A}/charts/{friend['id']}", json={**CHART, "name": "Friend", "is_primary": True}, headers=h)
    assert r.status_code == 422  # the update path cannot sneak it in either
    r = await client.put(f"{A}/charts/{me['id']}", json={**CHART, "relationship": "partner"}, headers=h)
    assert r.status_code == 422  # and the real primary cannot be relabelled to someone else while primary
    primaries = [c for c in (await client.get(f"{A}/charts", headers=h)).json() if c["is_primary"]]
    assert [c["id"] for c in primaries] == [me["id"]]


async def test_first_chart_for_someone_else_is_not_primary_and_new_primary_defaults_to_self(client: AsyncClient) -> None:
    h = await register(client)
    first = await create_chart(client, h, name="Mum", is_primary=False, relationship="family")
    assert first["is_primary"] is False and first["relationship_label"] == "family"
    mine = await create_chart(client, h, name="Me", is_primary=True)
    assert mine["is_primary"] is True and mine["relationship_label"] == "self"


async def test_deleting_primary_never_promotes_a_saved_person(client: AsyncClient, fake_llm: FakeLLM) -> None:
    h = await register(client)
    me = await create_chart(client, h, name="Me")
    await create_chart(client, h, name="Partner", is_primary=False, relationship="partner")
    await client.delete(f"{A}/charts/{me['id']}", headers=h)
    charts = (await client.get(f"{A}/charts", headers=h)).json()
    assert len(charts) == 1 and charts[0]["is_primary"] is False  # no primary rather than a wrong one
    cid = (await client.post(f"{A}/chat/conversations", json={}, headers=h)).json()
    assert cid["chart_id"] is None
    assert (await client.get(P, headers=h)).json()["code"] == "CHART_REQUIRED"


async def test_database_blocks_a_non_self_primary(client: AsyncClient) -> None:
    h = await register(client)
    friend = await create_chart(client, h, is_primary=False, relationship="friend")
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        async with SessionLocal() as s:
            await s.execute(text("UPDATE birth_charts SET is_primary = true WHERE id = :i"), {"i": friend["id"]})
            await s.commit()
