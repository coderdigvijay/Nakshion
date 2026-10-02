"""Record which version of the Terms/Privacy Policy a user accepted

Revision ID: 010
Revises: 009
Create Date: 2026-10-02

Nullable on purpose: existing users have no recorded version. Idempotent and reversible
(downgrade drops the column; the acceptance timestamp in users.terms_accepted_at is kept).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_version VARCHAR(40)")


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS terms_version")
