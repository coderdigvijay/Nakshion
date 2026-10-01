"""In-process circuit breaker and token bucket (one Render instance, llm-integration.md §2)."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Callable

Clock = Callable[[], float]


class CircuitBreaker:
    """Opens after `failures` failures within `window_s`; stays open `open_s`; half-open admits one probe."""

    def __init__(self, failures: int = 5, window_s: float = 60.0, open_s: float = 60.0, clock: Clock = time.monotonic):
        self._max = failures
        self._window = window_s
        self._open_s = open_s
        self._clock = clock
        self._fails: deque[float] = deque()
        self._opened_at: float | None = None
        self._probe_in_flight = False

    @property
    def state(self) -> str:
        if self._opened_at is None:
            return "closed"
        if self._clock() - self._opened_at >= self._open_s:
            return "half_open"
        return "open"

    def allow(self) -> bool:
        st = self.state
        if st == "closed":
            return True
        if st == "half_open" and not self._probe_in_flight:
            self._probe_in_flight = True
            return True
        return False

    def record_success(self) -> None:
        self._fails.clear()
        self._opened_at = None
        self._probe_in_flight = False

    def record_failure(self) -> None:
        now = self._clock()
        if self.state == "half_open":
            self._opened_at = now
            self._probe_in_flight = False
            return
        self._fails.append(now)
        while self._fails and now - self._fails[0] > self._window:
            self._fails.popleft()
        if len(self._fails) >= self._max:
            self._opened_at = now
            self._fails.clear()


class TokenBucket:
    """Client-side RPM limiter. `acquire` waits up to `max_wait_s`, then returns False (fall over)."""

    def __init__(self, rpm: int, clock: Clock = time.monotonic):
        self._capacity = max(1, rpm)
        self._tokens = float(self._capacity)
        self._rate = self._capacity / 60.0
        self._clock = clock
        self._last = clock()
        self._lock = asyncio.Lock()

    def _refill(self) -> None:
        now = self._clock()
        self._tokens = min(self._capacity, self._tokens + (now - self._last) * self._rate)
        self._last = now

    async def acquire(self, max_wait_s: float = 2.0) -> bool:
        async with self._lock:
            self._refill()
            if self._tokens >= 1:
                self._tokens -= 1
                return True
            wait = (1 - self._tokens) / self._rate
            if wait > max_wait_s:
                return False
            await asyncio.sleep(wait)
            self._refill()
            if self._tokens >= 1:
                self._tokens -= 1
                return True
            return False
