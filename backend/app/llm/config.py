"""LLM/RAG settings. Self-contained so this package does not depend on app.core.config.

Construct directly in tests (`LLMSettings(gemini_api_key=None, ...)`) or from the
environment (`LLMSettings()`); env var names follow llm-integration.md §1.1 / §7.2.
Model IDs are configuration, never literals elsewhere in code.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.llm.types import Task

# Prices: USD per 1M tokens, standard tier (llm-integration.md §1, verified there 2026-10-01).
# Each entry: list of (effective_from ISO date, input, output). cache_read_multiplier per vendor.
DEFAULT_PRICES: dict[str, list[tuple[str, float, float]]] = {
    "gemini-3.8-flash": [("2000-01-01", 0.75, 3.75), ("2027-01-01", 1.50, 7.50)],
    "gemini-3.5-flash-lite": [("2000-01-01", 0.30, 2.50)],
    "gemini-3.1-flash-lite": [("2000-01-01", 0.25, 1.50)],
    "claude-haiku-4-5": [("2000-01-01", 1.00, 5.00)],
    "claude-haiku-4-5-20251001": [("2000-01-01", 1.00, 5.00)],
    "claude-sonnet-5-5": [("2000-01-01", 2.00, 10.00)],
}
# Anthropic cache reads cost 0.1x input (documented). Gemini implicit-cache discount is not
# assumed (1.0) so the spend guard over-estimates rather than under-estimates.
DEFAULT_CACHE_READ_MULTIPLIER: dict[str, float] = {"anthropic": 0.1, "gemini": 1.0, "fake": 1.0}
# Unknown model: charge at the most expensive known rate so the guard fails safe.
UNKNOWN_MODEL_PRICE = (4.00, 20.00)


BACKEND_ENV = Path(__file__).resolve().parents[2] / ".env"


class LLMSettings(BaseSettings):
    # Reads process env first, then backend/.env, so a standalone script needs no os.environ
    # workaround. Tests pass `_env_file=None` to stay hermetic.
    model_config = SettingsConfigDict(env_file=BACKEND_ENV, env_file_encoding="utf-8", extra="ignore",
                                      populate_by_name=True)

    # --- credentials (never logged; SecretStr repr is masked) ---
    # Single key or numbered keys (GEMINI_API_KEY1..5). Numbered keys rotate on 429 inside the adapter.
    gemini_api_key: SecretStr | None = Field(default=None, alias="GEMINI_API_KEY")
    gemini_api_key1: SecretStr | None = Field(default=None, alias="GEMINI_API_KEY1")
    gemini_api_key2: SecretStr | None = Field(default=None, alias="GEMINI_API_KEY2")
    gemini_api_key3: SecretStr | None = Field(default=None, alias="GEMINI_API_KEY3")
    gemini_api_key4: SecretStr | None = Field(default=None, alias="GEMINI_API_KEY4")
    gemini_api_key5: SecretStr | None = Field(default=None, alias="GEMINI_API_KEY5")
    anthropic_api_key: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    anthropic_api_key1: SecretStr | None = Field(default=None, alias="ANTHROPIC_API_KEY1")

    # --- routing (§1.1). Fallbacks are comma-separated model IDs. ---
    model_chat: str = Field(default="gemini-3.8-flash", alias="LLM_MODEL_CHAT")
    # Cross-vendor first (independent outage domain), then a same-vendor lighter model so chat
    # still has a fallback when only Gemini keys are configured (BUG-003).
    fallback_chat: str = Field(default="claude-haiku-4-5,gemini-3.5-flash-lite", alias="LLM_FALLBACK_CHAT")
    model_daily: str = Field(default="gemini-3.5-flash-lite", alias="LLM_MODEL_DAILY")
    fallback_daily: str = Field(default="gemini-3.1-flash-lite", alias="LLM_FALLBACK_DAILY")
    model_premium: str = Field(default="claude-sonnet-5-5", alias="LLM_MODEL_PREMIUM")
    fallback_premium: str = Field(default="gemini-3.8-flash,gemini-3.5-flash-lite", alias="LLM_FALLBACK_PREMIUM")
    model_judge: str = Field(default="claude-sonnet-5-5", alias="LLM_MODEL_JUDGE")

    # --- deadlines / resilience (§2) ---
    chat_deadline_s: float = Field(default=25.0, alias="LLM_CHAT_DEADLINE_S")
    retry_min_remaining_s: float = 8.0
    retry_backoff_ms: tuple[int, int] = (300, 800)
    breaker_failures: int = 5
    breaker_window_s: float = 60.0
    breaker_open_s: float = 60.0
    rate_wait_max_s: float = 2.0
    rpm_gemini: int = Field(default=1000, alias="LLM_RPM_GEMINI")
    rpm_anthropic: int = Field(default=50, alias="LLM_RPM_ANTHROPIC")

    # --- provider knobs ---
    gemini_thinking_level: str | None = Field(default="minimal", alias="LLM_GEMINI_THINKING_LEVEL")
    # Models that still accept `temperature` (sent via extra_body, anthropic SDK 1.x removed the kwarg).
    anthropic_sampling_models: tuple[str, ...] = ("claude-haiku-4-5", "claude-haiku-4-5-20251001")
    # Models that run adaptive thinking (max_tokens must leave room for it) and take `effort`.
    anthropic_thinking_models: dict[str, str] = {"claude-sonnet-5-5": "medium"}
    anthropic_thinking_headroom_tokens: int = 2000

    # --- budgets (§7.2) and per-user quotas (PRD §6.7) ---
    daily_budget_usd: float = Field(default=1.50, alias="LLM_DAILY_BUDGET_USD")
    monthly_budget_usd: float = Field(default=40.00, alias="LLM_MONTHLY_BUDGET_USD")
    quota_chat_free: int = Field(default=5, alias="LLM_QUOTA_CHAT_FREE")
    quota_chat_premium: int = Field(default=60, alias="LLM_QUOTA_CHAT_PREMIUM")
    max_user_message_chars: int = 2000
    max_output_tokens_cap: int = 4096   # ceiling for the truncation retry (cost is bounded by budget guard)

    # --- RAG (§6) ---
    embeddings_runtime: str = Field(default="local", alias="EMBEDDINGS_RUNTIME")  # local | off
    embedding_model: str = Field(default="BAAI/bge-small-en-v1.5", alias="EMBEDDING_MODEL")
    rag_top_k: int = 5
    rag_token_cap: int = 1200
    rag_candidates: int = 20
    # Licence kill-switch: drop retrieval of tier-3 "modern author paraphrase" notes (see app/rag/sources.yaml).
    rag_exclude_review: bool = Field(default=False, alias="RAG_EXCLUDE_REVIEW")
    # Optional local cross-encoder rerank (+0.04 nDCG, +145 MB RAM, +0.5 s on a fast CPU): OFF by default.
    rag_rerank_model: str | None = Field(default=None, alias="RAG_RERANK_MODEL")
    rag_timeout_s: float = Field(default=3.0, alias="RAG_TIMEOUT_S")

    prices: dict[str, list[tuple[str, float, float]]] = DEFAULT_PRICES
    cache_read_multiplier: dict[str, float] = DEFAULT_CACHE_READ_MULTIPLIER

    # ------------------------------------------------------------------ helpers
    def gemini_keys(self) -> list[str]:
        fields = (self.gemini_api_key, self.gemini_api_key1, self.gemini_api_key2, self.gemini_api_key3,
                  self.gemini_api_key4, self.gemini_api_key5)
        return list(dict.fromkeys(k.get_secret_value() for k in fields if k and k.get_secret_value().strip()))

    def anthropic_keys(self) -> list[str]:
        fields = (self.anthropic_api_key, self.anthropic_api_key1)
        return list(dict.fromkeys(k.get_secret_value() for k in fields if k and k.get_secret_value().strip()))

    def chain_for(self, task: Task) -> list[str]:
        """Ordered model IDs for a task: primary first, then cross-vendor fallbacks."""
        primary, fallback = {
            "chat": (self.model_chat, self.fallback_chat),
            "daily_personal": (self.model_daily, self.fallback_daily),
            "daily_sign": (self.model_daily, self.fallback_daily),
            "compat": (self.model_daily, self.fallback_daily),
            "title": (self.model_daily, self.fallback_daily),
            "premium_report": (self.model_premium, self.fallback_premium),
            "judge": (self.model_judge, ""),
        }[task]
        chain = [primary] + [m.strip() for m in fallback.split(",") if m.strip()]
        seen: list[str] = []
        for m in chain:
            if m not in seen:
                seen.append(m)
        return seen

    def price_for(self, model: str, on: date | None = None) -> tuple[float, float]:
        rows = self.prices.get(model)
        if not rows:
            return UNKNOWN_MODEL_PRICE
        day = (on or date.today()).isoformat()
        current = rows[0]
        for row in rows:
            if row[0] <= day:
                current = row
        return current[1], current[2]


def provider_for_model(model: str) -> str:
    """Vendor is inferred from the model ID prefix, so env vars stay plain model IDs."""
    if model.startswith("gemini-"):
        return "gemini"
    if model.startswith("claude-"):
        return "anthropic"
    if model.startswith("fake"):
        return "fake"
    raise ValueError(f"cannot infer provider for model id {model!r}")
