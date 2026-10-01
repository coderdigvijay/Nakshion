"""Spend guard (llm-integration.md §7.2) and per-user quotas (PRD §6.7).

Counters are atomic (Redis INCRBY inside MULTI with EXPIRE), never read-then-write.
Quota/budget checks fail CLOSED (PITFALLS #7): a counter error means no LLM call.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any, Literal, Protocol

from app.llm.config import LLMSettings
from app.llm.errors import LLMBudgetUnavailable, QuotaExceeded
from app.llm.types import Task

log = logging.getLogger("nakshion.llm.budget")

Tier = Literal["free", "premium"]
MICRO = 1_000_000


class Counter(Protocol):
    async def incr(self, key: str, amount: int, ttl_s: int) -> int: ...
    async def get(self, key: str) -> int: ...


class MemoryCounter:
    """Tests and single-process dev. Atomic under the event loop via a lock."""

    def __init__(self) -> None:
        self._d: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def incr(self, key: str, amount: int, ttl_s: int) -> int:
        async with self._lock:
            self._d[key] = self._d.get(key, 0) + amount
            return self._d[key]

    async def get(self, key: str) -> int:
        return self._d.get(key, 0)


class RedisCounter:
    """`redis.asyncio.Redis` (Upstash). INCRBY + EXPIRE NX in one MULTI transaction."""

    def __init__(self, redis: Any) -> None:
        self._r = redis

    async def incr(self, key: str, amount: int, ttl_s: int) -> int:
        async with self._r.pipeline(transaction=True) as pipe:
            pipe.incrby(key, amount)
            pipe.expire(key, ttl_s, nx=True)
            value, _ = await pipe.execute()
        return int(value)

    async def get(self, key: str) -> int:
        v = await self._r.get(key)
        return int(v or 0)


@dataclass(frozen=True)
class BudgetDecision:
    task: Task
    max_output_tokens: int | None = None   # lowered cap when degraded
    use_daily_models: bool = False         # free chat drops to daily-class models at 100 %
    level: str = "normal"                  # normal | alert | degraded


class BudgetGuard:
    def __init__(self, settings: LLMSettings, counter: Counter, *, today: callable = None) -> None:
        self._s = settings
        self._c = counter
        self._today = today or (lambda: datetime.now(timezone.utc).date())
        self._alerted_for: date | None = None

    def _keys(self) -> tuple[str, str]:
        d = self._today()
        return f"llm_spend:{d.isoformat()}", f"llm_spend_m:{d.strftime('%Y-%m')}"

    async def ratio(self) -> float:
        dk, mk = self._keys()
        daily, monthly = await asyncio.gather(self._c.get(dk), self._c.get(mk))
        return max(
            daily / (self._s.daily_budget_usd * MICRO) if self._s.daily_budget_usd > 0 else 0.0,
            monthly / (self._s.monthly_budget_usd * MICRO) if self._s.monthly_budget_usd > 0 else 0.0,
        )

    async def admit(self, task: Task, tier: Tier = "free") -> BudgetDecision:
        try:
            r = await self.ratio()
        except Exception:  # noqa: BLE001 - fail closed
            log.exception("budget counter unavailable; failing closed")
            raise LLMBudgetUnavailable("budget counter unavailable") from None
        if r >= 0.8 and self._alerted_for != self._today():
            self._alerted_for = self._today()
            log.warning("llm_budget_alert", extra={"ratio": round(r, 3)})
        if r >= 1.5:
            raise LLMBudgetUnavailable("spend guard: all generation paused")
        if r >= 1.0:
            if tier == "premium" or task in ("judge", "title"):
                return BudgetDecision(task=task, level="degraded")
            if task == "chat":
                return BudgetDecision(task=task, max_output_tokens=400, use_daily_models=True, level="degraded")
            raise LLMBudgetUnavailable("spend guard: free generation uses templates")
        return BudgetDecision(task=task, level="alert" if r >= 0.8 else "normal")

    async def record(self, cost_usd: float) -> None:
        amount = int(round(cost_usd * MICRO))
        if amount <= 0:
            return
        dk, mk = self._keys()
        try:
            await self._c.incr(dk, amount, ttl_s=3 * 86400)
            await self._c.incr(mk, amount, ttl_s=40 * 86400)
        except Exception:  # noqa: BLE001 - spend already happened; log, do not fail the reply
            log.exception("failed to record llm spend")


class UserQuota:
    """Chat replies per user per user-local day. Reserve before the call, release on failure
    (PRD: a failed reply consumes no quota)."""

    def __init__(self, settings: LLMSettings, counter: Counter) -> None:
        self._s = settings
        self._c = counter

    def limit(self, tier: Tier) -> int:
        return self._s.quota_chat_premium if tier == "premium" else self._s.quota_chat_free

    @staticmethod
    def _key(user_id: str, local_date: date) -> str:
        return f"llmq:chat:{user_id}:{local_date.isoformat()}"

    async def reserve(self, user_id: str, tier: Tier, local_date: date) -> int:
        key = self._key(user_id, local_date)
        try:
            used = await self._c.incr(key, 1, ttl_s=36 * 3600)
        except Exception:  # noqa: BLE001 - fail closed
            log.exception("quota counter unavailable; failing closed")
            raise LLMBudgetUnavailable("quota counter unavailable") from None
        if used > self.limit(tier):
            await self._c.incr(key, -1, ttl_s=36 * 3600)
            raise QuotaExceeded(self.limit(tier))
        return used

    async def release(self, user_id: str, local_date: date) -> None:
        try:
            await self._c.incr(self._key(user_id, local_date), -1, ttl_s=36 * 3600)
        except Exception:  # noqa: BLE001
            log.exception("failed to release quota")
