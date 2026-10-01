"""Shared fixtures for LLM/RAG unit tests. No test here touches a network or a real API."""

from __future__ import annotations

import inspect
import json
import sys
from datetime import date
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[2]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.llm.config import LLMSettings  # noqa: E402

CHARTS = json.loads((BACKEND / "evals" / "fixtures" / "charts.json").read_text(encoding="utf-8"))


@pytest.hookimpl(tryfirst=True)
def pytest_pycollect_makeitem(collector, name, obj):
    """Auto-mark async tests in this directory (no repo-wide asyncio_mode needed)."""
    if inspect.iscoroutinefunction(obj) and name.startswith("test"):
        pytest.mark.asyncio(obj)


@pytest.fixture
def chart():
    return json.loads(json.dumps(CHARTS["known_time_india"]))


@pytest.fixture
def chart_unknown():
    return json.loads(json.dumps(CHARTS["unknown_time"]))


@pytest.fixture
def settings():
    return LLMSettings(
        _env_file=None,
        LLM_MODEL_CHAT="fake-primary", LLM_FALLBACK_CHAT="fake-secondary",
        LLM_MODEL_DAILY="fake-daily", LLM_FALLBACK_DAILY="", rpm_gemini=1000, rpm_anthropic=1000,
        retry_backoff_ms=(0, 0), retry_min_remaining_s=0.5,
    )


TODAY = date(2026, 10, 1)


def chat_json(answer: str, citations: list[str], **kw) -> str:
    return json.dumps({"answer": answer, "citations": citations, "topic": kw.get("topic", "self"),
                       "follow_ups": kw.get("follow_ups", []), "confidence": kw.get("confidence", "medium"),
                       "needs_birth_time": kw.get("needs_birth_time", False)})


GOOD = ("Your tropical Sun in Cancer gives you a protective, caring core, and you tend to lead with feeling. "
        "Your Saturn Mahadasha asks for patience and structure, a period that favours steady, long-term work. "
        "Try writing down one small commitment each week and keeping it.")
