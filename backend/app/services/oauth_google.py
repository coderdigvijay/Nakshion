"""Google OAuth (authorization code + PKCE + state), api-contract A8/A9.

ID tokens are verified with PyJWT against Google's JWKS (cached in-process 1 h).
Every failure path returns the frontend error redirect; nothing raw reaches the browser.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import secrets
import time
import uuid
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlencode

import httpx
import jwt
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AppError, BadRequest, UpstreamUnavailable
from app.core.security import create_access_token, user_id_hash
from app.models import User
from app.services import cache

log = logging.getLogger("app.oauth")

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
JWKS_URL = "https://www.googleapis.com/oauth2/v3/certs"
ISSUERS = {"accounts.google.com", "https://accounts.google.com"}
STATE_TTL_S = 600

_jwks: dict[str, Any] = {"keys": None, "at": 0.0}


class OAuthFailed(Exception):
    pass


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


async def authorization_url(terms_accepted: bool = False) -> str:
    """``terms_accepted`` is the user's explicit consent to the Terms/Privacy Policy given on OUR page before
    the redirect to Google; it is stored with the single-use state and required only to create a NEW account."""
    if not settings.GOOGLE_CLIENT_ID:
        return failure_redirect()
    state = secrets.token_urlsafe(32)
    verifier = secrets.token_urlsafe(64)
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    try:
        await cache.secure_set_json(f"oauth_state:{state}", {"v": verifier, "terms": bool(terms_accepted)}, STATE_TTL_S)
    except UpstreamUnavailable:
        return failure_redirect()
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "prompt": "select_account",
    }
    return f"{AUTH_URL}?{urlencode(params)}"


def failure_redirect(reason: str = "oauth_failed") -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/auth/callback?error={reason}"


CODE_TTL_S = 60


async def success_redirect(user: User) -> str:
    """Redirect with a single-use, 60 s opaque code instead of the JWT (keeps the token out of
    history, logs and Referer). The SPA trades it via POST /auth/oauth/exchange."""
    code = secrets.token_urlsafe(32)
    await cache.secure_set_json(f"oauth_code:{code}", {"uid": str(user.id), "ver": user.token_version}, CODE_TTL_S)
    return f"{settings.FRONTEND_URL.rstrip('/')}/auth/callback?{urlencode({'code': code})}"


async def exchange_login_code(db: AsyncSession, code: str) -> str:
    """Single use (GETDEL). Re-checks the user and token_version so a revoked/deleted user gets nothing."""
    rec = await cache.secure_pop_json(f"oauth_code:{code}")
    user = None
    if rec:
        try:
            user = await db.get(User, uuid.UUID(rec["uid"]))
        except (ValueError, KeyError):
            user = None
    if user is None or user.token_version != rec.get("ver"):
        raise BadRequest("This sign-in link is invalid or has expired. Please try again.", code="INVALID_OR_EXPIRED_CODE")
    return create_access_token(user.id, user.token_version)


async def _get_jwks(client: httpx.AsyncClient, force: bool = False) -> dict:
    if not force and _jwks["keys"] and time.monotonic() - _jwks["at"] < 3600:
        return _jwks["keys"]
    resp = await client.get(JWKS_URL)
    resp.raise_for_status()
    _jwks["keys"], _jwks["at"] = resp.json(), time.monotonic()
    return _jwks["keys"]


async def _verify_id_token(client: httpx.AsyncClient, id_token: str) -> dict:
    header = jwt.get_unverified_header(id_token)
    if header.get("alg") != "RS256":
        raise OAuthFailed("unexpected alg")
    for force in (False, True):  # refetch once on key rotation
        jwks = await _get_jwks(client, force=force)
        jwk = next((k for k in jwks.get("keys", []) if k.get("kid") == header.get("kid")), None)
        if jwk is not None:
            key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
            claims = jwt.decode(
                id_token, key, algorithms=["RS256"], audience=settings.GOOGLE_CLIENT_ID,
                options={"require": ["exp", "iss", "aud", "sub"]},
            )
            if claims.get("iss") not in ISSUERS:
                raise OAuthFailed("bad issuer")
            return claims
    raise OAuthFailed("unknown kid")


async def exchange_code(code: str, state: str) -> tuple[dict, bool]:
    """Consume state, exchange the code with PKCE, verify the ID token. Returns (claims, terms_accepted)."""
    record = await cache.secure_pop_json(f"oauth_state:{state}")
    if not record:
        raise OAuthFailed("state missing or reused")
    async with httpx.AsyncClient(timeout=5.0) as client:
        resp = await client.post(
            TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
                "code_verifier": record["v"],
            },
        )
        if resp.status_code != 200:
            raise OAuthFailed(f"token exchange status {resp.status_code}")
        id_token = resp.json().get("id_token")
        if not id_token:
            raise OAuthFailed("no id_token")
        claims = await _verify_id_token(client, id_token)
    if claims.get("email_verified") not in (True, "true"):
        raise OAuthFailed("google email not verified")
    if not claims.get("sub") or not claims.get("email"):
        raise OAuthFailed("missing claims")
    return claims, bool(record.get("terms"))


async def upsert_google_user(db: AsyncSession, claims: dict, terms_accepted: bool = False) -> User:
    sub = str(claims["sub"])
    email = str(claims["email"]).strip().lower()
    now = datetime.now(UTC)
    user = await db.scalar(select(User).where(User.oauth_provider == "google", User.oauth_id == sub))
    if user is None:
        user = await db.scalar(select(User).where(User.email == email))
        if user is not None:
            if user.oauth_provider and user.oauth_id != sub:
                raise OAuthFailed("email linked to a different oauth identity")
            values: dict[str, Any] = {"oauth_provider": "google", "oauth_id": sub, "email_verified": True}
            if not user.email_verified:
                # Pre-hijack defense: an unverified local password could belong to an attacker
                # who registered this email first. Google just proved inbox ownership.
                values.update(password_hash=None, token_version=User.token_version + 1)
            if not user.avatar_url and claims.get("picture"):
                values["avatar_url"] = claims["picture"]
            await db.execute(update(User).where(User.id == user.id).values(**values))
            await db.commit()
            await db.refresh(user)
        else:
            if not terms_accepted:
                raise OAuthFailed("terms_required")  # no account without explicit acceptance
            user = User(
                email=email,
                password_hash=None,
                name=(claims.get("name") or "")[:100] or None,
                email_verified=True,
                oauth_provider="google",
                oauth_id=sub,
                avatar_url=claims.get("picture"),
                terms_accepted_at=now,
                terms_version=settings.TERMS_VERSION,
            )
            db.add(user)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()
                raise OAuthFailed("concurrent signup") from None
    await db.execute(update(User).where(User.id == user.id).values(last_login_at=now))
    await db.commit()
    return user


async def handle_callback(db: AsyncSession, *, code: str | None, state: str | None, error: str | None) -> str:
    """Returns the frontend redirect URL (success with token, or error)."""
    if error or not code or not state:
        return failure_redirect()
    try:
        claims, terms = await exchange_code(code, state)
        user = await upsert_google_user(db, claims, terms)
    except OAuthFailed as exc:
        log.warning("oauth_failed", extra={"reason": str(exc)[:40]})
        return failure_redirect("terms_required" if str(exc) == "terms_required" else "oauth_failed")
    except (jwt.PyJWTError, httpx.HTTPError, AppError, KeyError, ValueError) as exc:
        log.warning("oauth_failed", extra={"reason": type(exc).__name__})
        return failure_redirect()
    try:
        url = await success_redirect(user)
    except UpstreamUnavailable:
        return failure_redirect()
    log.info("oauth_login", extra={"user": user_id_hash(user.id)})
    return url
