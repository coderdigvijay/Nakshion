"""Domain exceptions and the single module that maps them to HTTP responses.

Every error body is ``{"detail": str, "code": str, "errors"?: [...]}`` (api-contract.md 1.3).
Services raise ``AppError`` subclasses; they never raise HTTPException.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import InterfaceError, OperationalError
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("app.errors")


class AppError(Exception):
    status: int = 500
    code: str = "INTERNAL_ERROR"
    detail: str = "Something went wrong. Please try again."

    def __init__(
        self,
        detail: str | None = None,
        *,
        code: str | None = None,
        status: int | None = None,
        errors: list[dict[str, str]] | None = None,
        headers: dict[str, str] | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        if detail is not None:
            self.detail = detail
        if code is not None:
            self.code = code
        if status is not None:
            self.status = status
        self.errors = errors
        self.extra = extra or {}
        self.headers = headers
        super().__init__(self.detail)


class BadRequest(AppError):
    status, code, detail = 400, "BAD_REQUEST", "Invalid request."


class Unauthenticated(AppError):
    status, code, detail = 401, "UNAUTHENTICATED", "Please log in again."


class Forbidden(AppError):
    status, code, detail = 403, "FORBIDDEN", "You are not allowed to do that."


class NotFound(AppError):
    status, code, detail = 404, "NOT_FOUND", "Not found."


class Conflict(AppError):
    status, code, detail = 409, "CONFLICT", "That conflicts with the current state."


class ValidationFailed(AppError):
    status, code, detail = 422, "VALIDATION_ERROR", "Please check your input."


class RateLimited(AppError):
    status, code, detail = 429, "RATE_LIMITED", "Too many requests. Please slow down."

    def __init__(
        self, detail: str | None = None, *, retry_after: int = 60, code: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail, code=code, headers={"Retry-After": str(max(1, int(retry_after)))}, extra=extra)


class QuotaExceeded(RateLimited):
    code = "QUOTA_EXCEEDED"
    detail = "You've reached your limit for now."


class UpstreamUnavailable(AppError):
    status, code, detail = 503, "DEPENDENCY_UNAVAILABLE", "A service we depend on is unavailable. Please try again shortly."

    def __init__(self, detail: str | None = None, **kw: Any) -> None:
        kw.setdefault("headers", {"Retry-After": "10"})  # every 503 tells the client when to retry
        super().__init__(detail, **kw)


class AIUnavailable(UpstreamUnavailable):
    code = "AI_UNAVAILABLE"
    detail = "The stars are obscured right now. Please try again in a moment."


class ChartCalculationFailed(AppError):
    status, code, detail = 500, "CHART_CALCULATION_FAILED", "We couldn't calculate this chart. Please check the birth details."


def _body(detail: str, code: str, errors: list[dict[str, Any]] | None = None,
          extra: dict[str, Any] | None = None) -> dict[str, Any]:
    body: dict[str, Any] = {"detail": detail, "code": code}
    if errors:
        body["errors"] = errors
    if extra:
        body.update(extra)
    return body


# Pydantic error-type -> contract code, for fields whose constraint maps to a named code.
_FIELD_CODES = {
    ("content", "string_too_long"): ("MESSAGE_TOO_LONG", "Please keep questions under 2000 characters."),
}

_STATUS_CODES = {400: "BAD_REQUEST", 401: "UNAUTHENTICATED", 403: "FORBIDDEN", 404: "NOT_FOUND",
                 405: "METHOD_NOT_ALLOWED", 409: "CONFLICT", 429: "RATE_LIMITED"}


def _field_name(loc: tuple[Any, ...]) -> str:
    parts = [str(p) for p in loc if p not in ("body", "query", "path", "header")]
    return ".".join(parts) or "request"


_FIELD_MESSAGES = {"email": "Please enter a valid email address."}


def _label(field: str) -> str:
    leaf = field.split(".")[-1].replace("_", " ").strip()
    return (leaf[:1].upper() + leaf[1:]) if leaf else "This field"


def _num(v: Any) -> str:
    return str(int(v)) if isinstance(v, (int, float)) and float(v).is_integer() else str(v)


def _humanise(err: dict[str, Any]) -> str:
    """Plain per-field copy; never Pydantic's wording ("at most 100 items")."""
    typ = str(err.get("type", ""))
    ctx = err.get("ctx") or {}
    field = _field_name(tuple(err.get("loc", ())))
    leaf = field.split(".")[-1]
    label = _label(field)
    msg = str(err.get("msg", "Invalid value"))
    for prefix in ("Value error, ", "Assertion failed, "):
        if msg.startswith(prefix):
            return msg[len(prefix):]
    if leaf in _FIELD_MESSAGES and typ not in ("missing", "extra_forbidden"):
        return _FIELD_MESSAGES[leaf]
    if typ == "missing":
        return f"{label} is required."
    if typ == "extra_forbidden":
        return f"Unexpected field: {field}."
    if typ in ("string_too_long", "too_long"):
        return f"{label} must be {_num(ctx.get('max_length'))} characters or fewer."
    if typ in ("string_too_short", "too_short"):
        n = ctx.get("min_length")
        return f"{label} is required." if n in (1, None) else f"{label} must be at least {_num(n)} characters."
    if typ in ("greater_than_equal", "greater_than"):
        return f"{label} must be at least {_num(ctx.get('ge', ctx.get('gt')))}."
    if typ in ("less_than_equal", "less_than"):
        return f"{label} must be at most {_num(ctx.get('le', ctx.get('lt')))}."
    if typ == "string_pattern_mismatch":
        return f"{label} is not in the expected format."
    if typ in ("date_parsing", "date_from_datetime_parsing", "date_type"):
        return f"{label} must be a valid date (YYYY-MM-DD)."
    if typ in ("time_parsing", "time_type"):
        return f"{label} must be a valid time (HH:MM)."
    if typ in ("uuid_parsing", "uuid_type"):
        return f"{label} is not valid."
    if typ in ("literal_error", "enum"):
        return f"{label} has an unsupported value."
    if typ.endswith("_type") or typ.endswith("_parsing"):
        return f"{label} has the wrong format."
    return f"{label} is not valid."


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        if exc.status >= 500:
            log.error("app_error", extra={"code": exc.code})
        return JSONResponse(_body(exc.detail, exc.code, exc.errors, exc.extra), status_code=exc.status, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        errs = exc.errors()
        if errs and all(e.get("loc", ("",))[0] == "path" for e in errs):
            # A malformed id in the URL (e.g. /compatibility/not-a-uuid) is "no such resource", not a retryable 422.
            return JSONResponse(_body("Not found.", "NOT_FOUND"), status_code=404)
        if any(e.get("type") == "json_invalid" for e in errs):
            msg = "Request body isn't valid JSON."  # loc is a byte offset, never a field name
            return JSONResponse(_body(msg, "VALIDATION_ERROR", [{"field": "body", "message": msg}]), status_code=422)
        errors: list[dict[str, str]] = []
        code = "VALIDATION_ERROR"
        for i, err in enumerate(exc.errors()):
            field = _field_name(tuple(err.get("loc", ())))
            message = _humanise(err)
            # A ValueError raised by a validator may carry "CODE|message".
            ctx_err = (err.get("ctx") or {}).get("error")
            if isinstance(ctx_err, Exception) and "|" in str(ctx_err):
                c, m = str(ctx_err).split("|", 1)
                if c.isupper():
                    message = m
                    if i == 0:
                        code = c
            mapped = _FIELD_CODES.get((field.split(".")[-1], str(err.get("type"))))
            if mapped:
                message = mapped[1]
                if i == 0:
                    code = mapped[0]
            errors.append({"field": field, "message": message})
        detail = errors[0]["message"] if errors else "Please check your input."
        return JSONResponse(_body(detail, code, errors), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
        if exc.status_code == 404:
            detail = "Not found."
        return JSONResponse(
            _body(detail, _STATUS_CODES.get(exc.status_code, "HTTP_ERROR")),
            status_code=exc.status_code,
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(OperationalError)
    @app.exception_handler(InterfaceError)
    @app.exception_handler(ConnectionError)
    @app.exception_handler(TimeoutError)
    async def _db_unavailable(_: Request, exc: Exception) -> JSONResponse:
        # Neon scales to zero after 5 idle minutes; the first connection can be slow or time out.
        # Tell the client plainly (and that it is retryable) instead of a generic 500.
        log.warning("database_unavailable", extra={"exc_type": type(exc).__name__})
        return JSONResponse(
            _body("The database is waking up. Please try again in a few seconds.", "DEPENDENCY_UNAVAILABLE"),
            status_code=503,
            headers={"Retry-After": "5"},
        )

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled_error", extra={"exc_type": type(exc).__name__})
        return JSONResponse(_body("Something went wrong. Please try again.", "INTERNAL_ERROR"), status_code=500)
