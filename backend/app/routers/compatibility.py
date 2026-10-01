from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse

from app.core.deps import DB, CurrentUser, rate_limit
from app.schemas.compatibility import CompatibilityIn, CompatibilityReportOut
from app.services import compatibility_service

router = APIRouter(prefix="/compatibility", tags=["compatibility"])


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=CompatibilityReportOut,
    responses={200: {"model": CompatibilityReportOut, "description": "Identical report from the last 30 days"}},
    dependencies=[Depends(rate_limit("compat_create", 10, 3600))],
)
async def create_report(body: CompatibilityIn, db: DB, user: CurrentUser) -> JSONResponse:
    report, created = await compatibility_service.create_report(db, user, body)
    return JSONResponse(report.model_dump(mode="json"), status_code=201 if created else 200)


@router.get("", response_model=list[CompatibilityReportOut])
async def list_reports(db: DB, user: CurrentUser) -> list[CompatibilityReportOut]:
    return await compatibility_service.list_reports(db, user)


@router.get("/{report_id}", response_model=CompatibilityReportOut)
async def get_report(report_id: uuid.UUID, db: DB, user: CurrentUser) -> CompatibilityReportOut:
    return await compatibility_service.get_report(db, user, report_id)


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_report(report_id: uuid.UUID, db: DB, user: CurrentUser) -> Response:
    await compatibility_service.delete_report(db, user, report_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
