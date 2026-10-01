from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services import health_service

router = APIRouter(tags=["health"])


@router.get("/health")
@router.get("/health/live")
async def live() -> dict[str, str]:
    return health_service.live()


@router.get("/health/ready")
async def ready() -> JSONResponse:
    ok, checks = await health_service.ready()
    return JSONResponse({"status": "ok" if ok else "degraded", "checks": checks}, status_code=200 if ok else 503)
