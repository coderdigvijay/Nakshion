"""Password hashing (bcrypt) and JWT encode/decode (PyJWT, HS256 only)."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import bcrypt
import jwt

from app.core.config import settings

BCRYPT_MAX_BYTES = 72
PASSWORD_MIN_CHARS = 8

_COMMON_FILE = Path(__file__).resolve().parent / "data" / "common_passwords.txt"


def _load_common() -> frozenset[str]:
    try:
        return frozenset(
            line.strip().lower() for line in _COMMON_FILE.read_text(encoding="utf-8").splitlines() if line.strip()
        )
    except OSError:
        return frozenset()


COMMON_PASSWORDS = _load_common()


def password_policy_error(password: str) -> str | None:
    """Return "CODE|message" if the password breaks policy, else None (NIST 800-63B style)."""
    if len(password) < PASSWORD_MIN_CHARS:
        return "VALIDATION_ERROR|Password must be at least 8 characters."
    if len(password.encode("utf-8")) > BCRYPT_MAX_BYTES:
        return "PASSWORD_TOO_LONG|Password is too long (maximum 72 bytes)."
    if password.lower() in COMMON_PASSWORDS:
        return "PASSWORD_TOO_COMMON|That password is too common. Please choose a less guessable one."
    return None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS)).decode("ascii")


# A valid hash used to keep login timing constant for unknown emails / OAuth-only accounts.
_DUMMY_HASH = bcrypt.hashpw(b"nakshion-dummy-password", bcrypt.gensalt(rounds=settings.BCRYPT_ROUNDS))


def verify_password(password: str, password_hash: str | None) -> bool:
    pw = password.encode("utf-8")
    if len(pw) > BCRYPT_MAX_BYTES:
        bcrypt.checkpw(b"x", _DUMMY_HASH)
        return False
    if not password_hash:
        bcrypt.checkpw(pw, _DUMMY_HASH)
        return False
    try:
        return bcrypt.checkpw(pw, password_hash.encode("ascii"))
    except ValueError:
        return False


def create_access_token(user_id: uuid.UUID, token_version: int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)).timestamp()),
        "ver": token_version,
        "typ": "access",
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm="HS256")


def decode_access_token(token: str) -> tuple[uuid.UUID, int] | None:
    """Return (user_id, token_version) or None if invalid/expired/wrong type."""
    try:
        claims = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=["HS256"], options={"require": ["exp", "sub"]})
    except jwt.PyJWTError:
        return None
    if claims.get("typ") != "access":
        return None
    try:
        return uuid.UUID(str(claims["sub"])), int(claims.get("ver", -1))
    except (KeyError, ValueError, TypeError):
        return None


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def new_url_token() -> str:
    return secrets.token_urlsafe(32)


def user_id_hash(user_id: uuid.UUID | str) -> str:
    return sha256_hex(str(user_id))[:12]
