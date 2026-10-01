"""Scheduled jobs triggered by cron-job.org (architecture.md section 8)."""
from __future__ import annotations

import asyncio
import hmac
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from app.core import ratelimit
from app.core.config import settings
from app.core.errors import NotFound, RateLimited, Unauthenticated
from app.db.session import SessionLocal
from app.services import auth_service, horoscope_service

log = logging.getLogger("app.cron")

# "hourly" is kept as an alias of "daily_maintenance". Schedule maintenance ONCE A DAY: every DB touch keeps
# Neon compute awake for 5 minutes, and the free plan has a 100 CU-hour monthly budget.
JOBS = ("pregen_horoscopes", "daily_maintenance", "hourly")


# Strong references so a fire-and-forget pregeneration task is not garbage-collected mid-run.
_background: set[asyncio.Task] = set()


async def _pregenerate_in_background(on) -> None:
    try:
        result = await horoscope_service.pregenerate(on)
        log.info("cron_done", extra={"job": "pregen_horoscopes", **result})
    except Exception:  # noqa: BLE001 - nobody awaits this task; log instead of losing the error
        log.exception("cron_failed", extra={"job": "pregen_horoscopes"})


def authorise(secret: str | None, job: str) -> None:
    expected = settings.CRON_SECRET
    if not expected or not secret or not hmac.compare_digest(secret.encode(), expected.encode()):
        raise Unauthenticated("Invalid cron secret.")
    if job not in JOBS:
        raise NotFound("Unknown job.")
    if not ratelimit.check("cron", job, 1, 300):
        raise RateLimited("This job already ran in the last 5 minutes.", retry_after=300)


async def run(secret: str | None, job: str) -> dict:
    authorise(secret, job)
    if job == "pregen_horoscopes":
        # 24 LLM generations take far longer than cron-job.org's 30 s limit, so answer immediately and
        # finish the work in the background (the instance stays alive: single worker + keep-awake ping).
        task = asyncio.create_task(_pregenerate_in_background((datetime.now(UTC) + timedelta(days=1)).date()))
        _background.add(task)
        task.add_done_callback(_background.discard)
        return {"job": job, "status": "started"}
    else:
        resets = await auth_service.purge_expired_resets()
        async with SessionLocal() as s:
            res = await s.execute(text("DELETE FROM personal_readings WHERE date < current_date - 90"))
            usage = await s.execute(text("DELETE FROM llm_usage WHERE created_at < now() - interval '180 days'"))
            counters = await s.execute(text("DELETE FROM usage_counters WHERE period_start < current_date - 90"))
            await s.commit()
        result = {
            "password_resets_deleted": resets,
            "personal_readings_deleted": int(res.rowcount or 0),
            "llm_usage_deleted": int(usage.rowcount or 0),
            "usage_counters_deleted": int(counters.rowcount or 0),
        }
    log.info("cron_done", extra={"job": job, **result})
    return {"job": job, **result}
