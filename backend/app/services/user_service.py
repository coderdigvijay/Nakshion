"""Profile read/update and account deletion (api-contract.md section 4)."""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import RateLimited
from app.core.security import sha256_hex, user_id_hash
from app.models import BirthChart, DeletionLog, User
from app.schemas.user import QuotaOut, UpdateUserIn, UserOut
from app.services import auth_service, cache, email_service, quota_service

log = logging.getLogger("app.users")


async def to_out(db: AsyncSession, user: User) -> UserOut:
    tier = user.subscription_tier if user.subscription_tier in ("free", "premium") else "free"
    return UserOut(
        id=user.id,
        email=user.email,
        name=user.name or "",
        email_verified=user.email_verified,
        avatar_url=user.avatar_url,
        subscription_tier=tier,
        timezone=user.timezone or "UTC",
        created_at=user.created_at,
        has_password=user.password_hash is not None,
        preferred_language=user.preferred_language or "english",
        astrology_system=user.astrology_system or "vedic",
        quota=QuotaOut(**await quota_service.chat_quota_summary(db, user)),
    )


async def get_me(db: AsyncSession, user: User) -> UserOut:
    return await to_out(db, user)


async def update_me(db: AsyncSession, user: User, data: UpdateUserIn) -> UserOut:
    values = data.model_dump(exclude_unset=True, exclude_none=True)
    if "timezone" in values and values["timezone"] == user.timezone:
        values.pop("timezone")  # no-op change: free, and does not use the daily allowance
    if "timezone" in values:
        # Quotas reset at the user's local midnight, so repeated tz flips would buy extra quota.
        # Fail closed (Redis down -> 503) like other quota-protecting counters.
        if await cache.counter_incr(f"tzchange:{user.id}", 86400) > 1:
            raise RateLimited("You can change your time zone once a day.", retry_after=86400)
    if values:
        values["updated_at"] = datetime.now(UTC)
        await db.execute(update(User).where(User.id == user.id).values(**values))
        await db.commit()
        await db.refresh(user)
        if "timezone" in values:
            # "today" moved for this user: the personal reading key is date-scoped.
            await cache.delete_pattern(f"daily_personal:{user.id}:*")
    return await to_out(db, user)


async def update_consents(db: AsyncSession, user: User, *, ai_processing: bool) -> UserOut:
    now = datetime.now(UTC)
    values = {"ai_consent_at": now, "ai_consent_withdrawn_at": None} if ai_processing else {"ai_consent_withdrawn_at": now}
    await db.execute(update(User).where(User.id == user.id).values(**values))
    await db.commit()
    await db.refresh(user)
    return await to_out(db, user)


async def delete_me(db: AsyncSession, user: User, *, password: str | None, code: str | None) -> None:
    await auth_service.reauthenticate_for_deletion(user, password=password, code=code)
    await purge_user(db, user)


async def purge_user(db: AsyncSession, user: User) -> None:
    """The account-deletion path proper (after re-auth): cascade delete, deletion log, cache purge, email.
    Used by delete_me and by maintenance scripts."""
    chart_ids = list(await db.scalars(select(BirthChart.id).where(BirthChart.user_id == user.id)))
    email, name, uid = user.email, user.name, user.id
    db.add(DeletionLog(user_id_sha256=sha256_hex(str(uid))))
    await db.execute(delete(User).where(User.id == uid))  # FKs cascade to every user-owned table
    await db.commit()
    log.info("account_deleted", extra={"user": user_id_hash(uid)})
    # After commit: purge derived cache state (fail-open).
    await cache.delete_pattern(f"*{uid}*")
    for cid in chart_ids:
        await cache.delete_pattern(f"*{cid}*")
    email_service.send_account_deleted(email, name)
