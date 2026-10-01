from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Query

from app.core.deps import rate_limit
from app.services import insight_service

router = APIRouter(prefix="/panchang", tags=["panchang"])


@router.get("", dependencies=[Depends(rate_limit("panchang", 30, 60, per="ip"))])
async def get_panchang(
    day: date = Query(alias="date"), lat: float = Query(ge=-90, le=90), lon: float = Query(ge=-180, le=180)
) -> dict[str, Any]:
    return await insight_service.get_panchang(day, lat, lon)
