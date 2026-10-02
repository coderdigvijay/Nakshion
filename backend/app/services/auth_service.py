"""Email/password auth, OTP email verification, password reset (api-contract.md section 3)."""
from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ratelimit
from app.core.config import settings
from app.core.errors import (
    BadRequest,
    Conflict,
    RateLimited,
    UpstreamUnavailable,
)
from app.core.security import (
    create_access_token,
    hash_password,
    new_url_token,
    sha256_hex,
    user_id_hash,
    verify_password,
)
from app.db.session import SessionLocal
from app.models import PasswordReset, User
from app.services import cache, email_service

log = logging.getLogger("app.auth")

OTP_TTL_S = 600
OTP_MAX_ATTEMPTS = 5
RESET_TTL = timedelta(hours=1)
LOGIN_FAIL_WINDOW_S = 900
LOGIN_FAIL_PER_EMAIL = 10
LOGIN_FAIL_PER_IP = 50
# IP-independent backstops (X-Forwarded-For can be spoofed if the proxy passes client values through).
LOGIN_FAIL_PER_EMAIL_ANY_IP = 10   # then 429 for the rest of the 15-minute window: short, to limit lock-out abuse
EMAIL_CAP_PER_HOUR = 200           # all OTP / reset / deletion emails together: protects Brevo's 300/day free quota


# ------------------------------------------------------------------ helpers
def _otp_hash(code: str) -> str:
    return hashlib.sha256((code + settings.otp_pepper).encode()).hexdigest()


def _email_key(email: str) -> str:
    return hashlib.sha1(email.encode()).hexdigest()  # noqa: S324 - key derivation, not security


async def email_budget_ok() -> bool:
    """Global cap on transactional emails per hour (Redis, fail closed -> UpstreamUnavailable)."""
    return await cache.counter_incr("emailcap", 3600) <= EMAIL_CAP_PER_HOUR


async def _send_allowed(user: User, purpose: str = "otp") -> None:
    """OTP send throttle shared by register and resend: 1/min, 5/day per user (fail-closed)."""
    if await cache.counter_incr(f"{purpose}_resend_min:{user.id}", 60) > 1:
        raise RateLimited("Please wait a minute before requesting another code.", retry_after=60)
    if await cache.counter_incr(f"{purpose}_resend_day:{user.id}", 86400) > 5:
        raise RateLimited("You've requested too many codes today. Please try again tomorrow.", retry_after=3600)


async def _issue_otp(user: User, purpose: str = "otp") -> None:
    """Create a fresh OTP (fail-closed on Redis) and email it in the background."""
    await _send_allowed(user, purpose)
    if not await email_budget_ok():
        raise RateLimited("We're sending a lot of email right now. Please try again in a little while.", retry_after=1800)
    code = f"{secrets.randbelow(1_000_000):06d}"
    await cache.secure_set_json(f"{purpose}:{user.id}", {"hash": _otp_hash(code)}, OTP_TTL_S)
    await cache.secure_delete(f"{purpose}_attempts:{user.id}")
    if purpose == "otp":
        email_service.send_otp(user.email, user.name, code)
    else:
        email_service.send_deletion_code(user.email, user.name, code)


async def _check_otp(user: User, purpose: str, code: str) -> None:
    """Shared OTP verification (5 attempts, then the code is burned). Raises BadRequest/RateLimited."""
    record = await cache.secure_get_json(f"{purpose}:{user.id}")
    if not record:
        raise BadRequest("That code has expired. Please request a new one.", code="CODE_EXPIRED")
    attempts = await cache.counter_incr(f"{purpose}_attempts:{user.id}", OTP_TTL_S)
    if attempts > OTP_MAX_ATTEMPTS:
        await cache.secure_delete(f"{purpose}:{user.id}")
        raise RateLimited("Too many attempts. Please request a new code.", retry_after=60)
    if not hmac.compare_digest(record.get("hash", ""), _otp_hash(code)):
        if attempts >= OTP_MAX_ATTEMPTS:
            await cache.secure_delete(f"{purpose}:{user.id}")
        raise BadRequest("That code isn't right. Please check and try again.", code="INVALID_CODE")
    await cache.delete(f"{purpose}:{user.id}", f"{purpose}_attempts:{user.id}")


async def send_deletion_code(user: User) -> str:
    if user.password_hash:
        raise BadRequest("Confirm with your password instead.", code="PASSWORD_REAUTH_ONLY")
    await _issue_otp(user, "delcode")
    return "Confirmation code sent"


async def reauthenticate_for_deletion(user: User, *, password: str | None, code: str | None) -> None:
    """Account deletion is irreversible: a stolen bearer token alone must not be enough."""
    ratelimit.enforce("delete_account", str(user.id), 5, 900, "Too many attempts. Please wait and try again.")
    if user.password_hash:
        if not password:
            raise BadRequest("Please enter your password to delete your account.", code="REAUTH_REQUIRED")
        if not verify_password(password, user.password_hash):
            raise BadRequest("That password is incorrect.", code="INVALID_CURRENT_PASSWORD")
        return
    if not code:
        raise BadRequest("Please enter the confirmation code we emailed you.", code="REAUTH_REQUIRED")
    await _check_otp(user, "delcode", code)


# ------------------------------------------------------------------ A1 register
async def register(
    db: AsyncSession, *, email: str, password: str, name: str, terms_accepted: bool, age_confirmed: bool | None
) -> str:
    now = datetime.now(UTC)
    user = User(
        email=email,
        password_hash=hash_password(password),
        name=name,
        email_verified=False,
        terms_accepted_at=now if terms_accepted else None,
        terms_version=settings.TERMS_VERSION if terms_accepted else None,
        age_confirmed_at=now if age_confirmed else None,
        last_login_at=now,
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise Conflict("An account with this email already exists. Try logging in.", code="EMAIL_EXISTS") from None
    log.info("user_registered", extra={"user": user_id_hash(user.id)})
    try:
        await _issue_otp(user)
    except (UpstreamUnavailable, RateLimited):
        log.warning("email_send_failed", extra={"user": user_id_hash(user.id), "reason": "otp_store_unavailable"})
    return create_access_token(user.id, user.token_version)


# ------------------------------------------------------------------ A2 login
async def _login_fail_counts(ip: str, email: str) -> tuple[int, int, int] | None:
    try:
        ek = _email_key(email)
        per_email_ip, per_ip, per_email = await cache.counters_get(
            f"authfail:{ip}:{ek}", f"authfail:{ip}", f"authfail_email:{ek}"
        )
        return per_email_ip, per_ip, per_email
    except UpstreamUnavailable:
        return None


async def login(db: AsyncSession, *, email: str, password: str, ip: str) -> str:
    counts = await _login_fail_counts(ip, email)
    if counts is not None:
        if counts[0] >= LOGIN_FAIL_PER_EMAIL or counts[1] >= LOGIN_FAIL_PER_IP or counts[2] >= LOGIN_FAIL_PER_EMAIL_ANY_IP:
            retry = LOGIN_FAIL_WINDOW_S
            try:
                retry = max(1, await cache.secure_ttl(f"authfail_email:{_email_key(email)}")) if counts[2] >= LOGIN_FAIL_PER_EMAIL_ANY_IP else retry
            except UpstreamUnavailable:
                pass
            raise RateLimited("Too many login attempts. Please wait a few minutes and try again.", retry_after=retry)
    elif not ratelimit.check("login_fallback", ip, LOGIN_FAIL_PER_IP, LOGIN_FAIL_WINDOW_S):
        # Redis down: conservative in-process limit instead of failing every login.
        raise RateLimited("Too many login attempts. Please wait and try again.", retry_after=LOGIN_FAIL_WINDOW_S)

    user = await db.scalar(select(User).where(User.email == email))
    ok = verify_password(password, user.password_hash if user else None)  # constant-ish timing
    if not ok or user is None:
        ek = _email_key(email)
        try:
            await cache.counter_incr(f"authfail:{ip}:{ek}", LOGIN_FAIL_WINDOW_S)
            await cache.counter_incr(f"authfail:{ip}", LOGIN_FAIL_WINDOW_S)
            await cache.counter_incr(f"authfail_email:{ek}", LOGIN_FAIL_WINDOW_S)  # regardless of source IP
        except UpstreamUnavailable:
            pass
        log.info("login_failed")
        raise BadRequest("Incorrect email or password.", code="INVALID_CREDENTIALS")

    await db.execute(update(User).where(User.id == user.id).values(last_login_at=datetime.now(UTC)))
    await db.commit()
    if counts and (counts[0] or counts[2]):  # nothing to clear on the common path (saves commands)
        await cache.delete(f"authfail:{ip}:{_email_key(email)}", f"authfail_email:{_email_key(email)}")
    log.info("login_ok", extra={"user": user_id_hash(user.id)})
    return create_access_token(user.id, user.token_version)


# ------------------------------------------------------------------ A3 / A4 OTP
async def verify_email(db: AsyncSession, user: User, code: str) -> str:
    if user.email_verified:
        return "Email verified"
    await _check_otp(user, "otp", code)
    await db.execute(update(User).where(User.id == user.id).values(email_verified=True))
    await db.commit()
    log.info("email_verified", extra={"user": user_id_hash(user.id)})
    return "Email verified"


async def resend_otp(user: User) -> str:
    if user.email_verified:
        return "Email already verified"
    await _issue_otp(user)
    return "Verification code sent"


# ------------------------------------------------------------------ A5 / A6 reset
FORGOT_MESSAGE = "If an account exists for that email, a reset link is on its way."


async def forgot_password(db: AsyncSession, *, email: str, ip: str) -> str:
    # Over the limit: still 200, send nothing (no enumeration, no Brevo drain).
    if not ratelimit.check("forgot_ip", ip, 10, 3600) or not ratelimit.check("forgot_email", _email_key(email), 3, 3600):
        log.info("forgot_password_rate_limited")
        return FORGOT_MESSAGE
    user = await db.scalar(select(User).where(User.email == email))
    if user is None:
        return FORGOT_MESSAGE
    try:
        if not await email_budget_ok():  # Brevo free-quota guard: stay silent, same answer
            log.warning("email_cap_reached", extra={"kind": "password_reset"})
            return FORGOT_MESSAGE
    except UpstreamUnavailable:
        return FORGOT_MESSAGE
    raw = new_url_token()
    db.add(PasswordReset(user_id=user.id, token=sha256_hex(raw), expires_at=datetime.now(UTC) + RESET_TTL))
    await db.commit()
    email_service.send_password_reset(user.email, user.name, raw)
    log.info("password_reset_requested", extra={"user": user_id_hash(user.id)})
    return FORGOT_MESSAGE


async def reset_password(db: AsyncSession, *, token: str, new_password: str) -> str:
    new_hash = hash_password(new_password)  # CPU work before taking row locks
    user_id = await db.scalar(
        text(
            "UPDATE password_resets SET used = true "
            "WHERE token = :t AND used = false AND expires_at > now() RETURNING user_id"
        ),
        {"t": sha256_hex(token)},
    )
    if user_id is None:
        await db.rollback()
        raise BadRequest("This reset link is invalid or has expired. Please request a new one.", code="INVALID_OR_EXPIRED_TOKEN")
    await db.execute(
        update(PasswordReset).where(PasswordReset.user_id == user_id, PasswordReset.used.is_(False)).values(used=True)
    )
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(password_hash=new_hash, token_version=User.token_version + 1, email_verified=True)
    )
    await db.commit()
    log.info("password_reset_done", extra={"user": user_id_hash(user_id)})
    return "Password updated. Please log in."


# ------------------------------------------------------------------ A10 / A11 / A12
async def change_password(db: AsyncSession, user: User, *, current_password: str, new_password: str) -> tuple[str, str]:
    """Returns (message, fresh access token). Bumps token_version: every OTHER session (including a stolen token)
    stops working; the caller keeps going with the returned token."""
    ratelimit.enforce("change_password", str(user.id), 10, 900, "Too many attempts. Please wait and try again.")
    if not user.password_hash:
        raise BadRequest("Your account uses Google sign-in. Set a password instead.", code="NO_PASSWORD_SET")
    if not verify_password(current_password, user.password_hash):
        raise BadRequest("Your current password is incorrect.", code="INVALID_CURRENT_PASSWORD")
    new_ver = await db.scalar(
        update(User)
        .where(User.id == user.id)
        .values(password_hash=hash_password(new_password), token_version=User.token_version + 1)
        .returning(User.token_version)
    )
    await db.commit()
    log.info("password_changed", extra={"user": user_id_hash(user.id)})
    return "Password changed", create_access_token(user.id, int(new_ver))


async def set_password(db: AsyncSession, user: User, *, new_password: str) -> str:
    updated = await db.scalar(
        update(User)
        .where(User.id == user.id, User.password_hash.is_(None))
        .values(password_hash=hash_password(new_password))
        .returning(User.id)
    )
    if updated is None:
        await db.rollback()
        raise Conflict("You already have a password. Use change password instead.", code="PASSWORD_ALREADY_SET")
    await db.commit()
    return "Password set"


async def logout_all(db: AsyncSession, user: User) -> str:
    await db.execute(update(User).where(User.id == user.id).values(token_version=User.token_version + 1))
    await db.commit()
    return "Logged out of all sessions"


async def purge_expired_resets() -> int:
    """Cron 'hourly': drop reset rows older than 24 h."""
    async with SessionLocal() as db:
        res = await db.execute(text("DELETE FROM password_resets WHERE created_at < now() - interval '24 hours'"))
        await db.commit()
        return int(res.rowcount or 0)
