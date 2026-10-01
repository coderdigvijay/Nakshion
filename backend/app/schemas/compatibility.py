from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from app.schemas.chart import BirthInputs, parse_birth_time
from app.schemas.common import CleanName, InModel, Number, OutModel

RelationshipType = Literal["romantic", "friend", "family", "coworker"]


class CompatibilityIn(InModel):
    chart1_id: uuid.UUID
    partner_name: CleanName = Field(min_length=1, max_length=100)
    partner_date_of_birth: date
    partner_time_of_birth: time | None = None
    partner_has_exact_time: bool = True
    partner_birth_place_name: CleanName = Field(min_length=1, max_length=255)
    partner_latitude: float = Field(ge=-90, le=90)
    partner_longitude: float = Field(ge=-180, le=180)
    partner_timezone: str | None = Field(default=None, max_length=64)
    relationship_type: RelationshipType
    # v1-add
    partner_ashtakoota_role: Literal["bride", "groom"] | None = None
    self_ashtakoota_role: Literal["bride", "groom"] | None = None

    @field_validator("partner_time_of_birth", mode="before")
    @classmethod
    def _time(cls, v: object) -> object:
        return parse_birth_time(v)

    @model_validator(mode="after")
    def _check(self) -> "CompatibilityIn":
        # Reuse the chart validation rules (single source): build the partner BirthInputs.
        try:
            self.partner_inputs()
        except ValidationError as exc:
            first = exc.errors()[0]
            ctx_err = (first.get("ctx") or {}).get("error")
            raise ValueError(str(ctx_err) if ctx_err else f"Partner details: {first.get('msg')}") from None
        return self

    def partner_inputs(self) -> BirthInputs:
        return BirthInputs(
            name=self.partner_name,
            date_of_birth=self.partner_date_of_birth,
            time_of_birth=self.partner_time_of_birth,
            has_exact_time=self.partner_has_exact_time,
            birth_place_name=self.partner_birth_place_name,
            latitude=self.partner_latitude,
            longitude=self.partner_longitude,
            timezone=self.partner_timezone,
        )


class CompatibilityReportOut(OutModel):
    id: uuid.UUID
    chart1_id: uuid.UUID
    chart2_id: uuid.UUID
    relationship_type: str
    overall_score: Number
    compatibility_data: dict[str, Any]
    partner_name: str
    created_at: datetime
