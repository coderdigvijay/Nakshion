"""In-process sliding-window rate limiter (single Render instance; architecture.md section 7).

Auth brute-force counters (login failures) are Redis-backed in auth_service via cache.counter_*.
"""
from __future__ import annotations

import time
from collections import deque

from app.core.config import settings
from app.core.errors import RateLimited


class SlidingWindowLimiter:
    def __init__(self, max_keys: int = 50_000) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._max_keys = max_keys

    def hit(self, key: str, limit: int, window_s: float) -> float:
        """Record a hit. Returns 0 if allowed, else seconds until a slot frees up (no hit recorded)."""
        now = time.monotonic()
        q = self._hits.get(key)
        if q is None:
            if len(self._hits) >= self._max_keys:
                self._evict(now)
            q = self._hits[key] = deque()
        cutoff = now - window_s
        while q and q[0] <= cutoff:
            q.popleft()
        if len(q) >= limit:
            return max(1.0, q[0] + window_s - now)
        q.append(now)
        return 0.0

    def _evict(self, now: float) -> None:
        # Drop empty / oldest entries; bounded memory on 512 MB instance.
        for k in list(self._hits.keys())[: self._max_keys // 10]:
            self._hits.pop(k, None)

    def reset(self) -> None:
        self._hits.clear()


limiter = SlidingWindowLimiter()


def enforce(scope: str, ident: str, limit: int, window_s: float, detail: str | None = None) -> None:
    """Raise RateLimited (429 + Retry-After) if ``ident`` exceeded ``limit`` per ``window_s`` for ``scope``."""
    if not settings.RATE_LIMIT_ENABLED:
        return
    wait = limiter.hit(f"{scope}:{ident}", limit, window_s)
    if wait:
        raise RateLimited(detail, retry_after=int(wait) + 1)


def check(scope: str, ident: str, limit: int, window_s: float) -> bool:
    """Non-raising variant: True if allowed (and recorded)."""
    if not settings.RATE_LIMIT_ENABLED:
        return True
    return limiter.hit(f"{scope}:{ident}", limit, window_s) == 0.0
