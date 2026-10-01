"""Internal error types. Raw SDK exceptions never cross an adapter boundary."""

from __future__ import annotations

import re

_SECRET = re.compile(r"(AIza[0-9A-Za-z_\-]{20,}|sk-ant-[0-9A-Za-z_\-]{10,}|key=[^&\s]+)")


def redact(text: str) -> str:
    """Strip anything shaped like an API key from provider error text."""
    return _SECRET.sub("[REDACTED]", text or "")[:400]


class LLMError(Exception):
    """Base. `retryable` drives the router's retry-once rule."""

    retryable: bool = False

    def __init__(self, message: str = "", *, provider: str = "", model: str = "", status: int | None = None,
                 retry_after_s: float | None = None, quota_exhausted: bool = False) -> None:
        super().__init__(redact(message) or self.__class__.__name__)
        self.provider = provider
        self.model = model
        self.status = status
        self.retry_after_s = retry_after_s          # provider's Retry-After / retryDelay, when it sent one
        self.quota_exhausted = quota_exhausted      # per-day/per-project quota: do not retry for a long while

    def summary(self) -> str:
        """Safe one-line description for logs and llm_usage.error (keys redacted, length-capped)."""
        code = f" {self.status}" if self.status else ""
        return f"{type(self).__name__}{code}: {str(self)[:200]}"


class LLMTimeout(LLMError):
    retryable = True


class LLMRateLimited(LLMError):
    retryable = True


class LLMServerError(LLMError):
    """5xx or connection failure at the provider."""

    retryable = True


class LLMBadRequest(LLMError):
    """400/401/403/404: our request or credentials are wrong. Not retried on the same provider."""


class LLMBlocked(LLMError):
    """Provider safety block or refusal. Logged as llm_blocked, not retried."""


class LLMOutputInvalid(LLMError):
    """Structured output failed schema validation (after the one repair)."""


class LLMTruncated(LLMOutputInvalid):
    """finish_reason=length on structured output. Retried once with a larger budget."""


class LLMUnavailable(LLMError):
    """Every provider in the chain failed or the deadline passed. Maps to HTTP 503 AI_UNAVAILABLE."""


class LLMBudgetUnavailable(LLMUnavailable):
    """Global spend guard engaged (llm-integration.md §7.2). Also 503, with the 'resting' copy."""


class QuotaExceeded(Exception):
    """Per-user daily quota reached. Maps to HTTP 429 with a friendly message."""

    def __init__(self, limit: int) -> None:
        super().__init__(f"daily quota of {limit} reached")
        self.limit = limit
