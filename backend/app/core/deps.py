"""FastAPI dependencies: DB session, current user, rate limits."""
from __future__ import annotations

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import ratelimit
from app.core.clientip import ip_from_scope
from app.core.errors import Unauthenticated
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User

_bearer = HTTPBearer(auto_error=False)

DB = Annotated[AsyncSession, Depends(get_db)]


async def _user_from_token(db: AsyncSession, creds: HTTPAuthorizationCredentials | None) -> User | None:
    if creds is None or creds.scheme.lower() != "bearer" or not creds.credentials:
        return None
    decoded = decode_access_token(creds.credentials)
    if decoded is None:
        raise Unauthenticated()
    user_id, ver = decoded
    user = await db.get(User, user_id)
    # Deleted user or revoked token (token_version bumped) -> 401.
    if user is None or user.token_version != ver:
        raise Unauthenticated()
    return user


async def get_current_user(
    db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> User:
    user = await _user_from_token(db, creds)
    if user is None:
        raise Unauthenticated()
    return user


async def get_optional_user(
    db: DB, creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)]
) -> User | None:
    """Optional auth: no header -> anonymous; a bad token is still treated as anonymous here
    (R1 is public; failing it would log out a user whose token merely expired mid-view)."""
    try:
        return await _user_from_token(db, creds)
    except Unauthenticated:
        return None


CurrentUser = Annotated[User, Depends(get_current_user)]
OptionalUser = Annotated[User | None, Depends(get_optional_user)]


def client_ip(request: Request) -> str:
    return ip_from_scope(request.scope)


def rate_limit(scope: str, limit: int, window_s: int, *, per: str = "user") -> Callable:
    """Dependency factory: in-process sliding window keyed by user id or client IP."""

    if per == "user":

        async def _dep_user(user: CurrentUser) -> None:
            ratelimit.enforce(scope, str(user.id), limit, window_s)

        return _dep_user

    async def _dep_ip(request: Request) -> None:
        ratelimit.enforce(scope, client_ip(request), limit, window_s)

    return _dep_ip
