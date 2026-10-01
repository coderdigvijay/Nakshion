from __future__ import annotations

import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Numeric, String, Time, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BirthChart(Base):
    __tablename__ = "birth_charts"
    __table_args__ = (
        Index("uq_birth_charts_one_primary", "user_id", unique=True, postgresql_where=text("is_primary")),
        Index("ix_birth_charts_user_order", "user_id", text("is_primary DESC"), "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # DB column "relationship"; API field "relationship_label" (gap G-06).
    relationship: Mapped[str] = mapped_column(String(50), nullable=False, server_default="self", default="self")
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    time_of_birth: Mapped[time | None] = mapped_column(Time, nullable=True)
    has_exact_time: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("true"), default=True)
    birth_place_name: Mapped[str] = mapped_column(String(255), nullable=False)
    latitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    longitude: Mapped[Decimal] = mapped_column(Numeric(10, 7), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False)
    chart_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"), default=False)
    engine_version: Mapped[str] = mapped_column(String(20), nullable=False, server_default="0.0.0", default="0.0.0")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
