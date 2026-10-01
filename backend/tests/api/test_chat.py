from __future__ import annotations

import asyncio
import json

import pytest
from httpx import AsyncClient
from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal
from tests.conftest import FakeLLM, create_chart, register

H = "/api/v1/chat"
Q = {"content": "Will this year be good for a job change?", "language": "english"}


async def _setup(client: AsyncClient, verified: bool = True, chart: bool = True) -> tuple[dict, str]:
    h = await register(client, verified=verified)
    if chart:
        await create_chart(client, h)
    conv = (await client.post(f"{H}/conversations", json={}, headers=h)).json()
    return h, conv["id"]


async def test_send_returns_exactly_two_and_updates_conversation(client: AsyncClient, fake_llm: FakeLLM) -> None:
    h, cid = await _setup(client)
    r = await client.post(f"{H}/conversations/{cid}/messages", json=Q, headers=h)
    assert r.status_code == 200, r.text
    user_msg, ai_msg = r.json()
    assert user_msg["role"] == "user" and user_msg["content"] == Q["content"] and user_msg["tokens_used"] is None
    assert ai_msg["role"] == "assistant" and ai_msg["tokens_used"] == 321
    assert ai_msg["citations"] == [{"factor_id": "V.MD.SATURN", "label": "Saturn mahadasha"}]
    assert "provider" not in ai_msg
    convs = (await client.get(f"{H}/conversations", headers=h)).json()
    assert convs[0]["message_count"] == 2 and convs[0]["category"] == "career"
    assert convs[0]["title"] == "Will this year be good for a job change?"
    detail = (await client.get(f"{H}/conversations/{cid}", headers=h)).json()
    assert [m["role"] for m in detail["messages"]] == ["user", "assistant"]
    me = (await client.get("/api/v1/users/me", headers=h)).json()
    assert me["quota"]["chat_remaining_today"] == 4


async def test_precheck_order_and_codes(client: AsyncClient, fake_llm: FakeLLM) -> None:
    h, cid = await _setup(client, verified=False)
    r = await client.post(f"{H}/conversations/{cid}/messages", json=Q, headers=h)
    assert r.status_code == 403 and r.json()["code"] == "EMAIL_NOT_VERIFIED"
    h3 = await register(client, email="nochart@example.com")
    conv = (await client.post(f"{H}/conversations", json={}, headers=h3)).json()
    assert conv["chart_id"] is None
    r = await client.post(f"{H}/conversations/{conv['id']}/messages", json=Q, headers=h3)
    assert r.status_code == 409 and r.json()["code"] == "CHART_REQUIRED"
    r = await client.post(f"{H}/conversations/{cid}/messages", json=Q, headers=h3)
    assert r.status_code == 404  # not yours beats every other check
    assert fake_llm.calls == {}


async def test_validation(client: AsyncClient, fake_llm: FakeLLM) -> None:
    h, cid = await _setup(client)
    r = await client.post(f"{H}/conversations/{cid}/messages", json={"content": "x" * 2001}, headers=h)
    assert r.status_code == 422 and r.json()["code"] == "MESSAGE_TOO_LONG"
    r = await client.post(f"{H}/conversations/{cid}/messages", json={"content": "hi", "language": "french"}, headers=h)
    assert r.status_code == 422
    r = await client.post(f"{H}/conversations/{cid}/messages", json={"content": "   "}, headers=h)
    assert r.status_code == 422


async def test_quota_exceeded(client: AsyncClient, fake_llm: FakeLLM, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "QUOTA_CHAT_FREE", 1)
    h, cid = await _setup(client)
    assert (await client.post(f"{H}/conversations/{cid}/messages", json=Q, headers=h)).status_code == 200
    r = await client.post(f"{H}/conversations/{cid}/messages", json=Q, headers=h)
    assert r.status_code == 429 and r.json()["code"] == "QUOTA_EXCEEDED" and int(r.headers["retry-after"]) > 0
    assert fake_llm.calls["chat"] == 1  # pre-check saved an LLM call


async def test_llm_failure_persists_nothing(client: AsyncClient, fake_llm: FakeLLM) -> None:
    fake_llm.fail.add("chat")
    h, cid = await _setup(client)
    r = await client.post(f"{H}/conversations/{cid}/messages", json=Q, headers=h)
    assert r.status_code == 503 and r.json()["code"] == "AI_UNAVAILABLE"
    async with SessionLocal() as s:
        assert await s.scalar(text("SELECT count(*) FROM messages")) == 0
        assert await s.scalar(text("SELECT count(*) FROM usage_counters")) == 0
    # lock released: a retry is allowed
    fake_llm.fail.clear()
    assert (await client.post(f"{H}/conversations/{cid}/messages", json=Q, headers=h)).status_code == 200


async def test_concurrent_sends_one_in_flight(client: AsyncClient, fake_llm: FakeLLM) -> None:
    fake_llm.delay_s = 0.3
    h, cid = await _setup(client)
    a, b = await asyncio.gather(
        client.post(f"{H}/conversations/{cid}/messages", json=Q, headers=h),
        client.post(f"{H}/conversations/{cid}/messages", json=Q, headers=h),
    )
    codes = sorted([a.status_code, b.status_code])
    assert codes == [200, 409]
    assert "MESSAGE_IN_FLIGHT" in (a.text + b.text)
    async with SessionLocal() as s:
        assert await s.scalar(text("SELECT message_count FROM conversations")) == 2


async def test_concurrent_quota_never_overshoots(client: AsyncClient, fake_llm: FakeLLM, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "QUOTA_CHAT_FREE", 2)
    fake_llm.delay_s = 0.1
    h = await register(client)
    await create_chart(client, h)
    convs = [(await client.post(f"{H}/conversations", json={}, headers=h)).json()["id"] for _ in range(4)]
    rs = await asyncio.gather(*[client.post(f"{H}/conversations/{c}/messages", json=Q, headers=h) for c in convs])
    assert sum(r.status_code == 200 for r in rs) == 2
    async with SessionLocal() as s:
        assert await s.scalar(text("SELECT count FROM usage_counters")) == 2
        assert await s.scalar(text("SELECT count(*) FROM messages")) == 4


def _events(body: str) -> list[tuple[str, dict]]:
    out = []
    for block in body.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        out.append((lines["event"], json.loads(lines["data"])))
    return out


async def test_stream_happy_path(client: AsyncClient, fake_llm: FakeLLM) -> None:
    h, cid = await _setup(client)
    r = await client.post(f"{H}/conversations/{cid}/messages/stream", json=Q, headers=h)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/event-stream")
    ev = _events(r.text)
    assert [e for e, _ in ev] == ["meta", "delta", "delta", "done"]
    assert ev[-1][1]["assistant_message"]["content"] == "Saturn's steady influence."
    detail = (await client.get(f"{H}/conversations/{cid}", headers=h)).json()
    assert detail["conversation"]["message_count"] == 2 and len(detail["messages"]) == 2


async def test_stream_failure_removes_user_message_and_releases_lock(client: AsyncClient, fake_llm: FakeLLM, redis_client) -> None:
    fake_llm.stream_fail_after_delta = True
    h, cid = await _setup(client)
    r = await client.post(f"{H}/conversations/{cid}/messages/stream", json=Q, headers=h)
    ev = _events(r.text)
    assert ev[-1] == ("error", {"code": "AI_UNAVAILABLE", "detail": ev[-1][1]["detail"]})
    detail = (await client.get(f"{H}/conversations/{cid}", headers=h)).json()
    assert detail["messages"] == [] and detail["conversation"]["message_count"] == 0
    assert await redis_client.exists(f"chat_lock:{cid}") == 0
    async with SessionLocal() as s:
        assert await s.scalar(text("SELECT count(*) FROM usage_counters")) == 0


async def test_stream_client_disconnect_cleans_up(client: AsyncClient, fake_llm: FakeLLM, redis_client) -> None:
    """Simulate a disconnect by closing the generator after the first event."""
    from app.models import User
    from app.schemas.chat import SendMessageIn
    from app.services import chat_service

    fake_llm.delay_s = 5
    h, cid = await _setup(client)
    async with SessionLocal() as s:
        user = await s.scalar(__import__("sqlalchemy").select(User))
        gen = await chat_service.start_stream(s, user, __import__("uuid").UUID(cid), SendMessageIn(**Q))
        first = await gen.__anext__()
        assert first.startswith("event: meta")
        await gen.__anext__()  # first delta, provider now stalls
        await gen.aclose()  # client went away
    detail = (await client.get(f"{H}/conversations/{cid}", headers=h)).json()
    assert detail["messages"] == [] and detail["conversation"]["message_count"] == 0
    assert await redis_client.exists(f"chat_lock:{cid}") == 0


async def test_idor_conversations_and_messages(client: AsyncClient, fake_llm: FakeLLM) -> None:
    h, cid = await _setup(client)
    msgs = (await client.post(f"{H}/conversations/{cid}/messages", json=Q, headers=h)).json()
    h2 = await register(client, email="eve@example.com")
    await create_chart(client, h2)
    assert (await client.get(f"{H}/conversations/{cid}", headers=h2)).status_code == 404
    assert (await client.delete(f"{H}/conversations/{cid}", headers=h2)).status_code == 404
    assert (await client.post(f"{H}/conversations/{cid}/messages", json=Q, headers=h2)).status_code == 404
    assert (await client.put(f"{H}/messages/{msgs[1]['id']}/bookmark", json={"bookmarked": True}, headers=h2)).status_code == 404
    assert (await client.post(f"{H}/messages/{msgs[1]['id']}/feedback", json={"rating": "up"}, headers=h2)).status_code == 404
    chart_of_h = (await client.get("/api/v1/charts", headers=h)).json()[0]["id"]
    r = await client.post(f"{H}/conversations", json={"chart_id": chart_of_h}, headers=h2)
    assert r.status_code == 404  # cannot attach someone else's chart


async def test_bookmark_feedback_delete(client: AsyncClient, fake_llm: FakeLLM) -> None:
    h, cid = await _setup(client)
    msgs = (await client.post(f"{H}/conversations/{cid}/messages", json=Q, headers=h)).json()
    r = await client.put(f"{H}/messages/{msgs[1]['id']}/bookmark", json={"bookmarked": True}, headers=h)
    assert r.status_code == 200 and r.json()["bookmarked"] is True
    assert (await client.post(f"{H}/messages/{msgs[1]['id']}/feedback", json={"rating": "down", "reason": "generic"}, headers=h)).status_code == 204
    detail = (await client.get(f"{H}/conversations/{cid}", headers=h)).json()
    assert detail["messages"][1]["feedback"] == "down"
    assert (await client.delete(f"{H}/conversations/{cid}", headers=h)).status_code == 204
    assert (await client.get(f"{H}/conversations/{cid}", headers=h)).status_code == 404


async def test_sources_exposed_deduped_persisted_and_never_verbatim(client: AsyncClient, fake_llm: FakeLLM) -> None:
    h, cid = await _setup(client)
    user_msg, ai_msg = (await client.post(f"{H}/conversations/{cid}/messages", json=Q, headers=h)).json()
    expected = [
        {"source_id": "a1b2c3d4e5", "title": "Vedic Astrology Primer", "section": "Saturn Mahadasha", "tier": 1},
        {"source_id": "f6g7h8i9j0", "title": "Career Astrology", "section": "Timing", "tier": 2},
    ]
    assert ai_msg["sources"] == expected  # de-duplicated, title-less entry dropped, only the 4 allowed keys
    assert user_msg["sources"] is None
    assert "LONG VERBATIM" not in (await client.get(f"{H}/conversations/{cid}", headers=h)).text
    detail = (await client.get(f"{H}/conversations/{cid}", headers=h)).json()
    assert [m["sources"] for m in detail["messages"]] == [None, expected]  # survives a reload
    assert "file" not in str(ai_msg["sources"]) and "alias" not in str(ai_msg["sources"])


async def test_stream_done_event_carries_sources(client: AsyncClient, fake_llm: FakeLLM, monkeypatch) -> None:
    async def streaming(**kw):
        yield ("delta", "Saturn ")
        yield ("done", {"answer": "Saturn.", "citations": [], "tokens_used": 5, "topic": "career",
                        "sources": [{"source_id": "q1", "title": "Timing Transits", "section": "Saturn", "tier": 1}]})

    monkeypatch.setattr(fake_llm, "stream_chat_reply", streaming)
    mod = fake_llm.module()
    mod.stream_chat_reply = streaming
    from app.services import ai

    monkeypatch.setattr(ai, "_module", lambda: mod)
    h, cid = await _setup(client)
    r = await client.post(f"{H}/conversations/{cid}/messages/stream", json=Q, headers=h)
    done = [d for e, d in _events(r.text) if e == "done"][0]
    assert done["assistant_message"]["sources"] == [{"source_id": "q1", "title": "Timing Transits", "section": "Saturn", "tier": 1}]
    detail = (await client.get(f"{H}/conversations/{cid}", headers=h)).json()
    assert detail["messages"][1]["sources"][0]["title"] == "Timing Transits"


async def test_answer_without_retrieval_has_empty_sources(client: AsyncClient, fake_llm: FakeLLM, monkeypatch) -> None:
    orig = fake_llm.generate_chat_reply

    async def no_sources(**kw):
        out = await orig(**kw)
        out.pop("sources")
        return out

    monkeypatch.setattr(fake_llm, "generate_chat_reply", no_sources)
    mod = fake_llm.module()
    mod.generate_chat_reply = no_sources
    from app.services import ai

    monkeypatch.setattr(ai, "_module", lambda: mod)
    h, cid = await _setup(client)
    ai_msg = (await client.post(f"{H}/conversations/{cid}/messages", json=Q, headers=h)).json()[1]
    assert ai_msg["sources"] == []
