from __future__ import annotations

from httpx import AsyncClient

from tests.conftest import CHART, FakeLLM, create_chart, register

A = "/api/v1"


async def test_suggestions_use_one_system_consistently(client: AsyncClient) -> None:
    h = await register(client)
    chart = await create_chart(client, h)
    cd = chart["chart_data"]
    sidereal_moon = next(p["rashi_english"] for p in cd["vedic"]["planets"] if p["english"] == "Moon")
    tropical_moon = cd["moon_sign"]["sign"]
    assert sidereal_moon != tropical_moon  # the fixture chart is one where the two differ
    vedic = (await client.get(f"{A}/chat/suggestions", headers=h)).json()["suggestions"]
    text = " ".join(vedic)
    assert f"Moon in {sidereal_moon} (sidereal)" in text and "mahadasha" in text and tropical_moon not in text
    await client.put(f"{A}/users/me", json={"astrology_system": "western"}, headers=h)
    western = " ".join((await client.get(f"{A}/chat/suggestions", headers=h)).json()["suggestions"])
    assert f"tropical Moon in {tropical_moon}" in western and "mahadasha" not in western and sidereal_moon not in western


async def test_malformed_json_and_empty_after_strip(client: AsyncClient, fake_llm: FakeLLM) -> None:
    r = await client.post(f"{A}/auth/login", content=b'{"email": "a@b.co", "password": }',
                          headers={"Content-Type": "application/json"})
    assert r.status_code == 422 and r.json()["detail"] == "Request body isn't valid JSON."
    assert r.json()["errors"][0]["field"] == "body"
    h = await register(client)
    await create_chart(client, h)
    cid = (await client.post(f"{A}/chat/conversations", json={}, headers=h)).json()["id"]
    r = await client.post(f"{A}/chat/conversations/{cid}/messages", json={"content": "\x00\x01 \x02"}, headers=h)
    assert r.status_code == 422 and r.json()["detail"] == "Content is required."
    r = await client.post(f"{A}/chat/conversations/{cid}/messages", json={"content": "hi\x00there"}, headers=h)
    assert r.status_code == 200 and r.json()[0]["content"] == "hithere"


async def test_panchang_end_markers_and_rahu_kaal_agree_with_personal_reading(client: AsyncClient, fake_llm: FakeLLM) -> None:
    from datetime import date

    h = await register(client)
    chart = await create_chart(client, h)
    today = date.today().isoformat()
    pc = (await client.get(f"{A}/panchang", params={"date": today, "lat": chart["latitude"], "lon": chart["longitude"]})).json()
    for k in ("tithi", "nakshatra", "yoga", "karana"):
        assert pc[k]["end_local_date"] and pc[k]["end_day_offset"] in (0, 1, 2, -1), pc[k]
    assert any(pc[k]["end_day_offset"] != 0 or pc[k]["end_local_date"] == today for k in ("tithi", "nakshatra", "yoga", "karana"))
    me = (await client.get(f"{A}/users/me", headers=h)).json()
    await client.put(f"{A}/users/me", json={"timezone": pc["timezone"]}, headers=h)  # same zone as the panchang
    r3 = (await client.get(f"{A}/horoscopes/personal/today", headers=h)).json()
    if r3["date"] == today:  # user-local day equals the requested day
        assert r3["timing"]["rahu_kaal"]["start"] == pc["rahu_kaal"]["start"]
        assert r3["timing"]["rahu_kaal"]["end"] == pc["rahu_kaal"]["end"]
    assert me["id"]


async def test_delete_only_chart_then_recover(client: AsyncClient, fake_llm: FakeLLM) -> None:
    h = await register(client)
    only = await create_chart(client, h)
    cid = (await client.post(f"{A}/chat/conversations", json={}, headers=h)).json()["id"]
    assert (await client.delete(f"{A}/charts/{only['id']}", headers=h)).status_code == 204
    assert (await client.get(f"{A}/charts", headers=h)).json() == []  # zero charts is a valid state
    r = await client.post(f"{A}/chat/conversations/{cid}/messages", json={"content": "hi"}, headers=h)
    assert r.status_code == 409 and r.json()["code"] == "CHART_REQUIRED"
    assert (await client.get(f"{A}/horoscopes/personal/today", headers=h)).json()["code"] == "CHART_REQUIRED"
    new = await create_chart(client, h, name="Again", is_primary=False)
    assert new["is_primary"] is True and new["relationship_label"] == "self"  # first chart again -> primary
    r = await client.post(f"{A}/chat/conversations/{cid}/messages", json={"content": "hi"}, headers=h)
    assert r.status_code == 200  # conversation re-attaches to the new primary chart


async def test_delete_primary_with_partner_charts_promotes_self_first(client: AsyncClient) -> None:
    h = await register(client)
    me = await create_chart(client, h, name="Me")
    await create_chart(client, h, name="Friend", is_primary=False, relationship="friend")
    mine2 = await create_chart(client, h, name="Me2", is_primary=False, relationship="self")
    assert (await client.delete(f"{A}/charts/{me['id']}", headers=h)).status_code == 204
    charts = (await client.get(f"{A}/charts", headers=h)).json()
    assert charts[0]["id"] == mine2["id"] and charts[0]["is_primary"] is True and sum(c["is_primary"] for c in charts) == 1
