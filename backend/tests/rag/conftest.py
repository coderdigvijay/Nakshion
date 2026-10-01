"""RAG tests. No network, no database by default. DB-backed tests use RAG_EVAL_DATABASE_URL, which must point at
a database whose name contains 'scratch' (never astroai_test, never astroai)."""

from __future__ import annotations

import inspect
import os
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))


@pytest.hookimpl(tryfirst=True)
def pytest_pycollect_makeitem(collector, name, obj):
    if inspect.iscoroutinefunction(obj) and name.startswith("test"):
        pytest.mark.asyncio(obj)


def scratch_db_url() -> str | None:
    url = os.environ.get("RAG_EVAL_DATABASE_URL")
    if url and "scratch" not in url.rsplit("/", 1)[1]:
        raise RuntimeError("RAG_EVAL_DATABASE_URL must name a *scratch* database")
    return url


@pytest.fixture(scope="session")
def kb_dir() -> Path:
    return BACKEND / "knowledge_base"
