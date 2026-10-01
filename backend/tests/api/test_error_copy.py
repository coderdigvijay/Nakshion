from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.core.config import settings
from tests.conftest import CHART, FakeLLM, create_chart, register


async def test_validation_messages_are_plain_per_field(client: AsyncClient) -> None:
    h = await register(client)
    cases = [
        ({"name": "x" * 101}, "Name must be 100 characters or fewer."),
        ({"name": ""}, "Name is required."),
        ({"birth_place_name": "p" * 300}, "Birth place name must be 255 characters or fewer."),
        ({"latitude": 91}, "Latitude must be at most 90."),
        ({"date_of_birth": "21/07/1994"}, "Date of birth must be a valid date (YYYY-MM-DD)."),
        ({"time_of_birth": "25:99"}, "Birth time must be HH:MM (24-hour)."),
    ]
    for over, expected in cases:
        r = await client.post("/api/v1/charts/", json={**CHART, **over}, headers=h)
        assert r.status_code == 422 and r.json()["detail"] == expected, (over, r.json())
        assert "items" not in r.json()["detail"] and "String should" not in r.json()["detail"]
    r = await client.post("/api/v1/charts/", json={k: v for k, v in CHART.items() if k != "name"}, headers=h)
    assert r.json()["detail"] == "Name is required."


async def test_quota_429_carries_reset_timestamp_not_a_timezone_label(
    client: AsyncClient, fake_llm: FakeLLM, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "QUOTA_CHAT_FREE", 1)
    h = await register(client)
    await create_chart(client, h)
    cid = (await client.post("/api/v1/chat/conversations", json={}, headers=h)).json()["id"]
    body = {"content": "hello"}
    assert (await client.post(f"/api/v1/chat/conversations/{cid}/messages", json=body, headers=h)).status_code == 200
    r = await client.post(f"/api/v1/chat/conversations/{cid}/messages", json=body, headers=h)
    d = r.json()
    assert r.status_code == 429 and d["code"] == "QUOTA_EXCEEDED"
    assert "UTC" not in d["detail"] and "midnight" not in d["detail"]
    assert d["resets_at"].endswith("Z") and d["limit"] == 1 and int(r.headers["retry-after"]) > 0


async def test_missing_resources_have_distinct_not_found_code(client: AsyncClient, fake_llm: FakeLLM) -> None:
    h = await register(client)
    import uuid

    for url in (f"/api/v1/compatibility/{uuid.uuid4()}", f"/api/v1/charts/{uuid.uuid4()}",
                f"/api/v1/chat/conversations/{uuid.uuid4()}", "/api/v1/compatibility/not-a-uuid",
                "/api/v1/charts/123", "/api/v1/nope"):
        r = await client.get(url, headers=h)
        assert r.status_code == 404 and r.json()["code"] == "NOT_FOUND", url
