"""CHECK constraints, index cleanup, FK-lookup indexes, case-insensitive email uniqueness (db review)

Revision ID: 007
Revises: 006
Create Date: 2026-10-01

Idempotent. Data/lossy notes:
- CHECK constraints are added NOT VALID then validated; if legacy rows violate one it stays NOT VALID
  (enforced for new writes) and a NOTICE is raised. No user data is rewritten.
- ``uq_users_email_lower`` is skipped with a NOTICE if existing emails collide case-insensitively.
- Drops four single-column indexes that are leading prefixes of composites (no information lost).
- Drops the HNSW index on kb_chunks: at ~400 rows an exact scan is faster, and an HNSW post-filtered by
  ``index_version``/``system`` can return fewer than K rows while two index versions coexist.
Downgrade restores the dropped indexes and removes everything added here.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CHECKS = [
    ("daily_horoscopes", "ck_horoscope_system", "system IN ('western','vedic')"),
    ("personal_readings", "ck_personal_system", "system IN ('western','vedic')"),
    ("usage_counters", "ck_usage_kind", "kind IN ('chat_reply','compat_report','premium_report','chart_create')"),
    ("usage_counters", "ck_usage_period", "period IN ('day','month')"),
    (
        "subscriptions",
        "ck_subscription_status",
        "status IN ('created','authenticated','active','pending','halted','paused','cancelled','completed','expired')",
    ),
    (
        "llm_usage",
        "ck_llm_usage_outcome",
        "outcome IN ('ok','repaired','fallback','failed','blocked','invalid','truncated','timeout','rate_limited','static','error')",
    ),
    ("birth_charts", "ck_chart_latitude", "latitude BETWEEN -90 AND 90"),
    ("birth_charts", "ck_chart_longitude", "longitude BETWEEN -180 AND 180"),
]

PREFIX_INDEXES = [
    ("ix_birth_charts_user_id", "birth_charts", "user_id"),
    ("ix_conversations_user_id", "conversations", "user_id"),
    ("ix_compatibility_reports_user_id", "compatibility_reports", "user_id"),
    ("ix_messages_conversation_id", "messages", "conversation_id"),
]

FK_INDEXES = [
    ("ix_compat_chart1", "compatibility_reports", "chart1_id"),
    ("ix_compat_chart2", "compatibility_reports", "chart2_id"),
    ("ix_conversations_chart", "conversations", "chart_id"),
    ("ix_personal_readings_chart", "personal_readings", "chart_id"),
]


def _add_check(table: str, name: str, expr: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = '{name}') THEN
            ALTER TABLE {table} ADD CONSTRAINT {name} CHECK ({expr}) NOT VALID;
          END IF;
          BEGIN
            ALTER TABLE {table} VALIDATE CONSTRAINT {name};
          EXCEPTION WHEN check_violation THEN
            RAISE NOTICE 'constraint {name} left NOT VALID: legacy rows violate it';
          END;
        END $$;
        """
    )


def upgrade() -> None:
    for table, name, expr in CHECKS:
        _add_check(table, name, expr)
    for name, table, col in FK_INDEXES:
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({col})")
    for name, _table, _col in PREFIX_INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {name}")
    op.execute("DROP INDEX IF EXISTS ix_kb_chunks_hnsw")
    op.execute(
        """
        DO $$ BEGIN
          CREATE UNIQUE INDEX IF NOT EXISTS uq_users_email_lower ON users (lower(email));
        EXCEPTION WHEN unique_violation THEN
          RAISE NOTICE 'uq_users_email_lower skipped: emails collide case-insensitively';
        END $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_users_email_lower")
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_chunks_hnsw ON kb_chunks USING hnsw (embedding vector_cosine_ops)")
    for name, table, col in PREFIX_INDEXES:
        op.execute(f"CREATE INDEX IF NOT EXISTS {name} ON {table} ({col})")
    for name, _table, _col in FK_INDEXES:
        op.execute(f"DROP INDEX IF EXISTS {name}")
    for table, name, _expr in reversed(CHECKS):
        op.execute(f"ALTER TABLE {table} DROP CONSTRAINT IF EXISTS {name}")
