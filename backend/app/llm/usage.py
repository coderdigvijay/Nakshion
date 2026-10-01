"""Usage accounting: one record per provider attempt (llm-integration.md §2 step 5, §11).

Prompt bodies, birth data and user text are never part of a usage record or log line.
backend-elite supplies a sink that writes `llm_usage` rows; the default only logs.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Protocol

from app.llm.config import LLMSettings
from app.llm.types import LLMResult

log = logging.getLogger("nakshion.llm")

Outcome = str  # ok | repaired | fallback | failed | blocked | invalid | timeout | rate_limited


@dataclass(frozen=True)
class UsageRecord:
    request_id: str
    user_id: str | None          # for the llm_usage FK / quota reconciliation; never sent to a provider
    user_id_hash: str | None     # for logs
    task: str
    provider: str
    model: str
    prompt_version: str
    input_tokens: int
    cached_input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    outcome: Outcome
    validator_flags: tuple[str, ...] = field(default_factory=tuple)
    error: str | None = None     # mapped error class + status + redacted provider message (failed attempts)


class UsageSink(Protocol):
    async def record(self, rec: UsageRecord) -> None: ...


class LoggingUsageSink:
    async def record(self, rec: UsageRecord) -> None:
        d = asdict(rec)
        d.pop("user_id", None)  # hash only in logs
        log.info("llm_call", extra={"llm": d})


class MemoryUsageSink:
    def __init__(self) -> None:
        self.records: list[UsageRecord] = []

    async def record(self, rec: UsageRecord) -> None:
        self.records.append(rec)


def cost_usd(settings: LLMSettings, result: LLMResult, on: date | None = None) -> float:
    price_in, price_out = settings.price_for(result.model, on)
    mult = settings.cache_read_multiplier.get(result.provider, 1.0)
    uncached = max(0, result.input_tokens - result.cached_input_tokens - result.cache_write_tokens)
    total = (
        uncached * price_in
        + result.cached_input_tokens * price_in * mult
        + result.cache_write_tokens * price_in * 1.25
        + result.output_tokens * price_out
    )
    return round(total / 1_000_000, 8)
