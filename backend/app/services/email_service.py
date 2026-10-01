"""Transactional email via Brevo (OTP, password reset, deletion confirmation).

Sends run as background tasks (5 s timeout, 3 attempts with backoff) so a slow or failing
Brevo never blocks or fails the user's request (api-contract A1: user is still created).
Without BREVO_API_KEY (dev/test) the email is logged as skipped, never its content.
"""
from __future__ import annotations

import asyncio
import html
import logging

import httpx

from app.core.config import settings

log = logging.getLogger("app.email")

BREVO_URL = "https://api.brevo.com/v3/smtp/email"
_background: set[asyncio.Task] = set()

# Test hook: when set, outgoing emails are appended here instead of sent.
outbox: list[dict] | None = None


def _payload(to_email: str, to_name: str | None, subject: str, text: str, tag: str) -> dict:
    body_html = "".join(f"<p>{html.escape(p)}</p>" for p in text.split("\n\n"))
    footer = f"<p style='color:#888;font-size:12px'>{html.escape(settings.APP_NAME)}. If you didn't request this, you can ignore this email.</p>"
    return {
        "sender": {"email": settings.EMAIL_SENDER_ADDRESS, "name": settings.EMAIL_SENDER_NAME},
        "to": [{"email": to_email, **({"name": to_name} if to_name else {})}],
        "subject": subject,
        "textContent": text + "\n\nIf you didn't request this, you can ignore this email.",
        "htmlContent": f"<html><body>{body_html}{footer}</body></html>",
        "headers": {"X-Mailin-Tag": tag},
        "tags": [tag],
    }


async def _deliver(payload: dict, tag: str) -> bool:
    if outbox is not None:
        outbox.append(payload)
        return True
    if not settings.BREVO_API_KEY:
        log.info("email_skipped_no_api_key", extra={"tag": tag})
        return False
    if not settings.EMAIL_SENDER_ADDRESS:
        log.error("email_send_failed", extra={"tag": tag, "reason": "EMAIL_SENDER_ADDRESS not configured"})
        return False
    headers = {"api-key": settings.BREVO_API_KEY, "accept": "application/json", "content-type": "application/json"}
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(BREVO_URL, json=payload, headers=headers)
            if resp.status_code < 300:
                log.info("email_sent", extra={"tag": tag, "status": resp.status_code})
                return True
            if 400 <= resp.status_code < 500 and resp.status_code != 429:
                # Brevo's error code only (e.g. "unauthorized" = key invalid or IP not allow-listed,
                # "invalid_parameter" = unverified sender). Never the key, address or body.
                try:
                    brevo_code = str(resp.json().get("code", ""))[:40]
                except ValueError:
                    brevo_code = ""
                log.error("email_send_failed", extra={"tag": tag, "status": resp.status_code, "brevo_code": brevo_code})
                return False
        except httpx.HTTPError as exc:
            log.warning("email_send_retry", extra={"tag": tag, "err": type(exc).__name__, "attempt": attempt})
        await asyncio.sleep(0.5 * (2**attempt))
    log.error("email_send_failed", extra={"tag": tag})
    return False


def _fire(payload: dict, tag: str) -> None:
    task = asyncio.create_task(_deliver(payload, tag))
    _background.add(task)
    task.add_done_callback(_background.discard)


def send_otp(to_email: str, to_name: str | None, code: str) -> None:
    text = (
        f"Your {settings.APP_NAME} verification code is {code}.\n\n"
        "It expires in 10 minutes. Log in and enter this code on the verification page."
    )
    _fire(_payload(to_email, to_name, f"Your {settings.APP_NAME} verification code", text, "otp"), "otp")


def send_password_reset(to_email: str, to_name: str | None, raw_token: str) -> None:
    link = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={raw_token}"
    text = (
        f"We received a request to reset your {settings.APP_NAME} password.\n\n"
        f"Reset it here (valid for 1 hour): {link}"
    )
    _fire(_payload(to_email, to_name, f"Reset your {settings.APP_NAME} password", text, "password_reset"), "password_reset")


def send_deletion_code(to_email: str, to_name: str | None, code: str) -> None:
    text = (
        f"Your {settings.APP_NAME} account deletion code is {code}.\n\n"
        "It expires in 10 minutes. Deleting your account permanently removes all your charts and conversations."
    )
    _fire(_payload(to_email, to_name, f"Confirm deleting your {settings.APP_NAME} account", text, "delete_code"), "delete_code")


def send_account_deleted(to_email: str, to_name: str | None) -> None:
    text = (
        f"Your {settings.APP_NAME} account and all its data (charts, conversations, reports) "
        "have been permanently deleted."
    )
    _fire(_payload(to_email, to_name, f"Your {settings.APP_NAME} account was deleted", text, "account_deleted"), "account_deleted")


async def drain() -> None:
    """Await pending sends (tests / graceful shutdown)."""
    if _background:
        await asyncio.gather(*list(_background), return_exceptions=True)
