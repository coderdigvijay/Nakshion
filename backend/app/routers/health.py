from __future__ import annotations

import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.deps import rate_limit
from app.services import health_service

router = APIRouter(tags=["health"])


@router.get("/health")
@router.get("/health/live")
async def live() -> dict[str, str]:
    return health_service.live()


@router.get("/health/ready", dependencies=[Depends(rate_limit("health_ready", 10, 60, per="ip"))])
async def ready(x_cron_secret: Annotated[str | None, Header()] = None) -> JSONResponse:
    """Public: only {"status": "ok" | "degraded"}. The per-dependency detail (database, redis, engine, rag) is
    returned only with the X-Cron-Secret header, so an anonymous caller learns nothing about internals."""
    ok, checks = await health_service.ready()
    body: dict = {"status": "ok" if ok else "degraded"}
    secret = settings.CRON_SECRET
    if secret and x_cron_secret and hmac.compare_digest(x_cron_secret.encode(), secret.encode()):
        body["checks"] = checks
    return JSONResponse(body, status_code=200 if ok else 503)
