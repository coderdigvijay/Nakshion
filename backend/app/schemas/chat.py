from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator

from app.schemas.common import InModel, OutModel

Category = Literal["general", "love", "career", "health", "timing", "spiritual", "compatibility"]


class CreateConversationIn(InModel):
    chart_id: uuid.UUID | None = None
    category: Category | None = None


class SendMessageIn(InModel):
    content: str = Field(min_length=1, max_length=2000)
    language: Literal["english", "hindi", "hinglish"] = "english"

    @field_validator("content", mode="before")
    @classmethod
    def _strip(cls, v: object) -> object:
        if isinstance(v, str):
            # drop control characters FIRST, then trim: otherwise "\x00 " survives as a blank message
            v = "".join(ch for ch in v if ch in "\n\t" or ord(ch) >= 32).strip()
        return v


class BookmarkIn(InModel):
    bookmarked: bool


class FeedbackIn(InModel):
    rating: Literal["up", "down"]
    reason: Literal["inaccurate", "generic", "harmful", "other"] | None = None
    comment: str | None = Field(default=None, max_length=500)


class UpdateConversationIn(InModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    status: Literal["active", "archived"] | None = None


class ConversationOut(OutModel):
    id: uuid.UUID
    user_id: uuid.UUID
    chart_id: uuid.UUID | None
    title: str | None
    category: str | None
    status: str
    message_count: int
    created_at: datetime
    updated_at: datetime


class CitationOut(OutModel):
    factor_id: str
    label: str


class SourceOut(OutModel):
    """A reference note the answer drew on (citation chip). ``source_id`` is an opaque hash, never a file name."""

    source_id: str
    title: str
    section: str
    tier: int | None = None


class MessageOut(OutModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: Literal["user", "assistant"]
    content: str
    bookmarked: bool
    tokens_used: int | None
    created_at: datetime
    citations: list[CitationOut] | None = None
    sources: list[SourceOut] | None = None
    feedback: Literal["up", "down"] | None = None


class ConversationDetailOut(OutModel):
    conversation: ConversationOut
    messages: list[MessageOut]


class SuggestionsOut(OutModel):
    suggestions: list[str]
