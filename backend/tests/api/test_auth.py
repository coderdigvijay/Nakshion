from __future__ import annotations

import re

from httpx import AsyncClient
from sqlalchemy import text

from app.db.session import SessionLocal
from app.services import email_service
from tests.conftest import register

A = "/api/v1/auth"


def _last_otp() -> str:
    body = email_service.outbox[-1]["textContent"]
    return re.search(r"\b(\d{6})\b", body).group(1)


def _last_reset_token() -> str:
    body = email_service.outbox[-1]["textContent"]
    return re.search(r"token=([\w-]+)", body).group(1)


async def test_register_login_me(client: AsyncClient) -> None:
    h = await register(client, verified=False)
    me = (await client.get(f"{A}/me", headers=h)).json()
    assert me["email"] == "asha@example.com" and me["name"] == "Asha"
    assert me["email_verified"] is False and me["has_password"] is True
    assert me["subscription_tier"] == "free" and me["quota"]["chat_daily_limit"] == 5
    assert me["created_at"].endswith("Z")
    assert "password_hash" not in me
    r = await client.post(f"{A}/login", json={"email": "ASHA@example.com ", "password": "correct horse battery"})
    assert r.status_code == 200 and r.json()["token_type"] == "bearer"


async def test_register_duplicate_is_409(client: AsyncClient) -> None:
    await register(client)
    r = await client.post(f"{A}/register", json={"email": "asha@example.com", "password": "correct horse battery", "name": "A"})
    assert r.status_code == 409 and r.json()["code"] == "EMAIL_EXISTS"


async def test_validation_detail_is_string(client: AsyncClient) -> None:
    r = await client.post(f"{A}/register", json={"email": "nope", "password": "correct horse battery", "name": "A"})
    body = r.json()
    assert r.status_code == 422 and isinstance(body["detail"], str)
    assert body["code"] == "VALIDATION_ERROR" and body["errors"][0]["field"] == "email"


async def test_password_policy_codes(client: AsyncClient) -> None:
    long_pw = "é" * 40  # 80 bytes > 72
    r = await client.post(f"{A}/register", json={"email": "a@example.com", "password": long_pw, "name": "A"})
    assert r.status_code == 422 and r.json()["code"] == "PASSWORD_TOO_LONG"
    r = await client.post(f"{A}/register", json={"email": "a@example.com", "password": "12345678", "name": "A"})
    assert r.status_code == 422 and r.json()["code"] == "PASSWORD_TOO_COMMON"
    r = await client.post(f"{A}/register", json={"email": "a@example.com", "password": "pw", "name": "A", "is_admin": True})
    assert r.status_code == 422


async def test_wrong_password_is_400_not_401(client: AsyncClient) -> None:
    await register(client)
    r = await client.post(f"{A}/login", json={"email": "asha@example.com", "password": "wrong password!"})
    assert r.status_code == 400 and r.json()["code"] == "INVALID_CREDENTIALS"
    r = await client.post(f"{A}/login", json={"email": "ghost@example.com", "password": "whatever123"})
    assert r.status_code == 400 and r.json()["code"] == "INVALID_CREDENTIALS"


async def test_login_bruteforce_limited(client: AsyncClient) -> None:
    await register(client)
    for _ in range(10):
        await client.post(f"{A}/login", json={"email": "asha@example.com", "password": "wrong password!"})
    r = await client.post(f"{A}/login", json={"email": "asha@example.com", "password": "correct horse battery"})
    assert r.status_code == 429 and r.json()["code"] == "RATE_LIMITED" and "retry-after" in r.headers


async def test_unauthenticated_and_bad_tokens(client: AsyncClient) -> None:
    assert (await client.get(f"{A}/me")).status_code == 401
    r = await client.get(f"{A}/me", headers={"Authorization": "Bearer not.a.jwt"})
    assert r.status_code == 401 and r.json()["code"] == "UNAUTHENTICATED"


async def test_logout_all_revokes_token(client: AsyncClient) -> None:
    h = await register(client)
    assert (await client.post(f"{A}/logout-all", headers=h)).status_code == 200
    assert (await client.get(f"{A}/me", headers=h)).status_code == 401


async def test_verify_email_flow(client: AsyncClient) -> None:
    h = await register(client, verified=False)
    code = _last_otp()
    r = await client.post(f"{A}/verify-email", json={"code": "000000" if code != "000000" else "111111"}, headers=h)
    assert r.status_code == 400 and r.json()["code"] == "INVALID_CODE"
    r = await client.post(f"{A}/verify-email", json={"code": code}, headers=h)
    assert r.status_code == 200 and r.json()["message"] == "Email verified"
    assert (await client.get(f"{A}/me", headers=h)).json()["email_verified"] is True
    # idempotent
    assert (await client.post(f"{A}/verify-email", json={"code": "123456"}, headers=h)).status_code == 200


async def test_verify_attempts_exhausted(client: AsyncClient) -> None:
    h = await register(client, verified=False)
    code = _last_otp()
    wrong = "000000" if code != "000000" else "111111"
    for _ in range(5):
        assert (await client.post(f"{A}/verify-email", json={"code": wrong}, headers=h)).status_code == 400
    r = await client.post(f"{A}/verify-email", json={"code": code}, headers=h)
    assert r.status_code in (400, 429)  # code invalidated after 5 wrong attempts
    assert (await client.get(f"{A}/me", headers=h)).json()["email_verified"] is False


async def test_resend_otp_throttled(client: AsyncClient) -> None:
    h = await register(client, verified=False)
    r = await client.post(f"{A}/resend-otp", headers=h)
    assert r.status_code == 429 and "retry-after" in r.headers  # register just sent one


async def test_forgot_reset_flow_single_use_and_revokes(client: AsyncClient) -> None:
    h = await register(client, verified=False)
    r = await client.post(f"{A}/forgot-password", json={"email": "asha@example.com"})
    assert r.status_code == 200
    token = _last_reset_token()
    async with SessionLocal() as s:  # raw token never stored
        stored = await s.scalar(text("SELECT token FROM password_resets"))
    assert stored != token and len(stored) == 64
    r = await client.post(f"{A}/reset-password", json={"token": token, "new_password": "a brand new secret"})
    assert r.status_code == 200
    assert (await client.get(f"{A}/me", headers=h)).status_code == 401  # token_version bumped
    r = await client.post(f"{A}/reset-password", json={"token": token, "new_password": "another new secret"})
    assert r.status_code == 400 and r.json()["code"] == "INVALID_OR_EXPIRED_TOKEN"
    r = await client.post(f"{A}/login", json={"email": "asha@example.com", "password": "a brand new secret"})
    assert r.status_code == 200
    h2 = {"Authorization": f"Bearer {r.json()['access_token']}"}
    assert (await client.get(f"{A}/me", headers=h2)).json()["email_verified"] is True


async def test_forgot_unknown_email_same_answer(client: AsyncClient) -> None:
    r = await client.post(f"{A}/forgot-password", json={"email": "ghost@example.com"})
    assert r.status_code == 200 and email_service.outbox == []


async def test_change_and_set_password(client: AsyncClient) -> None:
    h = await register(client)
    r = await client.post(f"{A}/change-password", json={"current_password": "nope nope", "new_password": "fresh password 1"}, headers=h)
    assert r.status_code == 400 and r.json()["code"] == "INVALID_CURRENT_PASSWORD"
    r = await client.post(f"{A}/change-password", json={"current_password": "correct horse battery", "new_password": "fresh password 1"}, headers=h)
    assert r.status_code == 200
    assert (await client.get(f"{A}/me", headers=h)).status_code == 200  # MVP: no token bump
    r = await client.post(f"{A}/set-password", json={"new_password": "fresh password 2"}, headers=h)
    assert r.status_code == 409 and r.json()["code"] == "PASSWORD_ALREADY_SET"


async def test_oauth_only_user_change_password_and_set(client: AsyncClient) -> None:
    h = await register(client)
    async with SessionLocal() as s:
        await s.execute(text("UPDATE users SET password_hash = NULL"))
        await s.commit()
    r = await client.post(f"{A}/change-password", json={"current_password": "x", "new_password": "fresh password 1"}, headers=h)
    assert r.status_code == 400 and r.json()["code"] == "NO_PASSWORD_SET"
    r = await client.post(f"{A}/login", json={"email": "asha@example.com", "password": "anything goes"})
    assert r.status_code == 400
    assert (await client.post(f"{A}/set-password", json={"new_password": "fresh password 1"}, headers=h)).status_code == 200
    assert (await client.get(f"{A}/me", headers=h)).json()["has_password"] is True


async def test_oauth_callback_failures_redirect(client: AsyncClient) -> None:
    r = await client.get(f"{A}/oauth/google/callback", params={"code": "x", "state": "never-issued"})
    assert r.status_code == 302 and r.headers["location"].endswith("/auth/callback?error=oauth_failed")
    assert r.headers["referrer-policy"] == "no-referrer"


async def test_delete_account_cascades_and_revokes(client: AsyncClient) -> None:
    h = await register(client)
    r = await client.request("DELETE", "/api/v1/users/me", headers=h)  # no re-auth -> refused
    assert r.status_code == 400 and r.json()["code"] == "REAUTH_REQUIRED"
    r = await client.request("DELETE", "/api/v1/users/me", json={"password": "correct horse battery"}, headers=h)
    assert r.status_code == 204
    assert (await client.get(f"{A}/me", headers=h)).status_code == 401
    async with SessionLocal() as s:
        assert await s.scalar(text("SELECT count(*) FROM users")) == 0
        assert await s.scalar(text("SELECT count(*) FROM deletion_log")) == 1


async def test_update_me(client: AsyncClient) -> None:
    h = await register(client)
    r = await client.put("/api/v1/users/me", json={"name": "  Asha Rao ", "timezone": "Asia/Kolkata"}, headers=h)
    assert r.status_code == 200 and r.json()["name"] == "Asha Rao" and r.json()["timezone"] == "Asia/Kolkata"
    r = await client.put("/api/v1/users/me", json={"timezone": "Mars/Base"}, headers=h)
    assert r.status_code == 422
    r = await client.put("/api/v1/users/me", json={"subscription_tier": "premium"}, headers=h)
    assert r.status_code == 422  # mass assignment blocked
