from __future__ import annotations

from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends

from app.core.deps import DB, CurrentUser, OptionalUser, rate_limit
from app.schemas.horoscope import DailyHoroscopeOut
from app.services import horoscope_service, personal_reading_service

router = APIRouter(prefix="/horoscopes", tags=["horoscopes"])

# Public endpoint that can trigger generation: per-IP limit on top of the global one.
_limit = Depends(rate_limit("horoscope", 60, 60, per="ip"))


@router.get("/daily", response_model=DailyHoroscopeOut, dependencies=[_limit])
async def daily(
    db: DB,
    user: OptionalUser,
    sign: str | None = None,
    date: date | None = None,  # noqa: A002 - query parameter name from the contract
    system: Literal["western", "vedic"] = "western",
) -> dict[str, Any]:
    return await horoscope_service.daily_for_request(db, user, sign, date, system, past_days=1)


@router.get("/daily/{on}", response_model=DailyHoroscopeOut, dependencies=[_limit])
async def daily_on(
    on: date, db: DB, user: OptionalUser, sign: str | None = None, system: Literal["western", "vedic"] = "western"
) -> dict[str, Any]:
    return await horoscope_service.daily_for_request(db, user, sign, on, system, past_days=1)


@router.get("/personal/today", dependencies=[Depends(rate_limit("personal_reading", 30, 3600))])
async def personal_today(db: DB, user: CurrentUser) -> dict[str, Any]:
    return await personal_reading_service.get_today(db, user)
