from __future__ import annotations

from typing import Annotated

from pydantic import AfterValidator, EmailStr, Field, field_validator

from app.core.security import password_policy_error
from app.schemas.common import CleanName, InModel, OutModel, _no_control_chars


def _policy(v: str) -> str:
    err = password_policy_error(v)
    if err:
        raise ValueError(err)
    return v


NewPassword = Annotated[str, AfterValidator(_policy)]


class _EmailIn(InModel):
    email: EmailStr = Field(max_length=255)

    @field_validator("email", mode="before")
    @classmethod
    def _lower(cls, v: object) -> object:
        return v.strip().lower() if isinstance(v, str) else v


class RegisterIn(_EmailIn):
    # Passwords are NOT stripped: whitespace is significant.
    password: NewPassword
    name: CleanName = Field(min_length=1, max_length=100)
    terms_accepted: bool = Field(default=False, validate_default=True)  # absent == not accepted (validator runs on the default)
    age_confirmed: bool | None = None

    @field_validator("terms_accepted")
    @classmethod
    def _terms(cls, v: bool) -> bool:
        if v is not True:
            raise ValueError("TERMS_NOT_ACCEPTED|Please accept the Terms and Privacy Policy to create an account.")
        return v

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return _no_control_chars(v)


class LoginIn(_EmailIn):
    password: str = Field(min_length=1, max_length=1024)


class VerifyEmailIn(InModel):
    code: str = Field(pattern=r"^\d{6}$")


class ForgotPasswordIn(_EmailIn):
    pass


class ResetPasswordIn(InModel):
    token: str = Field(min_length=10, max_length=200)
    new_password: NewPassword


class ChangePasswordIn(InModel):
    current_password: str = Field(min_length=1, max_length=1024)
    new_password: NewPassword


class SetPasswordIn(InModel):
    new_password: NewPassword


class TokenOut(OutModel):
    access_token: str
    token_type: str = "bearer"


class OAuthExchangeIn(InModel):
    code: str = Field(min_length=20, max_length=100)


class PasswordChangedOut(OutModel):
    message: str
    access_token: str  # fresh token: the old one (and every other session) is revoked by the change
    token_type: str = "bearer"
