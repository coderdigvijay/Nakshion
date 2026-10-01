from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DailyHoroscope(Base):
    __tablename__ = "daily_horoscopes"
    __table_args__ = (UniqueConstraint("zodiac_sign", "date", "system", name="uq_horoscope_sign_date_system"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    zodiac_sign: Mapped[str] = mapped_column(String(20), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    system: Mapped[str] = mapped_column(String(10), nullable=False, server_default="western", default="western")
    transit_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    general_reading: Mapped[str] = mapped_column(Text, nullable=False)
    love_reading: Mapped[str | None] = mapped_column(Text, nullable=True)
    career_reading: Mapped[str | None] = mapped_column(Text, nullable=True)
    wellness_reading: Mapped[str | None] = mapped_column(Text, nullable=True)
    lucky_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    lucky_color: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class PersonalReading(Base):
    __tablename__ = "personal_readings"
    __table_args__ = (Index("ix_personal_readings_date", "date"), Index("ix_personal_readings_chart", "chart_id"))

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    date: Mapped[date] = mapped_column(Date, primary_key=True)
    system: Mapped[str] = mapped_column(String(10), primary_key=True)
    chart_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("birth_charts.id", ondelete="SET NULL"), nullable=True
    )
    reading: Mapped[dict] = mapped_column(JSONB, nullable=False)
    generated_by: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
