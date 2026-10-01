"""Liveness (no I/O at all) and readiness (DB + Redis + engine self-test)."""
from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal
from app.services import ai, cache, engine

log = logging.getLogger("app.health")


def live() -> dict[str, str]:
    # MUST NOT touch Postgres or Redis: the keep-awake pinger hits this every 14 min (Neon CU-hours).
    out = {"status": "ok", "version": settings.APP_VERSION}
    if settings.SOURCE_CODE_URL:
        out["source"] = settings.SOURCE_CODE_URL  # AGPL notice (astrology-engine.md 1.1)
    return out


async def _db_ok() -> bool:
    try:
        async with SessionLocal() as s:
            await asyncio.wait_for(s.execute(text("SELECT 1")), timeout=5)
        return True
    except Exception:  # noqa: BLE001
        log.warning("ready_db_failed")
        return False


async def ready() -> tuple[bool, dict[str, bool]]:
    db_ok, redis_ok = await asyncio.gather(_db_ok(), cache.ping())
    engine_ok = engine.last_self_test()  # computed once at startup (lifespan)
    checks = {"database": db_ok, "redis": redis_ok, "engine": engine_ok}
    # RAG is informational: a degraded index only makes chat chart-facts-only, so it never fails readiness.
    return all(checks.values()), {**checks, "rag": ai.rag_status()}
