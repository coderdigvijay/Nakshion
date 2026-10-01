from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import text

from app.db.session import SessionLocal
from tests.conftest import CHART, FakeLLM, create_chart, register

K = "/api/v1/compatibility"


async def test_unknown_time_chart_shape_roundtrips(client: AsyncClient) -> None:
    h = await register(client)
    c = await create_chart(client, h, time_of_birth=None)
    cd = c["chart_data"]
    assert c["time_of_birth"] is None and c["has_exact_time"] is False
    assert cd["metadata"]["houses_available"] is False and cd["houses"] == []
    assert cd["rising_sign"]["sign"] == "Unknown" and "mc" not in cd
    assert all(p["house"] is None for p in cd["planets"])
    v = cd["vedic"]
    assert v["lagna"] is None and v["houses_available"] is False and v["house_lords"] == []
    assert v["functional_benefics"] == [] and v["yogakaraka"] is None
    assert "navamsa_d9" not in v and "dashamsa_d10" not in v and v["suppressed"]["items"]
    assert v["dasha"]["approximate"] is True and v["dasha"]["candidates"] and v["dasha"]["approximate_note"]
    got = (await client.get(f"/api/v1/charts/{c['id']}", headers=h)).json()
    assert got["chart_data"]["vedic"]["lagna"] is None  # nulls survive the response schema


async def test_stored_1x_chart_is_recomputed_on_read(client: AsyncClient) -> None:
    h = await register(client)
    c = await create_chart(client, h, time_of_birth=None)
    async with SessionLocal() as s:
        await s.execute(text(
            "UPDATE birth_charts SET engine_version='1.0.0', "
            "chart_data = jsonb_set(chart_data, '{metadata,engine_version}', '\"1.0.0\"')"))
        await s.commit()
    got = (await client.get(f"/api/v1/charts/{c['id']}", headers=h)).json()
    assert got["chart_data"]["metadata"]["engine_version"].startswith("2.")
    assert got["chart_data"]["metadata"]["houses_available"] is False
    listed = (await client.get("/api/v1/charts", headers=h)).json()
    assert listed[0]["chart_data"]["metadata"]["engine_version"].startswith("2.")


def _payload(cid: str, **over) -> dict:
    return {"chart1_id": cid, "partner_name": "Meera", "partner_date_of_birth": "1995-02-14",
            "partner_time_of_birth": None, "partner_has_exact_time": False,
            "partner_birth_place_name": "Delhi", "partner_latitude": 28.61, "partner_longitude": 77.21,
            "partner_timezone": "Asia/Kolkata", "relationship_type": "romantic", **over}


async def test_compat_score_breakdown_and_ashtakoota_notes(client: AsyncClient, fake_llm: FakeLLM) -> None:
    h = await register(client)
    me = await create_chart(client, h)
    r = await client.post(K, json=_payload(me["id"]), headers=h)
    assert r.status_code == 201, r.text
    cd = r.json()["compatibility_data"]
    sb = cd["score_breakdown"]
    assert {"category_weights", "category_scores", "weighted_contributions", "blend", "formula", "explanation"} <= set(sb)
    assert sb["ashtakoota"]["included"] is True and sb["ashtakoota"]["tables_fixture_verified"] is False
    ak = cd["ashtakoota"]
    assert ak["tables_fixture_verified"] is False and ak["tables_note"] and "total_range" in ak
    assert cd["approximate"] is True
    r2 = await client.post(K, json=_payload(me["id"], relationship_type="friend"), headers=h)
    cd2 = r2.json()["compatibility_data"]
    assert cd2["ashtakoota"] is None and cd2["score_breakdown"]["ashtakoota"]["included"] is False


async def test_personal_reading_for_unknown_time_chart(client: AsyncClient, fake_llm: FakeLLM) -> None:
    h = await register(client)
    await create_chart(client, h, time_of_birth=None)
    r = await client.get("/api/v1/horoscopes/personal/today", headers=h)
    assert r.status_code == 200 and set(r.json()["areas"]) == {"love", "career", "wellness", "money"}
