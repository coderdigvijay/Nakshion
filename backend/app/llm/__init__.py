"""Nakshion LLM layer: provider abstraction, routing, prompts, grounding, budgets, safety.

The model narrates; it never calculates. Positions come from the engine (chart_data /
Factors); RAG supplies reference text; CHART FACTS always win.
"""

from app.llm.errors import (
    LLMBlocked,
    LLMBudgetUnavailable,
    LLMError,
    LLMOutputInvalid,
    LLMRateLimited,
    LLMTimeout,
    LLMUnavailable,
    QuotaExceeded,
)
from app.llm.service import (
    configure,
    generate_chat_reply,
    generate_compat_narrative,
    generate_daily_personal,
    generate_daily_sign,
    get_service,
    stream_chat_reply,
)

__all__ = [
    "configure", "get_service", "generate_chat_reply", "stream_chat_reply", "generate_daily_sign",
    "generate_compat_narrative", "generate_daily_personal", "LLMError", "LLMUnavailable", "LLMBudgetUnavailable", "LLMTimeout",
    "LLMRateLimited", "LLMBlocked", "LLMOutputInvalid", "QuotaExceeded",
]
