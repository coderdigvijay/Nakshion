"""Conversations and messages (api-contract.md section 6).

Send pipeline (H5): ownership -> verified -> chart -> consent -> quota pre-check -> per-conversation
lock -> read context and RELEASE the DB session -> LLM (25 s deadline) -> one short transaction
that inserts both messages, consumes quota atomically and bumps the conversation counters.
Streaming (H6): user message persisted first; assistant message persisted at the end; on any
failure or client disconnect the orphan user message is removed and the lock released (finally).
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import AIUnavailable, AppError, Conflict, Forbidden, NotFound, QuotaExceeded
from app.core.security import user_id_hash
from app.db.session import SessionLocal
from app.models import BirthChart, Conversation, Message, MessageFeedback, User
from app.schemas.chat import (
    ConversationDetailOut,
    ConversationOut,
    CreateConversationIn,
    FeedbackIn,
    MessageOut,
    SendMessageIn,
    SuggestionsOut,
    UpdateConversationIn,
)
from app.services import ai, cache, chart_service, engine, quota_service

log = logging.getLogger("app.chat")

# Privacy: no name (the chart label can be a real person's name) is sent to the LLM provider.
PROVIDER_DISPLAY_NAME = "the user"

CATEGORIES = {"general", "love", "career", "health", "timing", "spiritual", "compatibility"}
HISTORY_MESSAGES = 12  # last 6 turns
DETAIL_MESSAGES = 200
LOCK_TTL_S = 60


# ------------------------------------------------------------------ serialisation
def message_out(m: Message, feedback: str | None = None) -> MessageOut:
    cites = (m.meta or {}).get("citations") if m.role == "assistant" else None
    sources = (m.meta or {}).get("sources") if m.role == "assistant" else None
    return MessageOut(
        id=m.id,
        conversation_id=m.conversation_id,
        role=m.role,  # type: ignore[arg-type]
        content=m.content,
        bookmarked=m.bookmarked,
        tokens_used=m.tokens_used if m.role == "assistant" else None,
        created_at=m.created_at,
        citations=cites if isinstance(cites, list) else None,
        sources=ai.clean_sources(sources) if isinstance(sources, list) else None,  # re-sanitised on read
        feedback=feedback,  # type: ignore[arg-type]
    )


def conversation_out(c: Conversation) -> ConversationOut:
    return ConversationOut.model_validate(c)


def make_title(text: str, limit: int = 60) -> str:
    t = " ".join(text.split())
    if len(t) <= limit:
        return t
    cut = t[:limit]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,.;:-")


# ------------------------------------------------------------------ ownership (single source)
async def get_owned_conversation(db: AsyncSession, user_id: uuid.UUID, conv_id: uuid.UUID) -> Conversation:
    conv = await db.scalar(select(Conversation).where(Conversation.id == conv_id, Conversation.user_id == user_id))
    if conv is None:
        raise NotFound("Conversation not found.")
    return conv


async def _get_owned_message(db: AsyncSession, user_id: uuid.UUID, message_id: uuid.UUID) -> Message:
    msg = await db.scalar(
        select(Message)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(Message.id == message_id, Conversation.user_id == user_id)
    )
    if msg is None:
        raise NotFound("Message not found.")
    return msg


# ------------------------------------------------------------------ H1-H4, H10
async def create_conversation(db: AsyncSession, user: User, data: CreateConversationIn) -> ConversationOut:
    if data.chart_id is not None:
        chart_id: uuid.UUID | None = (await chart_service.get_owned(db, user.id, data.chart_id)).id
    else:
        primary = await chart_service.get_primary(db, user.id)
        chart_id = primary.id if primary else None
    conv = Conversation(user_id=user.id, chart_id=chart_id, category=data.category)
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    return conversation_out(conv)


async def list_conversations(db: AsyncSession, user: User, limit: int = 50, before: datetime | None = None) -> list[ConversationOut]:
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user.id, Conversation.status == "active")
        .order_by(Conversation.updated_at.desc())
        .limit(max(1, min(limit, 50)))
    )
    if before is not None:
        stmt = stmt.where(Conversation.updated_at < before)
    return [conversation_out(c) for c in await db.scalars(stmt)]


async def get_conversation(db: AsyncSession, user: User, conv_id: uuid.UUID) -> ConversationDetailOut:
    conv = await get_owned_conversation(db, user.id, conv_id)
    recent = (
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at.desc(), Message.role.asc())
        .limit(DETAIL_MESSAGES)
        .subquery()
    )
    msgs = list(await db.scalars(select(Message).join(recent, Message.id == recent.c.id)))
    msgs.sort(key=lambda m: (m.created_at, 0 if m.role == "user" else 1))
    fb_rows = await db.execute(
        select(MessageFeedback.message_id, MessageFeedback.rating).where(
            MessageFeedback.message_id.in_([m.id for m in msgs if m.role == "assistant"])
        )
    ) if msgs else []
    fb = {mid: rating for mid, rating in fb_rows}
    return ConversationDetailOut(conversation=conversation_out(conv), messages=[message_out(m, fb.get(m.id)) for m in msgs])


async def delete_conversation(db: AsyncSession, user: User, conv_id: uuid.UUID) -> None:
    res = await db.execute(delete(Conversation).where(Conversation.id == conv_id, Conversation.user_id == user.id))
    if not res.rowcount:
        await db.rollback()
        raise NotFound("Conversation not found.")
    await db.commit()


async def update_conversation(db: AsyncSession, user: User, conv_id: uuid.UUID, data: UpdateConversationIn) -> ConversationOut:
    conv = await get_owned_conversation(db, user.id, conv_id)
    if data.title is not None:
        conv.title = data.title.strip()
    if data.status is not None:
        conv.status = data.status
    await db.commit()
    await db.refresh(conv)
    return conversation_out(conv)


# ------------------------------------------------------------------ send: shared pre-checks
class _SendContext:
    def __init__(self, conv: Conversation, chart: BirthChart, history: list[dict[str, str]], first: bool) -> None:
        self.conv_id = conv.id
        self.chart_id = chart.id
        self.chart_name = chart.name
        self.chart_data = chart.chart_data
        self.history = history
        self.first = first
        self.quota_window: quota_service.Window | None = None


async def _prepare(db: AsyncSession, user: User, conv_id: uuid.UUID) -> _SendContext:
    conv = await get_owned_conversation(db, user.id, conv_id)                         # 1
    if not user.email_verified:                                                        # 2
        raise Forbidden("Please verify your email to chat with Nakshion.", code="EMAIL_NOT_VERIFIED")
    chart: BirthChart | None = None                                                    # 3
    if conv.chart_id is not None:
        chart = await db.scalar(select(BirthChart).where(BirthChart.id == conv.chart_id, BirthChart.user_id == user.id))
    if chart is None:
        chart = await chart_service.get_primary(db, user.id)
        if chart is not None:
            conv.chart_id = chart.id
    if chart is None:
        raise Conflict("Add your birth details first so answers are about *your* chart.", code="CHART_REQUIRED")
    if user.ai_consent_withdrawn_at is not None:                                       # 4
        raise Forbidden("You've turned off AI processing of your birth data. Re-enable it in your profile to chat.", code="AI_CONSENT_REQUIRED")
    rows = list(
        await db.scalars(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at.desc())
            .limit(HISTORY_MESSAGES)
        )
    )
    history = [{"role": m.role, "content": m.content} for m in reversed(rows)]
    ctx = _SendContext(conv, chart, history, first=conv.message_count == 0 and conv.title is None)
    chart_data = await engine.refresh_time_dependent(chart.chart_data)
    ctx.chart_data = chart_data
    await db.commit()  # persist chart attach; ends the txn so no connection is held during the LLM call
    return ctx


async def _acquire(conv_id: uuid.UUID) -> str:
    key = f"chat_lock:{conv_id}"
    if not await cache.acquire_lock(key, LOCK_TTL_S):                                  # 6
        raise Conflict("Your previous message is still being answered.", code="MESSAGE_IN_FLIGHT")
    return key


def _category(topic: Any) -> str:
    return topic if isinstance(topic, str) and topic in CATEGORIES else "general"


def _assistant_meta(result: dict[str, Any], language: str) -> dict[str, Any]:
    meta = dict(result.get("metadata") or {})
    meta["citations"] = result.get("citations") or []
    meta["sources"] = result.get("sources") or []
    meta.setdefault("topic", result.get("topic"))
    meta["language"] = language
    return meta


# ------------------------------------------------------------------ H5 send (non-streaming)
async def send_message(db: AsyncSession, user: User, conv_id: uuid.UUID, data: SendMessageIn) -> list[MessageOut]:
    ctx = await _prepare(db, user, conv_id)
    uid = user.id  # captured: never touch ORM instances after a rollback
    lock_key = await _acquire(ctx.conv_id)
    reserved = False
    try:
        ctx.quota_window = await quota_service.reserve(db, user, quota_service.CHAT_REPLY)  # 5: atomic, pre-LLM
        reserved = True
        received_at = datetime.now(UTC)
        result = await ai.chat_reply(
            chart_data=ctx.chart_data,
            question=data.content,
            history=ctx.history,
            language=data.language,
            user_id_hash=user_id_hash(uid),
            astrology_system=user.astrology_system,
            display_name=PROVIDER_DISPLAY_NAME,
            user_id=str(uid),
            tier=user.subscription_tier,
            deadline_s=settings.CHAT_DEADLINE_S,
        )
        replied_at = max(datetime.now(UTC), received_at + timedelta(microseconds=1))
        user_msg = Message(conversation_id=ctx.conv_id, role="user", content=data.content, created_at=received_at)
        ai_msg = Message(
            conversation_id=ctx.conv_id,
            role="assistant",
            content=result["answer"],
            meta=_assistant_meta(result, data.language),
            tokens_used=result.get("tokens_used"),
            created_at=replied_at,
        )
        db.add_all([user_msg, ai_msg])
        await _bump_conversation(db, ctx, data.content, 2, result.get("topic"), set_category=True)
        await db.commit()
        reserved = False  # the reservation is now the consumed unit
    except BaseException:
        if reserved and ctx.quota_window is not None:
            await asyncio.shield(quota_service.release(uid, quota_service.CHAT_REPLY, ctx.quota_window))
        raise
    finally:
        await cache.release_lock(lock_key)
    log.info("chat_reply", extra={"user": user_id_hash(uid), "conversation_id": str(ctx.conv_id), "tokens": result.get("tokens_used")})
    return [message_out(user_msg), message_out(ai_msg)]


async def _bump_conversation(
    db: AsyncSession, ctx: _SendContext, content: str, n: int, topic: Any, *, set_category: bool = False
) -> None:
    values: dict[str, Any] = {"message_count": Conversation.message_count + n, "updated_at": datetime.now(UTC)}
    stmt = update(Conversation).where(Conversation.id == ctx.conv_id)
    if ctx.first:
        values["title"] = func.coalesce(Conversation.title, make_title(content))
        if set_category:  # the stream path sets it once the reply (and its topic) exists
            values["category"] = func.coalesce(Conversation.category, _category(topic))
    await db.execute(stmt.values(**values))


# ------------------------------------------------------------------ H6 send (SSE streaming)
def _sse(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str, separators=(',', ':'))}\n\n"


async def start_stream(db: AsyncSession, user: User, conv_id: uuid.UUID, data: SendMessageIn) -> AsyncIterator[str]:
    """Runs all pre-checks (so errors are normal JSON responses), reserves quota, persists the user
    message, then returns the SSE generator. The generator uses its own short sessions."""
    ctx = await _prepare(db, user, conv_id)
    uid = user.id
    lock_key = await _acquire(ctx.conv_id)
    try:
        ctx.quota_window = await quota_service.reserve(db, user, quota_service.CHAT_REPLY)
    except BaseException:
        await cache.release_lock(lock_key)
        raise
    try:
        user_msg = Message(conversation_id=ctx.conv_id, role="user", content=data.content, created_at=datetime.now(UTC))
        db.add(user_msg)
        await _bump_conversation(db, ctx, data.content, 1, None)
        await db.commit()  # no refresh: it would reopen a transaction that outlives this request
    except BaseException:
        await asyncio.shield(quota_service.release(uid, quota_service.CHAT_REPLY, ctx.quota_window))
        await cache.release_lock(lock_key)
        raise
    return _stream(ctx, lock_key, user_msg, data, uid, user)


async def _stream(
    ctx: _SendContext, lock_key: str, user_msg: Message, data: SendMessageIn, uid: uuid.UUID, user: User
) -> AsyncIterator[str]:
    persisted = False
    try:
        yield _sse("meta", {"user_message": message_out(user_msg).model_dump(mode="json")})
        result: dict[str, Any] | None = None
        async for kind, payload in ai.chat_stream(
            chart_data=ctx.chart_data,
            question=data.content,
            history=ctx.history,
            language=data.language,
            user_id_hash=user_id_hash(uid),
            astrology_system=user.astrology_system,
            display_name=PROVIDER_DISPLAY_NAME,
            user_id=str(user.id),
            tier=user.subscription_tier,
            deadline_s=settings.CHAT_DEADLINE_S,
        ):
            if kind == "delta":
                yield _sse("delta", {"text": payload})
            elif kind == "replace":
                yield _sse("replace", {"text": payload})
            elif kind == "done":
                result = payload
        if result is None:
            raise AIUnavailable()
        async with SessionLocal() as s:
            ai_msg = Message(
                conversation_id=ctx.conv_id,
                role="assistant",
                content=result["answer"],
                meta=_assistant_meta(result, data.language),
                tokens_used=result.get("tokens_used"),
                created_at=max(datetime.now(UTC), user_msg.created_at + timedelta(microseconds=1)),
            )
            s.add(ai_msg)
            values: dict[str, Any] = {"message_count": Conversation.message_count + 1, "updated_at": datetime.now(UTC)}
            if ctx.first:
                values["category"] = func.coalesce(Conversation.category, _category(result.get("topic")))
            await s.execute(update(Conversation).where(Conversation.id == ctx.conv_id).values(**values))
            await s.commit()
            await s.refresh(ai_msg)
        persisted = True
        yield _sse("done", {"assistant_message": message_out(ai_msg).model_dump(mode="json")})
    except AppError as exc:
        yield _sse("error", {"code": exc.code, "detail": exc.detail})
    except Exception:  # noqa: BLE001 - never leak internals into the stream
        log.exception("chat_stream_failed")
        yield _sse("error", {"code": "AI_UNAVAILABLE", "detail": AIUnavailable.detail})
    finally:
        # Runs on normal end, error, and client disconnect (GeneratorExit / CancelledError).
        await asyncio.shield(_stream_cleanup(lock_key, ctx, user_msg.id, persisted, uid))


async def _stream_cleanup(
    lock_key: str, ctx: _SendContext, user_msg_id: uuid.UUID, persisted: bool, uid: uuid.UUID
) -> None:
    try:
        if not persisted:
            if ctx.quota_window is not None:
                await quota_service.release(uid, quota_service.CHAT_REPLY, ctx.quota_window)
            async with SessionLocal() as s:
                res = await s.execute(delete(Message).where(Message.id == user_msg_id))
                if res.rowcount:
                    await s.execute(
                        update(Conversation)
                        .where(Conversation.id == ctx.conv_id)
                        .values(message_count=Conversation.message_count - 1)
                    )
                await s.commit()
    except Exception:  # noqa: BLE001
        log.exception("chat_stream_cleanup_failed")
    finally:
        await cache.release_lock(lock_key)


# ------------------------------------------------------------------ H7 / H8 / H9
async def set_bookmark(db: AsyncSession, user: User, message_id: uuid.UUID, bookmarked: bool) -> MessageOut:
    msg = await _get_owned_message(db, user.id, message_id)
    msg.bookmarked = bookmarked
    await db.commit()
    await db.refresh(msg)
    return message_out(msg)


async def add_feedback(db: AsyncSession, user: User, message_id: uuid.UUID, data: FeedbackIn) -> None:
    msg = await _get_owned_message(db, user.id, message_id)
    if msg.role != "assistant":
        raise NotFound("Message not found.")
    stmt = insert(MessageFeedback).values(
        message_id=msg.id, user_id=user.id, rating=data.rating, reason=data.reason, comment=data.comment
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[MessageFeedback.message_id],
        set_={"rating": data.rating, "reason": data.reason, "comment": data.comment, "created_at": datetime.now(UTC)},
    )
    await db.execute(stmt)
    await db.commit()


async def suggestions(db: AsyncSession, user: User, conversation_id: uuid.UUID | None) -> SuggestionsOut:
    chart: BirthChart | None = None
    if conversation_id is not None:
        conv = await get_owned_conversation(db, user.id, conversation_id)
        if conv.chart_id:
            chart = await db.scalar(select(BirthChart).where(BirthChart.id == conv.chart_id, BirthChart.user_id == user.id))
    if chart is None:
        chart = await chart_service.get_primary(db, user.id)
    out: list[str] = []
    if chart is not None:
        system = user.astrology_system or "vedic"
        data = chart.chart_data or {}
        vedic = data.get("vedic") or {}
        if system == "vedic":
            # Sidereal throughout: Vedic Moon sign (rashi) and dasha, labelled as such.
            moon = next((p.get("rashi_english") for p in vedic.get("planets", []) if p.get("english") == "Moon"), None)
            maha = ((vedic.get("dasha") or {}).get("maha_dasha") or {}).get("current")
            if maha:
                out.append(f"What does my {maha} mahadasha mean for my career?")
            if moon:
                out.append(f"How does my Moon in {moon} (sidereal) shape my emotional needs?")
        else:
            moon = (data.get("moon_sign") or {}).get("sign")
            if moon:
                out.append(f"How does my tropical Moon in {moon} shape my emotional needs?")
        out.append("What should I focus on this month?")
        out.append("What are my strengths in relationships?")
    else:
        out = ["What can my birth chart tell me?", "How do I read my Sun, Moon and rising signs?", "What is a mahadasha?"]
    return SuggestionsOut(suggestions=out[:4])
