"""Product quotas in Postgres ``usage_counters`` (architecture.md section 7).

Periods are in the user's own time zone. ``consume`` is atomic
(INSERT ... ON CONFLICT DO UPDATE ... WHERE count < limit RETURNING) and runs in the caller's
transaction AFTER the expensive work succeeded; ``precheck`` is a cheap read beforehand.
Quota checks fail closed: a DB error propagates (no silent allow).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import QuotaExceeded
from app.db.session import SessionLocal
from app.models import UsageCounter, User

CHAT_REPLY = "chat_reply"
COMPAT_REPORT = "compat_report"

_PERIOD = {CHAT_REPLY: "day", COMPAT_REPORT: "month"}


def user_zone(user: User | None) -> ZoneInfo:
    name = (user.timezone if user else None) or settings.DEFAULT_ANON_TZ
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return ZoneInfo("UTC")


def local_today(user: User | None, now: datetime | None = None) -> date:
    return (now or datetime.now(UTC)).astimezone(user_zone(user)).date()


def limit_for(user: User, kind: str) -> int:
    premium = user.subscription_tier == "premium"
    if kind == CHAT_REPLY:
        return settings.QUOTA_CHAT_PREMIUM if premium else settings.QUOTA_CHAT_FREE
    if kind == COMPAT_REPORT:
        return settings.QUOTA_COMPAT_PREMIUM if premium else settings.QUOTA_COMPAT_FREE
    raise ValueError(kind)


@dataclass(frozen=True)
class Window:
    period: str
    start: date
    resets_at: datetime


def window(user: User, kind: str, now: datetime | None = None) -> Window:
    tz = user_zone(user)
    today = local_today(user, now)
    if _PERIOD[kind] == "day":
        start = today
        nxt = today + timedelta(days=1)
    else:
        start = today.replace(day=1)
        nxt = (start + timedelta(days=32)).replace(day=1)
    resets = datetime.combine(nxt, time(0), tzinfo=tz).astimezone(UTC)
    return Window(_PERIOD[kind], start, resets)


async def used(db: AsyncSession, user: User, kind: str) -> int:
    w = window(user, kind)
    n = await db.scalar(
        select(UsageCounter.count).where(
            UsageCounter.user_id == user.id,
            UsageCounter.kind == kind,
            UsageCounter.period == w.period,
            UsageCounter.period_start == w.start,
        )
    )
    return int(n or 0)


def _exceeded(user: User, kind: str, limit: int) -> QuotaExceeded:
    """Copy never names a time zone (the stored one is often the 'UTC' default); the exact reset
    instant is returned as ``resets_at`` (ISO UTC) so the client renders it in the viewer's zone."""
    w = window(user, kind)
    retry = max(1, int((w.resets_at - datetime.now(UTC)).total_seconds()))
    if kind == CHAT_REPLY:
        label = "free questions" if user.subscription_tier != "premium" else "questions"
        detail = f"You've used today's {limit} {label}. They reset daily."
    else:
        detail = f"You've used this month's {limit} compatibility reports."
    return QuotaExceeded(
        detail, retry_after=retry,
        extra={"resets_at": w.resets_at.strftime("%Y-%m-%dT%H:%M:%SZ"), "limit": limit},
    )


async def precheck(db: AsyncSession, user: User, kind: str) -> None:
    limit = limit_for(user, kind)
    if await used(db, user, kind) >= limit:
        raise _exceeded(user, kind, limit)


async def consume(db: AsyncSession, user: User, kind: str, w: Window | None = None) -> int:
    """Atomically take one unit in the caller's transaction. Raises QuotaExceeded if at limit."""
    limit = limit_for(user, kind)
    w = w or window(user, kind)
    new_count = await db.scalar(
        text(
            """
            INSERT INTO usage_counters (user_id, kind, period, period_start, count)
            VALUES (:u, :k, :p, :d, 1)
            ON CONFLICT (user_id, kind, period, period_start)
            DO UPDATE SET count = usage_counters.count + 1 WHERE usage_counters.count < :limit
            RETURNING count
            """
        ),
        {"u": user.id, "k": kind, "p": w.period, "d": w.start, "limit": limit},
    )
    if new_count is None:
        raise _exceeded(user, kind, limit)
    return int(new_count)


async def chat_quota_summary(db: AsyncSession, user: User) -> dict:
    limit = limit_for(user, CHAT_REPLY)
    n = await used(db, user, CHAT_REPLY)
    return {
        "chat_remaining_today": max(0, limit - n),
        "chat_daily_limit": limit,
        "resets_at": window(user, CHAT_REPLY).resets_at,
    }



async def reserve(db: AsyncSession, user: User, kind: str) -> Window:
    """Take one unit BEFORE an expensive call and commit it, so concurrent requests (even across
    conversations) cannot overshoot the limit. Pair with ``release`` on every failure path."""
    w = window(user, kind)
    await consume(db, user, kind, w)
    await db.commit()
    return w


async def release(user_id: "uuid.UUID", kind: str, w: Window) -> None:
    """Give a reserved unit back (own session; safe to call from cleanup paths)."""
    async with SessionLocal() as s:
        key = {"u": user_id, "k": kind, "p": w.period, "d": w.start}
        await s.execute(
            text(
                "UPDATE usage_counters SET count = count - 1 WHERE user_id = :u AND kind = :k "
                "AND period = :p AND period_start = :d AND count > 0"
            ),
            key,
        )
        await s.execute(
            text(
                "DELETE FROM usage_counters WHERE user_id = :u AND kind = :k AND period = :p "
                "AND period_start = :d AND count <= 0"
            ),
            key,
        )
        await s.commit()
