from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CompatibilityReport(Base):
    __tablename__ = "compatibility_reports"
    __table_args__ = (
        Index("ix_compat_user_created", "user_id", text("created_at DESC")),
        Index("ix_compat_dedupe", "user_id", "chart1_id", "chart2_id", "relationship_type", text("created_at DESC")),
        Index("ix_compat_chart1", "chart1_id"),
        Index("ix_compat_chart2", "chart2_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    chart1_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("birth_charts.id", ondelete="CASCADE"), nullable=False
    )
    chart2_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("birth_charts.id", ondelete="CASCADE"), nullable=False
    )
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False, server_default="romantic")
    overall_score: Mapped[Decimal] = mapped_column(Numeric(3, 1), nullable=False)
    compatibility_data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
