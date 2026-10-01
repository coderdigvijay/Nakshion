from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from app.schemas.common import OutModel


class DailyHoroscopeOut(OutModel):
    id: uuid.UUID
    zodiac_sign: str
    date: date
    general_reading: str
    love_reading: str | None
    career_reading: str | None
    wellness_reading: str | None
    lucky_number: int | None
    lucky_color: str | None
    transit_data: dict[str, Any]
    created_at: datetime
    # v1-add
    system: str = "western"
    generated_by: str = "llm"
