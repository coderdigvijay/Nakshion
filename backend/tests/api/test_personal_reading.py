from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.services import engine
from tests.conftest import FakeLLM, create_chart, register

P = "/api/v1/horoscopes/personal/today"

FACTS = {
    "areas": {"love": {"score": 4}, "career": {"score": 9}, "wellness": {"score": 2}, "money": {"score": 3}},
    "key_factors": [{"factor_id": "T.SATURN.CONJ.N.MOON", "label": "Saturn conjunct natal Moon", "weight": 0.8}],
    "timing": {"rahu_kaal": {"start": "13:30", "end": "15:00"}},
    "dasha_context": {"maha": "Saturn", "antar": "Mercury", "note": "steady"},
    "lucky": {"number": 5, "color": "Green"},
}


@pytest.fixture
def stub_engine(monkeypatch: pytest.MonkeyPatch) -> dict:
    calls = {"n": 0, "charts": []}

    async def personal_day(chart_data, on, **kw):
        calls["n"] += 1
        calls["charts"].append(chart_data["metadata"]["timezone"])
        return FACTS

    monkeypatch.setattr(engine, "personal_day", personal_day)
    return calls


async def test_personal_reading_template_shape_and_cache(client: AsyncClient, fake_llm: FakeLLM, stub_engine: dict) -> None:
    h = await register(client)
    chart = await create_chart(client, h)
    r = await client.get(P, headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["chart_id"] == chart["id"] and d["generated_by"] == "template"  # fake app.llm has no generator
    assert d["areas"]["career"]["score"] == 5 and d["areas"]["wellness"]["score"] == 2  # clamped 1..5
    assert all(d["areas"][k]["text"] for k in ("love", "career", "wellness", "money"))
    assert len(d["headline"]) <= 90 and d["lucky"] == {"number": 5, "color": "Green"}
    assert (await client.get(P, headers=h)).json() == d
    assert stub_engine["n"] == 1


async def test_primary_change_regenerates(client: AsyncClient, fake_llm: FakeLLM, stub_engine: dict) -> None:
    h = await register(client)
    await create_chart(client, h)
    first = (await client.get(P, headers=h)).json()
    other = await create_chart(client, h, name="NY", latitude=40.71, longitude=-74.0, is_primary=True)
    second = (await client.get(P, headers=h)).json()
    assert second["chart_id"] == other["id"] != first["chart_id"]
    assert stub_engine["charts"] == ["Asia/Kolkata", "America/New_York"]


async def test_personal_reading_prechecks(client: AsyncClient, fake_llm: FakeLLM, stub_engine: dict) -> None:
    assert (await client.get(P)).status_code == 401
    h = await register(client)
    r = await client.get(P, headers=h)
    assert r.status_code == 409 and r.json()["code"] == "CHART_REQUIRED"
    h2 = await register(client, email="u@example.com", verified=False)
    await create_chart(client, h2)
    assert (await client.get(P, headers=h2)).json()["code"] == "EMAIL_NOT_VERIFIED"


async def test_engine_without_personal_day_is_503(client: AsyncClient, fake_llm: FakeLLM,
                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    real_fn = engine._fn

    def missing(name: str):
        if name == "personal_day":
            raise engine.EngineMissing(name)
        return real_fn(name)

    monkeypatch.setattr(engine, "_fn", missing)
    h = await register(client)
    await create_chart(client, h)
    r = await client.get(P, headers=h)
    assert r.status_code == 503 and r.json()["code"] == "PERSONAL_READING_UNAVAILABLE"
    assert r.headers["retry-after"] == "30"
