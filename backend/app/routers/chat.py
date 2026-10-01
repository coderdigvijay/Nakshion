from __future__ import annotations

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import StreamingResponse

from app.core.deps import DB, CurrentUser, rate_limit
from app.schemas.chat import (
    BookmarkIn,
    ConversationDetailOut,
    ConversationOut,
    CreateConversationIn,
    FeedbackIn,
    MessageOut,
    SendMessageIn,
    SuggestionsOut,
    UpdateConversationIn,
)
from app.services import chat_service

router = APIRouter(prefix="/chat", tags=["chat"])

_send_limit = Depends(rate_limit("chat_send", 6, 60))


@router.post(
    "/conversations",
    status_code=status.HTTP_201_CREATED,
    response_model=ConversationOut,
    dependencies=[Depends(rate_limit("conv_create", 30, 3600))],
)
async def create_conversation(db: DB, user: CurrentUser, body: CreateConversationIn | None = None) -> ConversationOut:
    return await chat_service.create_conversation(db, user, body or CreateConversationIn())


@router.get("/conversations", response_model=list[ConversationOut])
async def list_conversations(
    db: DB, user: CurrentUser, limit: int = Query(50, ge=1, le=50), before: datetime | None = None
) -> list[ConversationOut]:
    return await chat_service.list_conversations(db, user, limit, before)


@router.get("/conversations/{conv_id}", response_model=ConversationDetailOut)
async def get_conversation(conv_id: uuid.UUID, db: DB, user: CurrentUser) -> ConversationDetailOut:
    return await chat_service.get_conversation(db, user, conv_id)


@router.patch("/conversations/{conv_id}", response_model=ConversationOut)
async def update_conversation(conv_id: uuid.UUID, body: UpdateConversationIn, db: DB, user: CurrentUser) -> ConversationOut:
    return await chat_service.update_conversation(db, user, conv_id, body)


@router.delete("/conversations/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conv_id: uuid.UUID, db: DB, user: CurrentUser) -> Response:
    await chat_service.delete_conversation(db, user, conv_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/conversations/{conv_id}/messages", response_model=list[MessageOut], dependencies=[_send_limit])
async def send_message(conv_id: uuid.UUID, body: SendMessageIn, db: DB, user: CurrentUser) -> list[MessageOut]:
    return await chat_service.send_message(db, user, conv_id, body)


@router.post("/conversations/{conv_id}/messages/stream", dependencies=[_send_limit])
async def send_message_stream(conv_id: uuid.UUID, body: SendMessageIn, db: DB, user: CurrentUser) -> StreamingResponse:
    events = await chat_service.start_stream(db, user, conv_id, body)
    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.put("/messages/{message_id}/bookmark", response_model=MessageOut)
async def bookmark(message_id: uuid.UUID, body: BookmarkIn, db: DB, user: CurrentUser) -> MessageOut:
    return await chat_service.set_bookmark(db, user, message_id, body.bookmarked)


@router.post("/messages/{message_id}/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def feedback(message_id: uuid.UUID, body: FeedbackIn, db: DB, user: CurrentUser) -> Response:
    await chat_service.add_feedback(db, user, message_id, body)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/suggestions", response_model=SuggestionsOut)
async def suggestions(db: DB, user: CurrentUser, conversation_id: uuid.UUID | None = None) -> SuggestionsOut:
    return await chat_service.suggestions(db, user, conversation_id)
