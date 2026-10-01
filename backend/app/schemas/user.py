from __future__ import annotations

import uuid
import zoneinfo
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import CleanName, InModel, OutModel, _no_control_chars

Language = Literal["english", "hindi", "hinglish"]
AstroSystem = Literal["vedic", "western"]


class QuotaOut(OutModel):
    chat_remaining_today: int
    chat_daily_limit: int
    resets_at: datetime


class UserOut(OutModel):
    id: uuid.UUID
    email: str
    name: str
    email_verified: bool
    avatar_url: str | None
    subscription_tier: Literal["free", "premium"]
    timezone: str
    created_at: datetime
    # v1-add
    has_password: bool
    preferred_language: Language
    astrology_system: AstroSystem
    quota: QuotaOut | None = None


class UpdateUserIn(InModel):
    name: CleanName | None = Field(default=None, min_length=1, max_length=100)
    timezone: str | None = Field(default=None, max_length=50)
    preferred_language: Language | None = None
    astrology_system: AstroSystem | None = None

    @field_validator("name")
    @classmethod
    def _name(cls, v: str | None) -> str | None:
        return None if v is None else _no_control_chars(v)

    @field_validator("timezone")
    @classmethod
    def _tz(cls, v: str | None) -> str | None:
        if v is not None and v not in zoneinfo.available_timezones():
            raise ValueError("Unknown time zone.")
        return v


class ConsentsIn(InModel):
    ai_processing: bool
    marketing_email: bool = False


class DeleteAccountIn(InModel):
    """Re-authentication for irreversible deletion: password users send ``password``;
    OAuth-only users send ``code`` from POST /users/me/deletion-code."""

    password: str | None = Field(default=None, max_length=1024)
    code: str | None = Field(default=None, pattern=r"^\d{6}$")
