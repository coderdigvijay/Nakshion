from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import AfterValidator, BeforeValidator
from fastapi import Query

from app.core.deps import CurrentUser, rate_limit
from app.schemas.geocoding import GeocodingOut
from app.services import geocoding_service

router = APIRouter(prefix="/geocoding", tags=["geocoding"])


def _len_check(v: str) -> str:
    if not 3 <= len(v) <= 100:
        raise ValueError("Search needs 3 to 100 characters.")
    return v


SearchQuery = Annotated[
    str,
    BeforeValidator(lambda v: v.strip() if isinstance(v, str) else v),
    AfterValidator(_len_check),
    Query(),
]


@router.get("/search", response_model=GeocodingOut, dependencies=[Depends(rate_limit("geocode", 30, 60))])
async def search(q: SearchQuery, user: CurrentUser) -> GeocodingOut:  # noqa: ARG001 - auth required (metered API)
    return await geocoding_service.search(q)
