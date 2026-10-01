"""Async engine and session factory (asyncpg). Small pool for Neon free tier."""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.url import prepare_url  # noqa: F401  (re-exported; also used by app.rag.ingest)


_url, _ssl_args = prepare_url(settings.DATABASE_URL)

engine = create_async_engine(
    _url,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=300,
    connect_args={
        "timeout": 10,  # Neon cold start (scale-to-zero) can take a few seconds
        "command_timeout": settings.DB_COMMAND_TIMEOUT_S,
        # Neon's pooled endpoint is pgbouncer in transaction mode: no server-side prepared statements.
        "statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid.uuid4().hex}__",
        **_ssl_args,
    },
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        try:
            yield session
        except BaseException:
            await session.rollback()
            raise
