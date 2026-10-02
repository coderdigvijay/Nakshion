"""Liveness (no I/O at all) and readiness (DB + Redis + engine self-test)."""
from __future__ import annotations

import asyncio
import logging
import time

from sqlalchemy import text

from app.core.config import settings
from app.db.session import SessionLocal
from app.services import ai, cache, engine

log = logging.getLogger("app.health")


def live() -> dict[str, str]:
    # MUST NOT touch Postgres or Redis: the keep-awake pinger hits this every 14 min (Neon CU-hours).
    out = {"status": "ok", "version": settings.build_version}
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


_ready_cache: tuple[float, tuple[bool, dict]] | None = None
READY_CACHE_S = 5.0


async def ready() -> tuple[bool, dict]:
    """DB + Redis + engine checks, cached for 5 s so that polling (or abuse) cannot hammer Postgres/Redis."""
    global _ready_cache
    now = time.monotonic()
    if _ready_cache and now - _ready_cache[0] < READY_CACHE_S:
        return _ready_cache[1]
    result = await _ready_uncached()
    _ready_cache = (now, result)
    return result


def reset_ready_cache() -> None:
    global _ready_cache
    _ready_cache = None


async def _ready_uncached() -> tuple[bool, dict]:
    db_ok, redis_ok = await asyncio.gather(_db_ok(), cache.ping())
    engine_ok = engine.last_self_test()  # computed once at startup (lifespan)
    checks = {"database": db_ok, "redis": redis_ok, "engine": engine_ok}
    # RAG is informational: a degraded index only makes chat chart-facts-only, so it never fails readiness.
    return all(checks.values()), {**checks, "rag": ai.rag_status()}
