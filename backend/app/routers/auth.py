from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import RedirectResponse

from app.core.deps import DB, CurrentUser, client_ip, rate_limit
from app.schemas.auth import (
    ChangePasswordIn,
    ForgotPasswordIn,
    LoginIn,
    PasswordChangedOut,
    OAuthExchangeIn,
    RegisterIn,
    ResetPasswordIn,
    SetPasswordIn,
    TokenOut,
    VerifyEmailIn,
)
from app.schemas.common import MessageOut
from app.schemas.user import UserOut
from app.services import auth_service, oauth_google, user_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=TokenOut,
    dependencies=[Depends(rate_limit("register", 5, 3600, per="ip"))],
)
async def register(body: RegisterIn, db: DB) -> TokenOut:
    token = await auth_service.register(
        db, email=body.email, password=body.password, name=body.name,
        terms_accepted=body.terms_accepted, age_confirmed=body.age_confirmed,
    )
    return TokenOut(access_token=token)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, db: DB, request: Request) -> TokenOut:
    return TokenOut(access_token=await auth_service.login(db, email=body.email, password=body.password, ip=client_ip(request)))


@router.post("/verify-email", response_model=MessageOut, dependencies=[Depends(rate_limit("verify_ip", 20, 600, per="ip"))])
async def verify_email(body: VerifyEmailIn, db: DB, user: CurrentUser) -> MessageOut:
    return MessageOut(message=await auth_service.verify_email(db, user, body.code))


@router.post("/resend-otp", response_model=MessageOut)
async def resend_otp(user: CurrentUser) -> MessageOut:
    return MessageOut(message=await auth_service.resend_otp(user))


@router.post("/forgot-password", response_model=MessageOut)
async def forgot_password(body: ForgotPasswordIn, db: DB, request: Request) -> MessageOut:
    return MessageOut(message=await auth_service.forgot_password(db, email=body.email, ip=client_ip(request)))


@router.post("/reset-password", response_model=MessageOut, dependencies=[Depends(rate_limit("reset_ip", 10, 900, per="ip"))])
async def reset_password(body: ResetPasswordIn, db: DB) -> MessageOut:
    return MessageOut(message=await auth_service.reset_password(db, token=body.token, new_password=body.new_password))


@router.get("/me", response_model=UserOut)
async def me(db: DB, user: CurrentUser) -> UserOut:
    return await user_service.get_me(db, user)


@router.get("/oauth/google", dependencies=[Depends(rate_limit("oauth_start", 20, 600, per="ip"))])
async def oauth_google_start(terms: bool = False) -> RedirectResponse:
    # ?terms=1 : the user ticked the Terms/Privacy checkbox on our page (required to create a NEW account)
    return RedirectResponse(await oauth_google.authorization_url(terms), status_code=302)


@router.get("/oauth/google/callback")
async def oauth_google_callback(db: DB, code: str | None = None, state: str | None = None, error: str | None = None) -> RedirectResponse:
    url = await oauth_google.handle_callback(db, code=code, state=state, error=error)
    return RedirectResponse(url, status_code=302, headers={"Referrer-Policy": "no-referrer", "Cache-Control": "no-store"})


@router.post(
    "/oauth/exchange", response_model=TokenOut, dependencies=[Depends(rate_limit("oauth_exchange", 20, 600, per="ip"))]
)
async def oauth_exchange(body: OAuthExchangeIn, db: DB) -> TokenOut:
    return TokenOut(access_token=await oauth_google.exchange_login_code(db, body.code))


@router.post("/change-password", response_model=PasswordChangedOut)
async def change_password(body: ChangePasswordIn, db: DB, user: CurrentUser) -> PasswordChangedOut:
    message, token = await auth_service.change_password(
        db, user, current_password=body.current_password, new_password=body.new_password
    )
    return PasswordChangedOut(message=message, access_token=token)


@router.post("/set-password", response_model=MessageOut)
async def set_password(body: SetPasswordIn, db: DB, user: CurrentUser) -> MessageOut:
    return MessageOut(message=await auth_service.set_password(db, user, new_password=body.new_password))


@router.post("/logout-all", response_model=MessageOut)
async def logout_all(db: DB, user: CurrentUser) -> MessageOut:
    return MessageOut(message=await auth_service.logout_all(db, user))
