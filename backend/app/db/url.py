"""Database URL normalisation shared by the app, alembic and scripts (no settings import side effects)."""
from __future__ import annotations

from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

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
