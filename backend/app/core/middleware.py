"""Pure-ASGI middleware (streaming-safe): request id, security headers, trailing-slash
normalisation, global per-IP rate limit, and one access-log line per request."""
from __future__ import annotations

import json
import logging
import time
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core import ratelimit
from app.core.config import settings
from app.core.clientip import ip_from_scope
from app.core.logging import request_id_var

log = logging.getLogger("app.access")

SECURITY_HEADERS = [
    (b"strict-transport-security", b"max-age=31536000"),
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    (b"x-frame-options", b"DENY"),
    (b"content-security-policy", b"default-src 'none'; frame-ancestors 'none'"),
]


class PathNormaliseMiddleware:
    """Strip a trailing slash so '/charts/' and '/charts' hit the same route without a 307
    redirect (api-contract 1.1: redirects drop CORS context on some browsers)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            path: str = scope["path"]
            if len(path) > 1 and path.endswith("/"):
                scope = dict(scope)
                scope["path"] = path.rstrip("/") or "/"
                raw = scope.get("raw_path")
                if raw:
                    scope["raw_path"] = raw.rstrip(b"/") or b"/"
        await self.app(scope, receive, send)


class RequestContextMiddleware:
    """Request id + security headers + access log (no PII: path templates only, no query)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        rid = uuid.uuid4().hex[:16]
        token = request_id_var.set(rid)
        start = time.perf_counter()
        status = {"code": 500}

        async def _send(message: Message) -> None:
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
                headers = list(message.get("headers", []))
                present = {k.lower() for k, _ in headers}
                headers += [h for h in SECURITY_HEADERS if h[0] not in present]
                headers.append((b"x-request-id", rid.encode()))
                message["headers"] = headers
            await send(message)

        try:
            await self.app(scope, receive, _send)
        finally:
            route = scope.get("route")
            log.info(
                "request",
                extra={
                    "method": scope.get("method"),
                    "route": getattr(route, "path", "unmatched"),
                    "status": status["code"],
                    "latency_ms": int((time.perf_counter() - start) * 1000),
                },
            )
            request_id_var.reset(token)


class GlobalRateLimitMiddleware:
    """Any route: 120/min per IP (architecture.md section 7). Health checks are exempt."""

    def __init__(self, app: ASGIApp, limit: int = 120, window_s: int = 60) -> None:
        self.app, self.limit, self.window_s = app, limit, window_s

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("method") != "OPTIONS" and not scope["path"].startswith("/health"):
            ip = ip_from_scope(scope)
            if not ratelimit.check("global_ip", ip, self.limit, self.window_s):
                body = json.dumps({"detail": "Too many requests. Please slow down.", "code": "RATE_LIMITED"}).encode()
                await send(
                    {
                        "type": "http.response.start",
                        "status": 429,
                        "headers": [(b"content-type", b"application/json"), (b"retry-after", b"60")],
                    }
                )
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)


class BodyLimitMiddleware:
    """Reject oversized request bodies: early on Content-Length, and while streaming (chunked or
    lying Content-Length) via a counting ``receive``. Over the cap -> 413 PAYLOAD_TOO_LARGE."""

    def __init__(self, app: ASGIApp, max_bytes: int | None = None) -> None:
        self.app = app
        self.max_bytes = max_bytes

    @property
    def limit(self) -> int:
        return self.max_bytes if self.max_bytes is not None else settings.MAX_BODY_BYTES

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        limit = self.limit
        for k, v in scope.get("headers", []):
            if k == b"content-length":
                try:
                    too_big = int(v) > limit
                except ValueError:
                    too_big = True
                if too_big:
                    await self._reject(send)
                    return
        received = 0
        exceeded = False
        started = False

        async def counting_receive() -> Message:
            nonlocal received, exceeded
            if exceeded:
                return {"type": "http.disconnect"}
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    # Do not raise: FastAPI converts body-read exceptions into a 400. Report a
                    # disconnect to the app and send the 413 ourselves.
                    exceeded = True
                    return {"type": "http.disconnect"}
            return message

        async def guarded_send(message: Message) -> None:
            nonlocal started
            if exceeded:
                return  # swallow whatever the app tries to answer with
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        await self.app(scope, counting_receive, guarded_send)
        if exceeded and not started:
            await self._reject(send)

    @staticmethod
    async def _reject(send: Send) -> None:
        body = json.dumps({"detail": "That request is too large.", "code": "PAYLOAD_TOO_LARGE"}).encode()
        await send({"type": "http.response.start", "status": 413,
                    "headers": [(b"content-type", b"application/json"), (b"connection", b"close")]})
        await send({"type": "http.response.body", "body": body})


class CatchAllMiddleware:
    """Turn unhandled exceptions into the standard 500 JSON *inside* the CORS layer. Starlette's own
    500 handler sits outside CORSMiddleware, so a browser would see a CORS failure instead of the error."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        started = False

        async def tracking_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, receive, tracking_send)
        except Exception:  # noqa: BLE001
            logging.getLogger("app.errors").exception("unhandled_error")
            if started:
                raise
            body = json.dumps({"detail": "Something went wrong. Please try again.", "code": "INTERNAL_ERROR"}).encode()
            await send({"type": "http.response.start", "status": 500, "headers": [(b"content-type", b"application/json")]})
            await send({"type": "http.response.body", "body": body})
