from __future__ import annotations

import uuid
from datetime import date
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query, Response, status

from app.core.deps import DB, CurrentUser, rate_limit
from app.schemas.chart import BirthChartOut, CreateChartIn, UpdateChartIn
from app.services import chart_service, insight_service

# Registered without trailing slash; PathNormaliseMiddleware makes "/charts/" hit the same route.
router = APIRouter(prefix="/charts", tags=["charts"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=BirthChartOut,
    dependencies=[Depends(rate_limit("chart_create", 20, 3600))],
)
async def create_chart(body: CreateChartIn, db: DB, user: CurrentUser) -> BirthChartOut:
    return await chart_service.create_chart(db, user, body)


@router.get("", response_model=list[BirthChartOut])
async def list_charts(
    db: DB, user: CurrentUser, relationship: Literal["self", "partner", "friend", "family", "coworker", "other"] | None = None
) -> list[BirthChartOut]:
    return await chart_service.list_charts(db, user, relationship)


@router.get("/{chart_id}", response_model=BirthChartOut)
async def get_chart(chart_id: uuid.UUID, db: DB, user: CurrentUser) -> BirthChartOut:
    return await chart_service.get_chart(db, user, chart_id)


@router.put("/{chart_id}", response_model=BirthChartOut, dependencies=[Depends(rate_limit("chart_create", 20, 3600))])
async def update_chart(chart_id: uuid.UUID, body: UpdateChartIn, db: DB, user: CurrentUser) -> BirthChartOut:
    return await chart_service.update_chart(db, user, chart_id, body)


@router.delete("/{chart_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chart(chart_id: uuid.UUID, db: DB, user: CurrentUser) -> Response:
    await chart_service.delete_chart(db, user, chart_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{chart_id}/primary", response_model=BirthChartOut)
async def set_primary(chart_id: uuid.UUID, db: DB, user: CurrentUser) -> BirthChartOut:
    return await chart_service.set_primary(db, user, chart_id)


@router.get("/{chart_id}/transits", dependencies=[Depends(rate_limit("chart_insight", 60, 60))])
async def transits(
    chart_id: uuid.UUID, db: DB, user: CurrentUser, from_: date | None = Query(None, alias="from"),
    days: int = Query(1, ge=1, le=90),
) -> dict[str, Any]:
    return await insight_service.get_transits(db, user, chart_id, from_, days)


@router.get("/{chart_id}/dasha", dependencies=[Depends(rate_limit("chart_insight", 60, 60))])
async def dasha(chart_id: uuid.UUID, db: DB, user: CurrentUser, levels: int = Query(2, ge=2, le=3)) -> dict[str, Any]:
    return await insight_service.get_dasha(db, user, chart_id, levels)
