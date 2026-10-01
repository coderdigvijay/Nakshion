"""The only module that talks to Redis.

Key registry: architecture.md section 6 (mirrored in .claude/caching_rules.md).
- Cache reads/writes FAIL OPEN (miss + WARNING log).
- Security state (OTP, OAuth state) uses the ``secure_*`` helpers, which FAIL CLOSED
  (raise UpstreamUnavailable -> 503 DEPENDENCY_UNAVAILABLE).
- Locks fail open to an in-process lock (single Render instance).
- A small in-process L1 TTL cache fronts hot immutable keys (horoscope:*, transits:{date}).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import OrderedDict
from typing import Any

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from app.core.config import settings
from app.core.errors import UpstreamUnavailable

log = logging.getLogger("app.cache")

_client: aioredis.Redis | None = None


def get_client() -> aioredis.Redis:
    global _client
    if _client is None:
        _client = aioredis.from_url(
            settings.REDIS_URL,
            socket_timeout=1.0,
            socket_connect_timeout=1.0,
            decode_responses=True,
            health_check_interval=30,
        )
    return _client


def set_client(client: aioredis.Redis | None) -> None:
    """Test hook: inject fakeredis (or None to reset)."""
    global _client
    _client = client
    _l1.clear()


async def close() -> None:
    global _client
    if _client is not None:
        try:
            await _client.aclose()
        except Exception:  # noqa: BLE001 - shutdown best effort
            pass
        _client = None


# ---------------------------------------------------------------- L1 in-process cache
class _TTLCache:
    def __init__(self, maxsize: int = 5000) -> None:
        self._d: OrderedDict[str, tuple[float, Any]] = OrderedDict()
        self.maxsize = maxsize

    def get(self, key: str) -> Any | None:
        item = self._d.get(key)
        if item is None:
            return None
        exp, val = item
        if exp < time.monotonic():
            self._d.pop(key, None)
            return None
        self._d.move_to_end(key)
        return val

    def set(self, key: str, val: Any, ttl: float) -> None:
        self._d[key] = (time.monotonic() + ttl, val)
        self._d.move_to_end(key)
        while len(self._d) > self.maxsize:
            self._d.popitem(last=False)

    def delete(self, key: str) -> None:
        self._d.pop(key, None)

    def clear(self) -> None:
        self._d.clear()


_l1 = _TTLCache()
_L1_PREFIXES = ("horoscope:", "transits:20", "transits:19")  # date-keyed, immutable values
_L1_MAX_TTL = 3600.0


def _l1_eligible(key: str) -> bool:
    return key.startswith(_L1_PREFIXES)


# ---------------------------------------------------------------- fail-open cache
async def get_json(key: str) -> Any | None:
    if _l1_eligible(key):
        hit = _l1.get(key)
        if hit is not None:
            return hit
    try:
        raw = await get_client().get(key)
    except (RedisError, OSError, asyncio.TimeoutError) as exc:
        log.warning("cache_read_failed", extra={"key_prefix": key.split(":", 1)[0], "err": type(exc).__name__})
        return None
    if raw is None:
        return None
    try:
        val = json.loads(raw)
    except ValueError:
        return None
    if _l1_eligible(key):
        _l1.set(key, val, _L1_MAX_TTL)
    return val


async def set_json(key: str, value: Any, ttl_s: int) -> None:
    if ttl_s <= 0:
        return
    if _l1_eligible(key):
        _l1.set(key, value, min(float(ttl_s), _L1_MAX_TTL))
    try:
        await get_client().set(key, json.dumps(value, default=str, separators=(",", ":")), ex=int(ttl_s))
    except (RedisError, OSError, asyncio.TimeoutError) as exc:
        log.warning("cache_write_failed", extra={"key_prefix": key.split(":", 1)[0], "err": type(exc).__name__})


async def delete(*keys: str) -> None:
    if not keys:
        return
    for k in keys:
        _l1.delete(k)
    try:
        await get_client().delete(*keys)
    except (RedisError, OSError, asyncio.TimeoutError) as exc:
        log.warning("cache_invalidate_failed", extra={"err": type(exc).__name__, "n": len(keys)})


async def delete_pattern(pattern: str, *, max_keys: int = 2000) -> int:
    """SCAN + DELETE (bounded). Used for per-user purges and per-chart wildcard invalidation."""
    deleted = 0
    try:
        client = get_client()
        batch: list[str] = []
        async for key in client.scan_iter(match=pattern, count=200):
            batch.append(key)
            if len(batch) >= 200:
                deleted += await client.delete(*batch)
                batch.clear()
            if deleted + len(batch) >= max_keys:
                break
        if batch:
            deleted += await client.delete(*batch)
    except (RedisError, OSError, asyncio.TimeoutError) as exc:
        log.warning("cache_pattern_invalidate_failed", extra={"err": type(exc).__name__})
    return deleted


# ---------------------------------------------------------------- fail-closed security state
async def secure_set_json(key: str, value: Any, ttl_s: int) -> None:
    try:
        await get_client().set(key, json.dumps(value, separators=(",", ":")), ex=int(ttl_s))
    except (RedisError, OSError, asyncio.TimeoutError) as exc:
        log.error("secure_state_write_failed", extra={"key_prefix": key.split(":", 1)[0], "err": type(exc).__name__})
        raise UpstreamUnavailable() from exc


async def secure_get_json(key: str) -> Any | None:
    try:
        raw = await get_client().get(key)
    except (RedisError, OSError, asyncio.TimeoutError) as exc:
        log.error("secure_state_read_failed", extra={"key_prefix": key.split(":", 1)[0], "err": type(exc).__name__})
        raise UpstreamUnavailable() from exc
    return json.loads(raw) if raw else None


async def secure_pop_json(key: str) -> Any | None:
    """Atomically read-and-delete (single use: OAuth state)."""
    try:
        raw = await get_client().getdel(key)
    except (RedisError, OSError, asyncio.TimeoutError) as exc:
        log.error("secure_state_read_failed", extra={"key_prefix": key.split(":", 1)[0], "err": type(exc).__name__})
        raise UpstreamUnavailable() from exc
    return json.loads(raw) if raw else None


async def secure_delete(key: str) -> None:
    try:
        await get_client().delete(key)
    except (RedisError, OSError, asyncio.TimeoutError) as exc:
        raise UpstreamUnavailable() from exc


async def secure_ttl(key: str) -> int:
    try:
        return int(await get_client().ttl(key))
    except (RedisError, OSError, asyncio.TimeoutError) as exc:
        raise UpstreamUnavailable() from exc


async def counter_incr(key: str, window_s: int) -> int:
    """Fixed-window counter; FAILS CLOSED (raises) because it guards quotas/brute force."""
    try:
        # Plain pipeline (no MULTI/EXEC): INCR + EXPIRE NX = 2 billed commands instead of 4.
        pipe = get_client().pipeline(transaction=False)
        pipe.incr(key)
        pipe.expire(key, window_s, nx=True)
        res = await pipe.execute()
        return int(res[0])
    except (RedisError, OSError, asyncio.TimeoutError) as exc:
        log.error("counter_failed", extra={"key_prefix": key.split(":", 1)[0], "err": type(exc).__name__})
        raise UpstreamUnavailable() from exc


async def counters_get(*keys: str) -> list[int]:
    """MGET several counters in one command (fail-closed)."""
    try:
        vals = await get_client().mget(*keys)
    except (RedisError, OSError, asyncio.TimeoutError) as exc:
        raise UpstreamUnavailable() from exc
    return [int(v or 0) for v in vals]


async def counter_get(key: str) -> int:
    try:
        v = await get_client().get(key)
    except (RedisError, OSError, asyncio.TimeoutError) as exc:
        raise UpstreamUnavailable() from exc
    return int(v or 0)


# ---------------------------------------------------------------- locks (fail open to in-process)
_local_locks: dict[str, float] = {}


async def acquire_lock(key: str, ttl_s: int) -> bool:
    try:
        return bool(await get_client().set(key, "1", nx=True, ex=ttl_s))
    except (RedisError, OSError, asyncio.TimeoutError) as exc:
        log.warning("lock_redis_unavailable_fallback_local", extra={"err": type(exc).__name__})
        now = time.monotonic()
        exp = _local_locks.get(key)
        if exp and exp > now:
            return False
        _local_locks[key] = now + ttl_s
        return True


async def release_lock(key: str) -> None:
    _local_locks.pop(key, None)
    try:
        await get_client().delete(key)
    except (RedisError, OSError, asyncio.TimeoutError):
        pass


async def ping() -> bool:
    try:
        return bool(await get_client().ping())
    except (RedisError, OSError, asyncio.TimeoutError):
        return False
