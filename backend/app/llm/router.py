"""LLMRouter: per-task model chain, deadline, retry-once, circuit breaker, client-side RPM,
structured-output validation with one repair, and a usage record per attempt.

llm-integration.md §2. Nothing outside app/llm/providers imports a vendor SDK.
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
import uuid
from typing import AsyncIterator, Callable

from pydantic import BaseModel, ValidationError

from app.llm.budget import BudgetGuard
from app.llm.config import LLMSettings, provider_for_model
from app.llm.errors import (
    LLMBlocked,
    LLMError,
    LLMOutputInvalid,
    LLMRateLimited,
    LLMServerError,
    LLMTimeout,
    LLMTruncated,
    LLMUnavailable,
)
from app.llm.providers.base import LLMProvider
from app.llm.resilience import CircuitBreaker, TokenBucket
from app.llm.types import LLMChunk, LLMRequest, LLMResult
from app.llm.usage import LoggingUsageSink, UsageRecord, UsageSink, cost_usd

log = logging.getLogger("nakshion.llm.router")

REPAIR_SCHEMA_NOTE = (
    "Your previous reply was not valid JSON for the required schema. Error: {error}\n"
    "Reply again with ONLY a JSON object that matches the schema."
)


def _retry_same_model(exc: LLMError) -> bool:
    """Same-model retry only for transient network errors, timeouts and a 429 that clears almost at once.
    A 5xx with a status (503 "high demand") or a 429 with a real wait is a capacity/quota problem: go
    straight to the next model and put this one on cooldown."""
    if not exc.retryable:
        return False
    if isinstance(exc, LLMServerError) and exc.status is not None:
        return False
    if isinstance(exc, LLMRateLimited):
        return (not exc.quota_exhausted) and exc.retry_after_s is not None and exc.retry_after_s <= 1.5
    return True


DEFAULT_429_COOLDOWN_S = 30.0
DAILY_QUOTA_COOLDOWN_S = 600.0
MAX_COOLDOWN_S = 3600.0
SERVER_ERROR_COOLDOWN_S = 30.0


def _outcome_for(exc: Exception) -> str:
    if isinstance(exc, LLMBlocked):
        return "blocked"
    if isinstance(exc, LLMTimeout):
        return "timeout"
    if isinstance(exc, LLMRateLimited):
        return "rate_limited"
    if isinstance(exc, LLMOutputInvalid):
        return "invalid"
    return "failed"


def parse_json_object(text: str) -> dict:
    """Tolerates a ```json fence; nothing else. Raises ValueError."""
    t = text.strip()
    if t.startswith("```"):
        t = t.strip("`")
        t = t[4:] if t.lower().startswith("json") else t
    obj = json.loads(t)
    if not isinstance(obj, dict):
        raise ValueError("top-level JSON is not an object")
    return obj


class LLMRouter:
    def __init__(
        self,
        settings: LLMSettings,
        providers: dict[str, LLMProvider],
        *,
        usage_sink: UsageSink | None = None,
        budget: BudgetGuard | None = None,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], "asyncio.Future"] = asyncio.sleep,
    ) -> None:
        self.s = settings
        self.providers = providers
        self.usage = usage_sink or LoggingUsageSink()
        self.budget = budget
        self._clock = clock
        self._sleep = sleep
        self._breakers: dict[str, CircuitBreaker] = {}
        self._cooldown_streak: dict[str, int] = {}   # consecutive capacity failures: cooldown doubles, reset on success
        self._cooldown: dict[str, float] = {}        # "provider:model" -> monotonic time it may be tried again
        self._buckets: dict[tuple[str, str], TokenBucket] = {}

    # ------------------------------------------------------------------ helpers
    def breaker(self, key: str) -> CircuitBreaker:
        """Keyed by "provider:model": a capacity outage on one model (e.g. a 503 'high demand'
        on gemini-3.8-flash) must not block a sibling model on the same vendor (BUG-003)."""
        if key not in self._breakers:
            self._breakers[key] = CircuitBreaker(
                self.s.breaker_failures, self.s.breaker_window_s, self.s.breaker_open_s, clock=self._clock
            )
        return self._breakers[key]

    def cooldown_active(self, key: str) -> float:
        """Seconds left on a model's cooldown (0 when usable)."""
        return max(0.0, self._cooldown.get(key, 0.0) - self._clock())

    def _start_cooldown(self, key: str, exc: LLMError) -> None:
        if isinstance(exc, LLMRateLimited):
            secs = exc.retry_after_s if exc.retry_after_s is not None else DEFAULT_429_COOLDOWN_S
            if exc.quota_exhausted:
                secs = max(secs, DAILY_QUOTA_COOLDOWN_S)
        elif isinstance(exc, LLMServerError) and exc.status is not None:
            secs = SERVER_ERROR_COOLDOWN_S
        else:
            return
        n = self._cooldown_streak.get(key, 0)
        self._cooldown_streak[key] = n + 1
        secs = min(secs * (2 ** min(n, 4)), MAX_COOLDOWN_S)   # 20 s, 40 s, 80 s ... a flapping model stops costing TTFT
        self._cooldown[key] = self._clock() + secs
        log.info("llm_cooldown", extra={"model": key, "seconds": round(secs, 1), "reason": type(exc).__name__})

    def _bucket(self, provider: str, model: str) -> TokenBucket:
        key = (provider, model)
        if key not in self._buckets:
            rpm = {"gemini": self.s.rpm_gemini, "anthropic": self.s.rpm_anthropic}.get(provider, 10_000)
            self._buckets[key] = TokenBucket(rpm, clock=self._clock)
        return self._buckets[key]

    def chain(self, req: LLMRequest, models: list[str] | None = None) -> list[tuple[str, str]]:
        wanted = models or self.s.chain_for(req.task)
        out = [(provider_for_model(m), m) for m in wanted if provider_for_model(m) in self.providers]
        if not out:
            msg = (f"no LLM provider configured for task {req.task} (models {wanted}; configured providers "
                   f"{sorted(self.providers) or 'none'}). Set GEMINI_API_KEY / GEMINI_API_KEY1..5 or ANTHROPIC_API_KEY.")
            log.error("llm_no_provider", extra={"task": req.task, "models": wanted})
            raise LLMUnavailable(msg)
        return out

    def _usable(self, chain: list[tuple[str, str]]) -> tuple[list[tuple[str, str]], bool]:
        """Models off cooldown; when EVERY model is cooling down, try the one that frees up first instead of failing
        the request outright (a cooldown is a hint, not a ban). -> (chain, forced)."""
        ok = [c for c in chain if self.cooldown_active(f"{c[0]}:{c[1]}") <= 0]
        if ok:
            return ok, False
        best = min(chain, key=lambda c: self.cooldown_active(f"{c[0]}:{c[1]}"))
        log.info("llm_all_cooling_down", extra={"forcing": best[1]})
        return [best], True

    async def _record(self, req: LLMRequest, result: LLMResult | None, provider: str, model: str,
                      outcome: str, latency_ms: int, flags: tuple[str, ...] = (),
                      error: Exception | None = None) -> float:
        cost = cost_usd(self.s, result) if result is not None else 0.0
        md = req.metadata
        rec = UsageRecord(
            request_id=md.get("request_id") or uuid.uuid4().hex,
            user_id=md.get("user_id"), user_id_hash=md.get("user_id_hash"),
            task=req.task, provider=provider, model=result.model if result else model,
            prompt_version=req.prompt_id,
            input_tokens=result.input_tokens if result else 0,
            cached_input_tokens=result.cached_input_tokens if result else 0,
            output_tokens=result.output_tokens if result else 0,
            cost_usd=cost, latency_ms=latency_ms, outcome=outcome, validator_flags=flags,
            error=error.summary() if isinstance(error, LLMError) else (type(error).__name__ if error else None),
        )
        if error is not None:
            # Never logs prompt bodies, user text or keys: only the mapped, redacted summary.
            log.warning("llm_attempt_failed", extra={
                "task": req.task, "provider": provider, "model": model, "outcome": outcome,
                "error": rec.error, "latency_ms": latency_ms, "request_id": rec.request_id})
        try:
            await self.usage.record(rec)
        except Exception:  # noqa: BLE001 - accounting must not break a reply
            log.exception("usage sink failed")
        if self.budget is not None and cost > 0:
            await self.budget.record(cost)
        return cost

    async def _call_once(self, provider: LLMProvider, req: LLMRequest, model: str, timeout: float) -> LLMResult:
        try:
            async with asyncio.timeout(timeout):
                return await provider.generate(req.with_(timeout_s=timeout), model)
        except TimeoutError:
            raise LLMTimeout("deadline", provider=provider.name, model=model) from None

    @staticmethod
    def _validate(result: LLMResult, schema: type[BaseModel]) -> LLMResult:
        if result.finish_reason == "length":
            raise LLMTruncated("truncated structured output (finish_reason=length)",
                               provider=result.provider, model=result.model)
        try:
            obj = schema.model_validate(parse_json_object(result.text))
        except (ValueError, ValidationError) as exc:
            err = LLMOutputInvalid(str(exc)[:300], provider=result.provider, model=result.model)
            raise err from None
        from dataclasses import replace

        return replace(result, parsed=obj.model_dump())

    # ------------------------------------------------------------------ generate
    async def generate(
        self,
        req: LLMRequest,
        *,
        schema: type[BaseModel] | None = None,
        deadline_s: float | None = None,
        models: list[str] | None = None,
    ) -> LLMResult:
        """Walk the chain until one provider returns a (schema-valid) result."""
        start = self._clock()
        deadline = start + (deadline_s or self.s.chat_deadline_s)
        chain, forced = self._usable(self.chain(req, models))
        last_exc: Exception | None = None
        for pname, model in chain:
            provider = self.providers[pname]
            br = self.breaker(f"{pname}:{model}")
            if not forced and self.cooldown_active(f"{pname}:{model}") > 0:
                log.info("llm_cooldown_skip", extra={"provider": pname, "model": model})
                continue
            if not br.allow():
                log.info("llm_breaker_open", extra={"provider": pname, "model": model})
                continue
            if not await self._bucket(pname, model).acquire(self.s.rate_wait_max_s):
                await self._record(req, None, pname, model, "rate_limited", 0)
                continue
            attempt_req = req
            retried = repaired = grown = False
            while True:
                remaining = deadline - self._clock()
                if remaining <= 1.0:
                    raise LLMUnavailable("deadline exhausted") from last_exc
                timeout = min(req.timeout_s, remaining - 1.0)
                t0 = self._clock()
                try:
                    result = await self._call_once(provider, attempt_req, model, timeout)
                    latency = int((self._clock() - t0) * 1000)
                    if schema is not None:
                        try:
                            result = self._validate(result, schema)
                        except LLMTruncated as exc:
                            # Not a content error: the budget was too small. Retry once, same prompt,
                            # with a larger output budget (thinking tokens share the cap on Gemini).
                            await self._record(req, result, pname, model, "truncated", latency, error=exc)
                            if grown:
                                raise
                            grown = True
                            bigger = min(self.s.max_output_tokens_cap, int(attempt_req.max_output_tokens * 2))
                            if bigger <= attempt_req.max_output_tokens:
                                raise
                            attempt_req = attempt_req.with_(max_output_tokens=bigger)
                            continue
                        except LLMOutputInvalid as exc:
                            await self._record(req, result, pname, model, "invalid", latency, error=exc)
                            if repaired:
                                raise
                            repaired = True
                            attempt_req = attempt_req.with_(messages=attempt_req.messages + (
                                {"role": "assistant", "content": result.text[:4000] or "(empty)"},
                                {"role": "user", "content": REPAIR_SCHEMA_NOTE.format(error=str(exc)[:300])},
                            ))
                            continue
                    br.record_success()
                    self._cooldown_streak.pop(f"{pname}:{model}", None)
                    await self._record(req, result, pname, model, "repaired" if repaired else "ok", latency)
                    return result
                except LLMError as exc:
                    last_exc = exc
                    if not isinstance(exc, LLMOutputInvalid):
                        await self._record(req, None, pname, model, _outcome_for(exc),
                                           int((self._clock() - t0) * 1000), error=exc)
                    if isinstance(exc, LLMBlocked):
                        log.warning("llm_blocked", extra={"provider": pname, "model": model, "task": req.task})
                    if exc.retryable:
                        br.record_failure()
                    if (_retry_same_model(exc) and not retried
                            and deadline - self._clock() > self.s.retry_min_remaining_s):
                        retried = True
                        lo, hi = self.s.retry_backoff_ms
                        wait = random.uniform(lo, hi) / 1000.0
                        if isinstance(exc, LLMRateLimited) and exc.retry_after_s:
                            wait = max(wait, exc.retry_after_s)       # honour Retry-After (<= 1.5 s here)
                        await self._sleep(wait)
                        continue
                    self._start_cooldown(f"{pname}:{model}", exc)
                    break  # next provider
        log.warning("llm_unavailable", extra={"task": req.task, "chain": [m for _, m in chain],
                                              "last_error": last_exc.summary() if isinstance(last_exc, LLMError) else None})
        raise LLMUnavailable("all providers failed: " + (last_exc.summary() if isinstance(last_exc, LLMError)
                                                         else "breakers open or rate limited")) from last_exc

    # ------------------------------------------------------------------ stream
    async def stream(
        self,
        req: LLMRequest,
        *,
        first_token_timeout_s: float | None = None,
        deadline_s: float | None = None,
        models: list[str] | None = None,
    ) -> AsyncIterator[LLMChunk]:
        """Fall over between providers only BEFORE the first text chunk. After that a failure
        propagates (the caller's documented partial-message rule applies)."""
        deadline = self._clock() + (deadline_s or self.s.chat_deadline_s)
        ftt = first_token_timeout_s or req.timeout_s
        chain, forced = self._usable(self.chain(req, models))
        last_exc: Exception | None = None
        for pname, model in chain:
            provider = self.providers[pname]
            br = self.breaker(f"{pname}:{model}")
            if not forced and self.cooldown_active(f"{pname}:{model}") > 0:
                continue
            if not br.allow() or not await self._bucket(pname, model).acquire(self.s.rate_wait_max_s):
                continue
            t0 = self._clock()
            agen = provider.stream(req, model).__aiter__()
            emitted = False
            try:
                while True:
                    remaining = deadline - self._clock()
                    if remaining <= 0:
                        raise LLMTimeout("stream deadline", provider=pname, model=model)
                    wait = min(remaining, ftt) if not emitted else remaining
                    try:
                        async with asyncio.timeout(wait):
                            chunk = await agen.__anext__()
                    except StopAsyncIteration:
                        break
                    except TimeoutError:
                        raise LLMTimeout("stream timeout", provider=pname, model=model) from None
                    if chunk.final is not None:
                        br.record_success()
                        self._cooldown_streak.pop(f"{pname}:{model}", None)
                        await self._record(req, chunk.final, pname, model, "ok",
                                           int((self._clock() - t0) * 1000))
                    if chunk.text:
                        emitted = True
                    yield chunk
                return
            except LLMError as exc:
                last_exc = exc
                if exc.retryable:
                    br.record_failure()
                self._start_cooldown(f"{pname}:{model}", exc)
                await self._record(req, None, pname, model, _outcome_for(exc), int((self._clock() - t0) * 1000),
                                   error=exc)
                if emitted:
                    raise LLMUnavailable("stream failed after first token") from exc
            finally:
                # Cancels the upstream HTTP stream on client disconnect (GeneratorExit/CancelledError).
                await agen.aclose()
        log.warning("llm_unavailable", extra={"task": req.task, "chain": [m for _, m in chain], "stream": True,
                                              "last_error": last_exc.summary() if isinstance(last_exc, LLMError) else None})
        raise LLMUnavailable("all providers failed: " + (last_exc.summary() if isinstance(last_exc, LLMError)
                                                         else "breakers open or rate limited")) from last_exc
