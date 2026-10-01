"""A primary chart must be the user's own ('self') chart (invariant in the database)

Revision ID: 009
Revises: 008
Create Date: 2026-10-01

Added NOT VALID then validated; if legacy rows break it (a saved person marked primary) it stays NOT VALID,
which still blocks new violations, and a NOTICE is raised. No data is rewritten. Downgrade drops the constraint.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_chart_primary_is_self') THEN
            ALTER TABLE birth_charts ADD CONSTRAINT ck_chart_primary_is_self
              CHECK (NOT is_primary OR relationship = 'self') NOT VALID;
          END IF;
          BEGIN
            ALTER TABLE birth_charts VALIDATE CONSTRAINT ck_chart_primary_is_self;
          EXCEPTION WHEN check_violation THEN
            RAISE NOTICE 'ck_chart_primary_is_self left NOT VALID: legacy primary charts are not labelled self';
          END;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE birth_charts DROP CONSTRAINT IF EXISTS ck_chart_primary_is_self")
