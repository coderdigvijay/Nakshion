from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Header

from app.services import cron_service

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)


@router.post("/cron/{job}")
async def run_cron(job: str, x_cron_secret: Annotated[str | None, Header()] = None) -> dict:
    return await cron_service.run(x_cron_secret, job)
