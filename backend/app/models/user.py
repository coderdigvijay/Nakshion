from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index("uq_users_oauth", "oauth_provider", "oauth_id", unique=True, postgresql_where=text("oauth_provider IS NOT NULL")),
        Index("uq_users_email_lower", text("lower(email)"), unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), default=False)
    oauth_provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    oauth_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    subscription_tier: Mapped[str] = mapped_column(String(20), nullable=False, server_default="free", default="free")
    timezone: Mapped[str] = mapped_column(String(50), nullable=False, server_default="UTC", default="UTC")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # 003
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0", default=0)
    preferred_language: Mapped[str] = mapped_column(String(10), nullable=False, server_default="english", default="english")
    astrology_system: Mapped[str] = mapped_column(String(10), nullable=False, server_default="vedic", default="vedic")
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    terms_version: Mapped[str | None] = mapped_column(String(40), nullable=True)  # 010
    age_confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ai_consent_withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PasswordReset(Base):
    __tablename__ = "password_resets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # SHA-256 hex of the raw token (the raw token is never stored).
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    used: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
