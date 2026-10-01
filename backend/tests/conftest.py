"""Shared fixtures for API/service tests.

- Postgres: a disposable ``<dev db>_test`` database migrated with ``alembic upgrade head``
  (never Neon). Tables are truncated before each test.
- Redis: fakeredis injected through services.cache.set_client.
- LLM: a fake ``app.llm`` module injected at the services/ai.py adapter seam.
- Email: captured in email_service.outbox (no network).
The real astrology engine is used (pure CPU, no network).
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

BACKEND = Path(__file__).resolve().parents[1]


def _test_db_url() -> str:
    from dotenv import dotenv_values

    base = os.environ.get("TEST_DATABASE_URL") or dotenv_values(BACKEND / ".env").get("DATABASE_URL", "")
    u = urlparse(base)
    if u.hostname not in ("localhost", "127.0.0.1", "::1"):
        raise RuntimeError("Tests only run against a local Postgres (refusing non-local DATABASE_URL).")
    name = u.path.lstrip("/")
    if not name.endswith("_test"):
        name = f"{name}_test"
    # One scratch DB per pytest process: concurrent runs (other agents, CI) never truncate each other.
    name = f"{name}_{os.getpid()}"
    return base.rsplit("/", 1)[0] + "/" + name


TEST_DB_URL = _test_db_url()
os.environ["DATABASE_URL"] = TEST_DB_URL
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-test-secret-key-0123")
os.environ["BCRYPT_ROUNDS"] = "4"
os.environ["APP_ENV"] = "test"
os.environ["CRON_SECRET"] = "test-cron-secret"
os.environ["LOCATIONIQ_API_KEY"] = "test-liq"
os.environ["GEOAPIFY_API_KEY"] = "test-geoapify"
os.environ["BREVO_API_KEY"] = ""


def _ensure_db() -> None:
    import psycopg

    sync = TEST_DB_URL.replace("+asyncpg", "")
    admin = sync.rsplit("/", 1)[0] + "/postgres"
    name = sync.rsplit("/", 1)[1]
    with psycopg.connect(admin, autocommit=True) as conn:
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname=%s", (name,)).fetchone():
            conn.execute(f'CREATE DATABASE "{name}"')
    env = {**os.environ, "DATABASE_URL": TEST_DB_URL}
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, env=env, check=True,
                   capture_output=True)


_ensure_db()


def pytest_sessionfinish(session, exitstatus) -> None:  # noqa: ARG001
    import psycopg

    sync = TEST_DB_URL.replace("+asyncpg", "")
    admin, name = sync.rsplit("/", 1)[0] + "/postgres", sync.rsplit("/", 1)[1]
    try:
        with psycopg.connect(admin, autocommit=True) as conn:
            conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
    except Exception:  # noqa: BLE001 - best-effort cleanup
        pass

import asyncio  # noqa: E402
import types  # noqa: E402
from collections.abc import AsyncIterator  # noqa: E402
from typing import Any  # noqa: E402

import fakeredis  # noqa: E402
import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.core import ratelimit  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services import ai, cache, email_service  # noqa: E402

TABLES = (
    "users, password_resets, birth_charts, conversations, messages, daily_horoscopes, "
    "compatibility_reports, usage_counters, llm_usage, message_feedback, personal_readings, deletion_log"
)


class FakeLLM:
    """Stands in for app.llm; records calls and can be told to fail or stall."""

    def __init__(self) -> None:
        self.calls: dict[str, int] = {}
        self.fail: set[str] = set()
        self.delay_s = 0.0
        self.stream_fail_after_delta = False

    def _hit(self, name: str) -> None:
        self.calls[name] = self.calls.get(name, 0) + 1
        if name in self.fail:
            raise type("LLMUnavailable", (Exception,), {})("down")

    async def generate_chat_reply(self, **kw: Any) -> dict:
        self._hit("chat")
        if self.delay_s:
            await asyncio.sleep(self.delay_s)
        return {
            "answer": "Saturn's steady influence favours a measured career move this year.",
            "citations": [{"factor_id": "V.MD.SATURN", "label": "Saturn mahadasha"}],
            "tokens_used": 321,
            "topic": "career",
            "sources": [
                {"source_id": "a1b2c3d4e5", "title": "Vedic Astrology Primer", "section": "Saturn Mahadasha", "tier": 1,
                 "content": "LONG VERBATIM PASSAGE", "file": "indian_bphs.md", "alias": "K1"},
                {"source_id": "a1b2c3d4e5", "title": "Vedic Astrology Primer", "section": "Saturn Mahadasha", "tier": 1},
                {"source_id": "f6g7h8i9j0", "title": "Career Astrology", "section": "Timing", "tier": 2},
                {"source_id": "zzz", "title": "", "section": "ignored: no title"},
            ],
            "metadata": {"provider": "fake", "prompt_version": "chat@test"},
        }

    async def stream_chat_reply(self, **kw: Any) -> AsyncIterator[tuple[str, Any]]:
        self._hit("stream")
        yield ("delta", "Saturn's steady ")
        if self.stream_fail_after_delta:
            raise type("LLMUnavailable", (Exception,), {})("mid-stream")
        if self.delay_s:
            await asyncio.sleep(self.delay_s)
        yield ("delta", "influence.")
        yield ("done", {"answer": "Saturn's steady influence.", "citations": [], "tokens_used": 50, "topic": "career"})

    async def generate_daily_sign(self, sign: str, date: Any, transit_data: dict, *, system: str = "tropical") -> dict:
        self._hit("daily")
        if self.delay_s:
            await asyncio.sleep(self.delay_s)
        return {"general": f"A calm day for {sign}.", "love": "Be kind.", "career": "Focus.", "wellness": "Rest.",
                "generated_by": "llm"}

    async def generate_compat_narrative(self, report: dict, relationship_type: str) -> dict:
        self._hit("compat")
        return {
            "summary": "A warm match.",
            "categories": {k: {"summary": f"{k} text"} for k in report["categories"]},
            "aspect_interpretations": [{"aspect_key": a["key"], "text": "interp"} for a in report["aspects"]],
            "strengths": ["s1", "s2", "s3"],
            "challenges": ["c1", "c2", "c3"],
        }

    def module(self) -> types.SimpleNamespace:
        return types.SimpleNamespace(
            generate_chat_reply=self.generate_chat_reply,
            stream_chat_reply=self.stream_chat_reply,
            generate_daily_sign=self.generate_daily_sign,
            generate_compat_narrative=self.generate_compat_narrative,
        )


@pytest.fixture
def fake_llm(monkeypatch: pytest.MonkeyPatch) -> FakeLLM:
    f = FakeLLM()
    mod = f.module()
    monkeypatch.setattr(ai, "_module", lambda: mod)
    return f


@pytest.fixture
def redis_client() -> fakeredis.FakeAsyncRedis:
    return fakeredis.FakeAsyncRedis(decode_responses=True)


@pytest_asyncio.fixture(autouse=True)
async def _isolation(redis_client: fakeredis.FakeAsyncRedis, monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[None]:
    async with SessionLocal() as s:
        await s.execute(text(f"TRUNCATE {TABLES} CASCADE"))
        await s.commit()
    cache.set_client(redis_client)
    ratelimit.limiter.reset()
    monkeypatch.setattr(email_service, "outbox", [])
    yield
    await email_service.drain()
    cache.set_client(None)


@pytest_asyncio.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def register(client: AsyncClient, email: str = "asha@example.com", password: str = "correct horse battery",
                   name: str = "Asha", verified: bool = True) -> dict[str, str]:
    r = await client.post("/api/v1/auth/register", json={"email": email, "password": password, "name": name})
    assert r.status_code == 201, r.text
    if verified:
        async with SessionLocal() as s:
            await s.execute(text("UPDATE users SET email_verified = true WHERE email = :e"), {"e": email})
            await s.commit()
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


CHART = {
    "name": "Asha",
    "date_of_birth": "1994-07-21",
    "time_of_birth": "14:05",
    "has_exact_time": True,
    "birth_place_name": "Pune, Maharashtra, India",
    "latitude": 18.5204,
    "longitude": 73.8567,
    "timezone": "Asia/Kolkata",
    "is_primary": True,
}


async def create_chart(client: AsyncClient, headers: dict, **over: Any) -> dict:
    r = await client.post("/api/v1/charts/", json={**CHART, **over}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()
