"""Add compatibility_reports table

Revision ID: 002
Revises: 001
Create Date: 2026-03-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "compatibility_reports",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("chart1_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("birth_charts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("chart2_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("birth_charts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relationship_type", sa.String(50), nullable=False, server_default="romantic"),
        sa.Column("overall_score", sa.Numeric(3, 1), nullable=False),
        sa.Column("compatibility_data", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("compatibility_reports")
