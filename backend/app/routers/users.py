from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.core.deps import DB, CurrentUser, rate_limit
from app.schemas.common import MessageOut
from app.schemas.user import ConsentsIn, DeleteAccountIn, UpdateUserIn, UserOut
from app.services import auth_service, user_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_me(db: DB, user: CurrentUser) -> UserOut:
    return await user_service.get_me(db, user)


@router.put("/me", response_model=UserOut, dependencies=[Depends(rate_limit("user_update", 30, 3600))])
async def update_me(body: UpdateUserIn, db: DB, user: CurrentUser) -> UserOut:
    return await user_service.update_me(db, user, body)


@router.put("/me/consents", response_model=UserOut)
async def update_consents(body: ConsentsIn, db: DB, user: CurrentUser) -> UserOut:
    return await user_service.update_consents(db, user, ai_processing=body.ai_processing)


@router.post("/me/deletion-code", response_model=MessageOut)
async def deletion_code(user: CurrentUser) -> MessageOut:
    return MessageOut(message=await auth_service.send_deletion_code(user))


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_me(db: DB, user: CurrentUser, body: DeleteAccountIn | None = None) -> Response:
    body = body or DeleteAccountIn()
    await user_service.delete_me(db, user, password=body.password, code=body.code)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
