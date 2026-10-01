from __future__ import annotations

import uuid
from datetime import date, datetime, time
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from app.schemas.common import CleanName, HHMMTime, InModel, Number, OutModel, _no_control_chars

RelationshipLabel = Literal["self", "partner", "friend", "family", "coworker", "other"]


def parse_birth_time(v: object) -> object:
    """Accept HH:MM or HH:MM:SS (contract 1.2); empty string -> None."""
    if v is None or isinstance(v, time):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        for fmt in ("%H:%M", "%H:%M:%S"):
            try:
                return datetime.strptime(s, fmt).time()
            except ValueError:
                continue
        raise ValueError("Birth time must be HH:MM (24-hour).")
    return v


class BirthInputs(InModel):
    """Shared birth-data fields and their validation (C1 steps 1-4)."""

    name: CleanName = Field(min_length=1, max_length=100)
    date_of_birth: date
    time_of_birth: time | None = None
    has_exact_time: bool = True
    birth_place_name: CleanName = Field(min_length=1, max_length=255)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    timezone: str | None = Field(default=None, max_length=64)  # hint only; resolved server-side
    # v1-add
    dst_fold: Literal[0, 1] | None = None
    utc_offset_override: int | None = Field(default=None, ge=-720, le=840)

    @field_validator("time_of_birth", mode="before")
    @classmethod
    def _time(cls, v: object) -> object:
        return parse_birth_time(v)

    @field_validator("name")
    @classmethod
    def _name(cls, v: str) -> str:
        return _no_control_chars(v)

    @field_validator("date_of_birth")
    @classmethod
    def _date_floor(cls, v: date) -> date:
        # Upper bound (today in the birthplace zone) is checked in chart_service after tz resolution.
        # Engine/ephemeris floor is 1800-01-02 (contract says 1800-01-01; engine range wins).
        if v < date(1800, 1, 2):
            raise ValueError("DATE_OUT_OF_RANGE|Birth date must be on or after 2 January 1800.")
        return v

    @model_validator(mode="after")
    def _location(self) -> "BirthInputs":
        if self.latitude == 0 and self.longitude == 0:
            raise ValueError("INVALID_LOCATION|Please choose a birth place from the list.")
        if self.time_of_birth is None:
            self.has_exact_time = False
        return self


class CreateChartIn(BirthInputs):
    is_primary: bool = False
    relationship: RelationshipLabel | None = None  # v1-add (G-06)


class UpdateChartIn(CreateChartIn):
    pass


class BirthChartOut(OutModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    relationship_label: str
    date_of_birth: date
    time_of_birth: HHMMTime
    has_exact_time: bool
    birth_place_name: str
    latitude: Number
    longitude: Number
    timezone: str
    chart_data: dict[str, Any]
    is_primary: bool
    created_at: datetime
    updated_at: datetime
