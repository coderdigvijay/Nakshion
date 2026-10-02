from __future__ import annotations

import asyncio

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.db.session import SessionLocal
from app.services import ai, personal_reading_service as prs
from tests.conftest import CHART, FakeLLM, create_chart, register

A = "/api/v1"
P = f"{A}/horoscopes/personal/today"

NARRATIVE = {
    "headline": "A steady day", "overview": "A fuller reading written by the model.",
    "areas": {k: {"text": f"{k} text"} for k in ("love", "career", "wellness", "money")},
    "affirmation": "I am steady.", "generated_by": "llm",
}


class GatedLLM:
    """Fake model that blocks on an Event: "slow" is by construction (the gate stays closed), never by wall-clock."""

    def __init__(self, open_gate: bool, fail: bool = False) -> None:
        self.gate = asyncio.Event()
        self.started = asyncio.Event()
        self.calls, self.kwargs, self.fail = 0, [], fail
        if open_gate:
            self.gate.set()

    async def generate_daily_personal(self, facts, **kw):
        self.calls += 1
        self.kwargs.append(kw)
        self.started.set()
        await self.gate.wait()
        if self.fail:
            raise RuntimeError("model down")
        return dict(NARRATIVE)


@pytest.fixture
def slow(fake_llm: FakeLLM, monkeypatch: pytest.MonkeyPatch):
    """install(blocked=True) -> the model never answers until llm.gate.set(); the request waits only 50 ms.
    install(blocked=False) -> the model answers immediately and the request waits up to 60 s for it."""

    def install(blocked: bool = True, fail: bool = False) -> GatedLLM:
        llm = GatedLLM(open_gate=not blocked, fail=fail)
        mod = fake_llm.module()
        mod.generate_daily_personal = llm.generate_daily_personal
        mod.DAILY_BUDGET_S = 12.0
        monkeypatch.setattr(ai, "_module", lambda: mod)
        monkeypatch.setattr(prs, "FOREGROUND_WAIT_S", 0.05 if blocked else 60.0)
        return llm

    return install


async def _setup(client: AsyncClient) -> tuple[dict, dict]:
    h = await register(client)
    return h, await create_chart(client, h)


async def test_slow_llm_serves_template_now_then_upgrades_in_background(client: AsyncClient, slow) -> None:
    llm = slow(blocked=True)
    h, chart = await _setup(client)
    first = (await client.get(P, headers=h)).json()
    assert first["generated_by"] == "template" and first["overview"]  # immediate, complete reading
    await asyncio.wait_for(llm.started.wait(), 10)
    assert llm.kwargs[0]["budget_s"] == 12.0  # the adapter passes the AI layer's budget through
    llm.gate.set()  # the model finishes now
    await prs.drain()
    second = (await client.get(P, headers=h)).json()
    assert second["generated_by"] == "llm" and second["overview"] == NARRATIVE["overview"]
    assert second["chart_id"] == chart["id"] and second["engine_version"] == first["engine_version"]
    async with SessionLocal() as s:
        row = (await s.execute(text("SELECT generated_by, count(*) OVER () FROM personal_readings"))).one()
    assert row == ("llm", 1)  # the row was overwritten, not duplicated
    assert llm.calls == 1


async def test_fast_llm_is_served_directly(client: AsyncClient, slow) -> None:
    slow(blocked=False)
    h, _ = await _setup(client)
    assert (await client.get(P, headers=h)).json()["generated_by"] == "llm"


async def test_repeated_page_loads_share_one_llm_call(client: AsyncClient, slow) -> None:
    llm = slow(blocked=True)
    h, _ = await _setup(client)
    rs = await asyncio.gather(*[client.get(P, headers=h) for _ in range(6)])
    assert all(r.status_code == 200 and r.json()["generated_by"] == "template" for r in rs)
    llm.gate.set()
    await prs.drain()
    assert llm.calls == 1  # single-flight per user+date+system+chart (the gate kept the first job in flight)


async def test_chart_edit_during_generation_discards_the_stale_upgrade(client: AsyncClient, slow) -> None:
    llm = slow(blocked=True)
    h, chart = await _setup(client)
    await client.get(P, headers=h)  # template served; the upgrade is blocked on the gate, bound to the OLD chart
    await asyncio.wait_for(llm.started.wait(), 10)
    r = await client.put(f"{A}/charts/{chart['id']}", json={**CHART, "time_of_birth": "21:40"}, headers=h)
    assert r.status_code == 200
    llm.gate.set()  # now the stale generation completes
    await prs.drain()
    async with SessionLocal() as s:
        assert await s.scalar(text("SELECT count(*) FROM personal_readings WHERE generated_by = 'llm'")) == 0
    fresh = (await client.get(P, headers=h)).json()
    assert fresh["chart_id"] == chart["id"]
    await prs.drain()
    assert llm.calls == 2  # a new generation for the edited chart


async def test_failed_llm_is_not_retried_on_every_page_load_but_after_five_minutes(client: AsyncClient, slow) -> None:
    llm = slow(blocked=False, fail=True)
    h, _ = await _setup(client)
    assert (await client.get(P, headers=h)).json()["generated_by"] == "template"  # the job ran, failed, template served
    await prs.drain()
    for _ in range(3):
        assert (await client.get(P, headers=h)).json()["generated_by"] == "template"
    assert llm.calls == 1  # the 5-minute template is trusted
    async with SessionLocal() as s:  # age the template row and forget the cache: time to retry
        await s.execute(text("UPDATE personal_readings SET created_at = now() - interval '10 minutes'"))
        await s.commit()
    from app.services import cache

    await cache.get_client().flushall()
    llm.fail = False
    assert (await client.get(P, headers=h)).json()["generated_by"] == "llm"  # request waits up to 60 s: deterministic
    assert llm.calls == 2


async def test_a_template_never_overwrites_an_llm_row(client: AsyncClient, slow) -> None:
    import uuid
    from datetime import date

    slow(blocked=False)
    h, chart = await _setup(client)
    assert (await client.get(P, headers=h)).json()["generated_by"] == "llm"
    async with SessionLocal() as s:
        uid = await s.scalar(text("SELECT user_id FROM personal_readings"))
        ts = await s.scalar(text("SELECT updated_at FROM birth_charts"))
    job = prs._Job(key="k", flight="f", user_id=uid, uid_hash="x", on=date.today(), system="vedic",
                   chart_id=uuid.UUID(chart["id"]), chart_updated_at=ts, facts={}, language="english", ttl_s=60)
    assert await prs._store(job, {"overview": "template text"}, "template") is False  # refused: an LLM row exists
    assert await prs._store(job, {"overview": "newer llm text"}, "llm") is True       # an LLM reading may replace it
    stale = prs._Job(**{**job.__dict__, "chart_updated_at": ts.replace(year=2001)})
    assert await prs._store(stale, {"overview": "from before an edit"}, "llm") is False  # chart changed since: discarded
    async with SessionLocal() as s:
        row = (await s.execute(text("SELECT generated_by, reading->>'overview' FROM personal_readings"))).one()
    assert row == ("llm", "newer llm text")
