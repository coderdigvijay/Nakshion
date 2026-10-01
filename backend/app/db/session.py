"""Async engine and session factory (asyncpg). Small pool for Neon free tier."""
from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings


_DROPPED_QUERY = {"sslmode", "channel_binding", "ssl", "gssencmode", "target_session_attrs"}


def prepare_url(url: str) -> tuple[str, dict[str, Any]]:
    """Normalise a DATABASE_URL for SQLAlchemy+asyncpg.

    Neon URLs carry libpq-only query params (``sslmode``, ``channel_binding``) that asyncpg rejects as
    unknown kwargs. They are stripped here and translated: sslmode=require/verify-* -> ssl="require".
    Returns (clean_url, extra_connect_args)."""
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://"):]
    elif url.startswith("postgres://"):
        url = "postgresql+asyncpg://" + url[len("postgres://"):]
    parts = urlsplit(url)
    query = parse_qsl(parts.query, keep_blank_values=True)
    sslmode = next((v for k, v in query if k == "sslmode"), None)
    ssl_param = next((v for k, v in query if k == "ssl"), None)
    kept = [(k, v) for k, v in query if k not in _DROPPED_QUERY]
    extra: dict[str, Any] = {}
    wants_ssl = (sslmode or ssl_param or "").lower() in {"require", "verify-ca", "verify-full", "true", "1"}
    if wants_ssl:
        extra["ssl"] = "require"
    return urlunsplit(parts._replace(query=urlencode(kept))), extra


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
