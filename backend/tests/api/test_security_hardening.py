from __future__ import annotations

import asyncio
import re
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models import User
from app.services import cache, email_service, oauth_google
from tests.conftest import FakeLLM, create_chart, register

A = "/api/v1"


# ---------------------------------------------------------------- 1. client IP behind a proxy
async def test_rate_limit_buckets_per_forwarded_client(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 1)
    body = {"email": "a@example.com", "password": "correct horse battery", "name": "A"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        # 5 registrations/hour/IP: client X exhausts its bucket, client Y (same proxy peer) is unaffected.
        for i in range(5):
            r = await c.post(f"{A}/auth/register", json={**body, "email": f"x{i}@example.com"},
                             headers={"X-Forwarded-For": "6.6.6.6, 203.0.113.10"})
            assert r.status_code == 201
        r = await c.post(f"{A}/auth/register", json={**body, "email": "x9@example.com"},
                         headers={"X-Forwarded-For": "1.1.1.1, 203.0.113.10"})
        assert r.status_code == 429  # spoofed left entry did not buy a fresh bucket
        r = await c.post(f"{A}/auth/register", json={**body, "email": "y@example.com"},
                         headers={"X-Forwarded-For": "198.51.100.7"})
        assert r.status_code == 201  # a different real client has its own bucket


# ---------------------------------------------------------------- 2. OAuth one-time code
async def _user_id(email: str) -> User:
    async with SessionLocal() as s:
        return await s.scalar(select(User).where(User.email == email))


async def test_oauth_code_exchange_single_use_and_revocable(client: AsyncClient) -> None:
    await register(client)
    user = await _user_id("asha@example.com")
    url = await oauth_google.success_redirect(user)
    assert "token=" not in url and "?code=" in url and "eyJ" not in url
    code = re.search(r"code=([\w-]+)", url).group(1)
    r = await client.post(f"{A}/auth/oauth/exchange", json={"code": code})
    assert r.status_code == 200 and r.json()["token_type"] == "bearer"
    me = await client.get(f"{A}/auth/me", headers={"Authorization": f"Bearer {r.json()['access_token']}"})
    assert me.status_code == 200 and me.json()["email"] == "asha@example.com"
    again = await client.post(f"{A}/auth/oauth/exchange", json={"code": code})
    assert again.status_code == 400 and again.json()["code"] == "INVALID_OR_EXPIRED_CODE"
    # token_version bumped between redirect and exchange -> refused
    url2 = await oauth_google.success_redirect(user)
    code2 = re.search(r"code=([\w-]+)", url2).group(1)
    async with SessionLocal() as s:
        await s.execute(text("UPDATE users SET token_version = token_version + 1"))
        await s.commit()
    assert (await client.post(f"{A}/auth/oauth/exchange", json={"code": code2})).status_code == 400


async def test_oauth_code_ttl_is_60s(client: AsyncClient, redis_client) -> None:
    await register(client)
    url = await oauth_google.success_redirect(await _user_id("asha@example.com"))
    code = re.search(r"code=([\w-]+)", url).group(1)
    assert 0 < await redis_client.ttl(f"oauth_code:{code}") <= 60
    assert (await client.post(f"{A}/auth/oauth/exchange", json={"code": "x" * 30})).status_code == 400
    assert (await client.post(f"{A}/auth/oauth/exchange", json={"code": "short"})).status_code == 422


# ---------------------------------------------------------------- 3. body size cap
async def test_body_cap_content_length_and_streaming(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    big = {"email": "a@example.com", "password": "correct horse battery", "name": "A" * 70000}
    r = await client.post(f"{A}/auth/register", json=big)
    assert r.status_code == 413 and r.json()["code"] == "PAYLOAD_TOO_LARGE"

    async def chunks():  # chunked upload: no Content-Length header at all
        for _ in range(20):
            yield b"x" * 8000

    r = await client.post(f"{A}/auth/login", content=chunks(), headers={"Content-Type": "application/json"})
    assert r.status_code == 413 and r.json()["code"] == "PAYLOAD_TOO_LARGE"
    ok = await client.post(f"{A}/auth/login", json={"email": "a@example.com", "password": "pw"})
    assert ok.status_code == 400  # normal bodies unaffected


# ---------------------------------------------------------------- 4. timezone change limit
async def test_timezone_change_once_per_day(client: AsyncClient) -> None:
    h = await register(client)
    r = await client.put(f"{A}/users/me", json={"timezone": "Asia/Kolkata"}, headers=h)
    assert r.status_code == 200
    assert (await client.put(f"{A}/users/me", json={"timezone": "Asia/Kolkata"}, headers=h)).status_code == 200  # no-op
    r = await client.put(f"{A}/users/me", json={"timezone": "Pacific/Auckland"}, headers=h)
    assert r.status_code == 429 and r.json()["code"] == "RATE_LIMITED" and int(r.headers["retry-after"]) > 0
    assert (await client.put(f"{A}/users/me", json={"name": "New Name"}, headers=h)).status_code == 200  # name unaffected


# ---------------------------------------------------------------- 5. reserve quota before the LLM
async def test_chat_quota_reserved_before_llm(client: AsyncClient, fake_llm: FakeLLM, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "QUOTA_CHAT_FREE", 2)
    fake_llm.delay_s = 0.15
    h = await register(client)
    await create_chart(client, h)
    convs = [(await client.post(f"{A}/chat/conversations", json={}, headers=h)).json()["id"] for _ in range(6)]
    rs = await asyncio.gather(*[
        client.post(f"{A}/chat/conversations/{c}/messages", json={"content": "hello"}, headers=h) for c in convs])
    assert sorted(r.status_code for r in rs) == [200, 200, 429, 429, 429, 429]
    assert fake_llm.calls["chat"] == 2  # no LLM spend beyond the limit (old code made all 6 calls)


async def test_quota_released_on_failure_stream_and_nonstream(client: AsyncClient, fake_llm: FakeLLM) -> None:
    h = await register(client)
    await create_chart(client, h)
    cid = (await client.post(f"{A}/chat/conversations", json={}, headers=h)).json()["id"]
    fake_llm.fail.add("chat")
    assert (await client.post(f"{A}/chat/conversations/{cid}/messages", json={"content": "hi"}, headers=h)).status_code == 503
    fake_llm.fail.add("stream")
    await client.post(f"{A}/chat/conversations/{cid}/messages/stream", json={"content": "hi"}, headers=h)
    me = (await client.get(f"{A}/users/me", headers=h)).json()
    assert me["quota"]["chat_remaining_today"] == me["quota"]["chat_daily_limit"]


async def test_stream_first_message_category_comes_from_reply(client: AsyncClient, fake_llm: FakeLLM) -> None:
    h = await register(client)
    await create_chart(client, h)
    cid = (await client.post(f"{A}/chat/conversations", json={}, headers=h)).json()["id"]
    await client.post(f"{A}/chat/conversations/{cid}/messages/stream", json={"content": "career?"}, headers=h)
    conv = (await client.get(f"{A}/chat/conversations/{cid}", headers=h)).json()["conversation"]
    assert conv["category"] == "career" and conv["title"] == "career?"


# ---------------------------------------------------------------- 6. public daily date window
async def test_daily_by_date_limited_to_today_pm1(client: AsyncClient, fake_llm: FakeLLM) -> None:
    from datetime import date, timedelta

    far = (date.today() - timedelta(days=10)).isoformat()
    r = await client.get(f"{A}/horoscopes/daily/{far}", params={"sign": "leo"})
    assert r.status_code == 422 and r.json()["code"] == "DATE_OUT_OF_RANGE"
    assert fake_llm.calls.get("daily", 0) == 0
    ok = await client.get(f"{A}/horoscopes/daily/{date.today().isoformat()}", params={"sign": "leo"})
    assert ok.status_code == 200


# ---------------------------------------------------------------- 7. deletion needs re-auth
async def test_delete_requires_password(client: AsyncClient) -> None:
    h = await register(client)
    for body, code in (({}, "REAUTH_REQUIRED"), ({"password": "wrong password!"}, "INVALID_CURRENT_PASSWORD")):
        r = await client.request("DELETE", f"{A}/users/me", json=body, headers=h)
        assert r.status_code == 400 and r.json()["code"] == code
    assert (await client.get(f"{A}/users/me", headers=h)).status_code == 200  # still exists
    assert (await client.request("DELETE", f"{A}/users/me", json={"password": "correct horse battery"}, headers=h)).status_code == 204


async def test_delete_oauth_only_user_needs_emailed_code(client: AsyncClient) -> None:
    h = await register(client)
    async with SessionLocal() as s:
        await s.execute(text("UPDATE users SET password_hash = NULL"))
        await s.commit()
    r = await client.request("DELETE", f"{A}/users/me", json={}, headers=h)
    assert r.status_code == 400 and r.json()["code"] == "REAUTH_REQUIRED"
    assert (await client.post(f"{A}/users/me/deletion-code", headers=h)).status_code == 200
    code = re.search(r"\b(\d{6})\b", email_service.outbox[-1]["textContent"]).group(1)
    wrong = "000000" if code != "000000" else "111111"
    r = await client.request("DELETE", f"{A}/users/me", json={"code": wrong}, headers=h)
    assert r.status_code == 400 and r.json()["code"] == "INVALID_CODE"
    assert (await client.request("DELETE", f"{A}/users/me", json={"code": code}, headers=h)).status_code == 204
    assert (await client.get(f"{A}/users/me", headers=h)).status_code == 401


async def test_deletion_code_refused_for_password_users(client: AsyncClient) -> None:
    h = await register(client)
    r = await client.post(f"{A}/users/me/deletion-code", headers=h)
    assert r.status_code == 400 and r.json()["code"] == "PASSWORD_REAUTH_ONLY"


# ---------------------------------------------------------------- 8. JWT library swap
async def test_tokens_are_hs256_and_reject_alg_none(client: AsyncClient) -> None:
    import base64, json

    h = await register(client)
    tok = h["Authorization"].split()[1]
    header = json.loads(base64.urlsafe_b64decode(tok.split(".")[0] + "=="))
    assert header["alg"] == "HS256"
    payload = tok.split(".")[1]
    none_tok = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode() + "." + payload + "."
    assert (await client.get(f"{A}/auth/me", headers={"Authorization": f"Bearer {none_tok}"})).status_code == 401


# ---------------------------------------------------------------- DB suspended / cold -> clear 503
async def test_database_waking_up_is_503_with_retry_after(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from sqlalchemy.exc import OperationalError

    h = await register(client)

    async def boom(*a, **k):
        raise OperationalError("SELECT 1", {}, ConnectionError("connection timed out"))

    monkeypatch.setattr("app.routers.users.user_service.get_me", boom)
    r = await client.get(f"{A}/users/me", headers=h)
    assert r.status_code == 503 and r.json()["code"] == "DEPENDENCY_UNAVAILABLE"
    assert "waking up" in r.json()["detail"] and r.headers["retry-after"] == "5"
    assert "connection timed out" not in r.text  # no driver text leaks


# ---------------------------------------------------------------- CORS exposes Retry-After on errors
ORIGIN = settings.cors_origins_list[0]  # an origin the app was actually configured with at import


async def test_retry_after_and_request_id_exposed_to_browsers(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from sqlalchemy.exc import OperationalError

    h = await register(client)
    # 503 (database waking up) carries Retry-After and the expose list
    async def boom(*a, **k):
        raise OperationalError("SELECT 1", {}, ConnectionError("x"))

    monkeypatch.setattr("app.routers.users.user_service.get_me", boom)
    r = await client.get(f"{A}/users/me", headers={**h, "Origin": ORIGIN})
    assert r.status_code == 503 and r.headers["retry-after"] == "5"
    exposed = r.headers["access-control-expose-headers"].lower()
    assert "retry-after" in exposed and "x-request-id" in exposed
    # 429 as well
    for _ in range(11):
        r = await client.post(f"{A}/auth/login", json={"email": "a@example.com", "password": "wrong password!"},
                              headers={"Origin": ORIGIN})
    assert r.status_code == 429 and "retry-after" in r.headers
    assert "retry-after" in r.headers["access-control-expose-headers"].lower()


async def test_unhandled_500_still_carries_cors_headers(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    h = await register(client)

    async def boom(*a, **k):
        raise RuntimeError("bug")

    monkeypatch.setattr("app.routers.users.user_service.get_me", boom)
    r = await client.get(f"{A}/users/me", headers={**h, "Origin": ORIGIN})
    assert r.status_code == 500 and r.json()["code"] == "INTERNAL_ERROR"
    assert r.headers.get("access-control-allow-origin") == ORIGIN
