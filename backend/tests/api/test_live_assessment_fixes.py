from __future__ import annotations

import re

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from app.models import User
from app.services import auth_service, email_service, health_service, oauth_google
from tests.conftest import FakeLLM, create_chart, register

A = "/api/v1"
RESET = f"{A}/auth/reset-password"
BAD_RESET = {"token": "a" * 30, "new_password": "brand new password"}


@pytest.fixture
async def raw() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------------------------------------------------------------- HIGH-1: spoofed X-Forwarded-For
async def test_spoofed_left_xff_entries_do_not_buy_new_buckets(raw: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 1)
    codes = []
    for i in range(11):  # the proxy appends the real client (198.51.100.9); the attacker forges everything to its left
        r = await raw.post(RESET, json=BAD_RESET, headers={"X-Forwarded-For": f"6.6.6.{i}, 198.51.100.9"})
        codes.append(r.status_code)
    assert codes[:10] == [400] * 10 and codes[10] == 429


async def test_login_and_register_limits_hold_under_spoofing(raw: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 1)
    body = {"password": "correct horse battery", "name": "A", "terms_accepted": True}
    codes = [(await raw.post(f"{A}/auth/register", json={**body, "email": f"r{i}@example.com"},
                             headers={"X-Forwarded-For": f"7.7.7.{i}, 198.51.100.20"})).status_code for i in range(6)]
    assert codes[:5] == [201] * 5 and codes[5] == 429  # 5 registrations/hour/IP
    codes = [(await raw.post(f"{A}/auth/login", json={"email": "victim@example.com", "password": "wrong password!"},
                             headers={"X-Forwarded-For": f"8.8.8.{i}, 198.51.100.21"})).status_code for i in range(11)]
    assert codes[:10] == [400] * 10 and codes[10] == 429


async def test_missing_xff_fails_closed_to_one_strict_shared_bucket(raw: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 1)
    codes = [(await raw.post(RESET, json=BAD_RESET)).status_code for _ in range(6)]  # no XFF at all: never "the proxy peer"
    assert codes[:5] == [400] * 5 and codes[5] == 429  # half of the normal 10 for the shared "unknown" bucket


async def test_configured_client_ip_header_separates_honest_clients_and_ignores_xff(raw: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "CLIENT_IP_HEADER", "cf-connecting-ip")
    a = {"cf-connecting-ip": "198.51.100.1"}
    for i in range(10):
        assert (await raw.post(RESET, json=BAD_RESET, headers={**a, "X-Forwarded-For": f"9.9.9.{i}"})).status_code == 400
    assert (await raw.post(RESET, json=BAD_RESET, headers={**a, "X-Forwarded-For": "1.2.3.4"})).status_code == 429  # XFF ignored
    other = await raw.post(RESET, json=BAD_RESET, headers={"cf-connecting-ip": "198.51.100.2"})
    assert other.status_code == 400  # a different honest client has its own bucket
    assert (await raw.post(RESET, json=BAD_RESET, headers={"cf-connecting-ip": "1.1.1.1, 2.2.2.2"})).status_code in (400, 429)


async def test_per_email_lockout_regardless_of_source_ip(raw: AsyncClient, client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    await register(client, email="victim@example.com")
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 1)
    for i in range(10):  # every attempt claims a different, fully attacker-chosen client IP
        r = await raw.post(f"{A}/auth/login", json={"email": "victim@example.com", "password": "guess guess guess"},
                           headers={"X-Forwarded-For": f"10.{i}.0.1"})
        assert r.status_code == 400
    r = await raw.post(f"{A}/auth/login", json={"email": "victim@example.com", "password": "correct horse battery"},
                       headers={"X-Forwarded-For": "10.99.0.1"})
    assert r.status_code == 429 and int(r.headers["retry-after"]) <= 900  # short window, not a permanent lock
    assert "victim" not in r.text  # generic copy
    ok = await raw.post(f"{A}/auth/login", json={"email": "someone-else@example.com", "password": "x" * 9},
                        headers={"X-Forwarded-For": "10.99.0.2"})
    assert ok.status_code == 400  # other accounts are unaffected


async def test_global_email_cap_protects_brevo(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_service, "EMAIL_CAP_PER_HOUR", 5)
    for i in range(3):
        await register(client, email=f"u{i}@example.com", verified=False)  # 3 OTP emails
    sent = len(email_service.outbox)
    for i in range(3):
        r = await client.post(f"{A}/auth/forgot-password", json={"email": f"u{i}@example.com"})
        assert r.status_code == 200 and "reset link is on its way" in r.json()["message"]  # same answer either way
    assert len(email_service.outbox) == sent + 2  # the 6th email of the hour was dropped silently


# ---------------------------------------------------------------- MEDIUM-1 / MEDIUM-2
async def test_default_config_and_health_ready_is_minimal_and_rate_limited(client: AsyncClient) -> None:
    health_service.reset_ready_cache()
    r = await client.get("/health/ready")
    assert r.json() == {"status": "ok"} or r.json() == {"status": "degraded"}  # no chunk counts, versions, internals
    assert "checks" not in r.text and "rag" not in r.text
    wrong = await client.get("/health/ready", headers={"X-Cron-Secret": "nope"})
    assert "checks" not in wrong.text
    live = (await client.get("/health/live")).json()
    assert live["version"] == settings.build_version
    codes = [(await client.get("/health/ready")).status_code for _ in range(12)]
    assert 429 in codes  # 10 per minute per client


# ---------------------------------------------------------------- privacy claims
async def test_terms_acceptance_required_and_recorded(client: AsyncClient) -> None:
    base = {"email": "t@example.com", "password": "correct horse battery", "name": "T"}
    for extra in ({}, {"terms_accepted": False}):
        r = await client.post(f"{A}/auth/register", json={**base, **extra})
        assert r.status_code == 422 and r.json()["code"] == "TERMS_NOT_ACCEPTED"
        assert "Terms and Privacy Policy" in r.json()["detail"]
    assert (await client.post(f"{A}/auth/register", json={**base, "terms_accepted": True})).status_code == 201
    async with SessionLocal() as s:
        u = await s.scalar(select(User).where(User.email == "t@example.com"))
    assert u.terms_accepted_at is not None and u.terms_version == settings.TERMS_VERSION


async def test_google_signup_needs_explicit_terms_acceptance(client: AsyncClient, redis_client) -> None:
    url = await oauth_google.authorization_url(terms_accepted=True)
    state = re.search(r"state=([\w-]+)", url).group(1)
    assert '"terms":true' in await redis_client.get(f"oauth_state:{state}")
    claims = {"sub": "g-1", "email": "new@example.com", "name": "New", "email_verified": True}
    async with SessionLocal() as db:
        with pytest.raises(oauth_google.OAuthFailed, match="terms_required"):
            await oauth_google.upsert_google_user(db, claims, terms_accepted=False)
    async with SessionLocal() as db:
        user = await oauth_google.upsert_google_user(db, claims, terms_accepted=True)
        assert user.terms_version == settings.TERMS_VERSION and user.terms_accepted_at is not None
    async with SessionLocal() as db:  # an EXISTING account may sign in without re-accepting
        assert (await oauth_google.upsert_google_user(db, claims, terms_accepted=False)).email == "new@example.com"


async def test_oauth_callback_reports_terms_required(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_exchange(code: str, state: str):
        return {"sub": "g-2", "email": "n2@example.com", "name": "N", "email_verified": True}, False

    monkeypatch.setattr(oauth_google, "exchange_code", fake_exchange)
    r = await client.get(f"{A}/auth/oauth/google/callback", params={"code": "c", "state": "s"})
    assert r.status_code == 302 and r.headers["location"].endswith("/auth/callback?error=terms_required")


async def test_deletion_log_holds_only_a_hash_and_a_timestamp(client: AsyncClient) -> None:
    h = await register(client)
    await client.request("DELETE", f"{A}/users/me", json={"password": "correct horse battery"}, headers=h)
    async with SessionLocal() as s:
        cols = [r[0] for r in (await s.execute(text(
            "SELECT column_name FROM information_schema.columns WHERE table_name='deletion_log' ORDER BY ordinal_position"))).all()]
        row = (await s.execute(text("SELECT user_id_sha256 FROM deletion_log"))).scalar()
    assert cols == ["id", "user_id_sha256", "deleted_at"]  # no email, name or birth data columns
    assert re.fullmatch(r"[0-9a-f]{64}", row)


async def test_chat_adapter_passes_no_name_and_the_rendered_prompt_has_no_birth_data(client: AsyncClient, fake_llm: FakeLLM, monkeypatch) -> None:
    seen: dict = {}
    orig = fake_llm.generate_chat_reply

    async def spy(**kw):
        seen.update(kw)
        return await orig(**kw)

    mod = fake_llm.module()
    mod.generate_chat_reply = spy
    from app.services import ai

    monkeypatch.setattr(ai, "_module", lambda: mod)
    h = await register(client, email="private.person@example.com", name="Priya Sharma")
    chart = await create_chart(client, h, name="Priya Sharma", birth_place_name="Some Private Street, Pune")
    cid = (await client.post(f"{A}/chat/conversations", json={}, headers=h)).json()["id"]
    assert (await client.post(f"{A}/chat/conversations/{cid}/messages", json={"content": "career?"}, headers=h)).status_code == 200
    assert seen["display_name"] == "the user"  # the chart label (often a real name) is not sent
    for k in ("question", "history", "language", "astrology_system", "tier"):
        assert k in seen
    assert "private.person" not in repr({k: v for k, v in seen.items() if k != "chart_data"})
    # What the provider actually sees is the rendered CHART FACTS block: verify it on the real prompt builder.
    from app.llm.facts import build_chart_facts

    prompt = build_chart_facts(chart["chart_data"], system="vedic", display_name=seen["display_name"]).render()
    for forbidden in ("Priya", "Sharma", "private.person", "Some Private Street", "Pune", "1994-07-21", "14:05", "18.52", "73.85"):
        assert forbidden not in prompt, forbidden
