"""Compatibility shim: alembic/env.py imports ``app.database.Base``. Canonical code is in app.db."""
from app.db.base import Base  # noqa: F401

__all__ = ["Base"]
