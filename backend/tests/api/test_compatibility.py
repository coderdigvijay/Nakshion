from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal
from tests.conftest import FakeLLM, create_chart, register

K = "/api/v1/compatibility"


def _payload(chart1_id: str, **over) -> dict:
    return {
        "chart1_id": chart1_id,
        "partner_name": "Meera",
        "partner_date_of_birth": "1995-02-14",
        "partner_time_of_birth": "09:30",
        "partner_has_exact_time": True,
        "partner_birth_place_name": "Delhi, India",
        "partner_latitude": 28.61,
        "partner_longitude": 77.21,
        "partner_timezone": "Europe/London",
        "relationship_type": "romantic",
        **over,
    }


async def test_create_shape_and_dedupe(client: AsyncClient, fake_llm: FakeLLM) -> None:
    h = await register(client)
    me = await create_chart(client, h)
    r = await client.post(f"{K}/", json=_payload(me["id"]), headers=h)
    assert r.status_code == 201, r.text
    rep = r.json()
    cd = rep["compatibility_data"]
    assert set(cd["categories"]) == {"emotional", "communication", "romance", "passion", "long-term"}
    assert all(isinstance(v["score"], float) and v["summary"] for v in cd["categories"].values())
    assert len(cd["strengths"]) == 3 and len(cd["challenges"]) == 3
    assert len(cd["synastry_aspects"]) <= 10 and all(a["interpretation"] == "interp" for a in cd["synastry_aspects"])
    assert isinstance(rep["overall_score"], float) and 0 <= rep["overall_score"] <= 10
    assert rep["partner_name"] == "Meera" and cd["ashtakoota"] is not None
    charts = (await client.get("/api/v1/charts", headers=h)).json()
    partner = [c for c in charts if c["id"] == rep["chart2_id"]][0]
    assert partner["relationship_label"] == "partner" and partner["timezone"] == "Asia/Kolkata"
    assert charts[0]["id"] == me["id"]  # partner never displaces "my chart"
    again = await client.post(K, json=_payload(me["id"], partner_name="meera"), headers=h)
    assert again.status_code == 200 and again.json()["id"] == rep["id"]
    assert fake_llm.calls["compat"] == 1
    lst = (await client.get(K, headers=h)).json()
    assert [x["id"] for x in lst] == [rep["id"]]
    assert (await client.get(f"{K}/{rep['id']}", headers=h)).json()["partner_name"] == "Meera"


async def test_llm_failure_uses_template(client: AsyncClient, fake_llm: FakeLLM) -> None:
    fake_llm.fail.add("compat")
    h = await register(client)
    me = await create_chart(client, h)
    r = await client.post(K, json=_payload(me["id"], relationship_type="friend"), headers=h)
    assert r.status_code == 201
    cd = r.json()["compatibility_data"]
    assert cd["generated_by"] == "template" and all(v["summary"] for v in cd["categories"].values())
    assert cd["ashtakoota"] is None


async def test_quota(client: AsyncClient, fake_llm: FakeLLM, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "QUOTA_COMPAT_FREE", 1)
    h = await register(client)
    me = await create_chart(client, h)
    assert (await client.post(K, json=_payload(me["id"]), headers=h)).status_code == 201
    r = await client.post(K, json=_payload(me["id"], partner_name="Other", partner_date_of_birth="1990-01-01"), headers=h)
    assert r.status_code == 429 and r.json()["code"] == "QUOTA_EXCEEDED"


async def test_unverified_and_idor(client: AsyncClient, fake_llm: FakeLLM) -> None:
    h = await register(client)
    me = await create_chart(client, h)
    rep = (await client.post(K, json=_payload(me["id"]), headers=h)).json()
    h2 = await register(client, email="eve@example.com")
    assert (await client.post(K, json=_payload(me["id"]), headers=h2)).status_code == 404
    assert (await client.get(f"{K}/{rep['id']}", headers=h2)).status_code == 404
    assert (await client.delete(f"{K}/{rep['id']}", headers=h2)).status_code == 404
    h3 = await register(client, email="unverified@example.com", verified=False)
    mine = await create_chart(client, h3)
    r = await client.post(K, json=_payload(mine["id"]), headers=h3)
    assert r.status_code == 403 and r.json()["code"] == "EMAIL_NOT_VERIFIED"
    assert (await client.delete(f"{K}/{rep['id']}", headers=h)).status_code == 204
    async with SessionLocal() as s:
        assert await s.scalar(text("SELECT count(*) FROM birth_charts WHERE name='Meera'")) == 1  # partner kept


async def test_partner_validation(client: AsyncClient, fake_llm: FakeLLM) -> None:
    h = await register(client)
    me = await create_chart(client, h)
    r = await client.post(K, json=_payload(me["id"], partner_latitude=0, partner_longitude=0), headers=h)
    assert r.status_code == 422 and r.json()["code"] == "INVALID_LOCATION"
    r = await client.post(K, json=_payload(me["id"], relationship_type="enemy"), headers=h)
    assert r.status_code == 422 and isinstance(r.json()["detail"], str)


async def test_concurrent_identical_partner_requests_create_one_partner(client: AsyncClient, fake_llm: FakeLLM) -> None:
    import asyncio

    h = await register(client)
    me = await create_chart(client, h)
    rs = await asyncio.gather(*[client.post(K, json=_payload(me["id"]), headers=h) for _ in range(4)])
    assert all(r.status_code in (200, 201) for r in rs), [r.text for r in rs]
    async with SessionLocal() as s:
        assert await s.scalar(text("SELECT count(*) FROM birth_charts WHERE name='Meera'")) == 1


async def test_llm_narrative_machine_tokens_never_reach_the_report(client: AsyncClient, fake_llm: FakeLLM, monkeypatch) -> None:
    orig = fake_llm.generate_compat_narrative

    async def leaky(report, relationship_type):
        out = await orig(report, relationship_type)
        out["summary"] = "Overall this is below_average and the Nadi dosha is PRESENT."
        out["strengths"] = ["Moon trine Venus", "s2", "s3"]
        return out

    mod = fake_llm.module()
    mod.generate_compat_narrative = leaky
    from app.services import ai

    monkeypatch.setattr(ai, "_module", lambda: mod)
    h = await register(client)
    me = await create_chart(client, h)
    cd = (await client.post(K, json=_payload(me["id"]), headers=h)).json()["compatibility_data"]
    assert cd["summary"] == "Overall this is below average and the Nadi dosha is present."
