"""Integrity and auth hardening (architecture.md section 4.2)

Revision ID: 003
Revises: 002
Create Date: 2026-10-01

Idempotent: every statement uses IF [NOT] EXISTS or a catalog check, so a partial apply re-runs.

Data steps:
- Pre-step for the one-primary-per-user partial unique index: keeps the OLDEST primary chart per
  user and clears ``is_primary`` on the rest (spec-approved, architecture.md section 4.2).
- CHECK constraints are added NOT VALID and then validated. If legacy rows violate one, it stays
  NOT VALID (still enforced for new writes) and a NOTICE is raised; no user data is rewritten.

Downgrade: reverses every statement. LOSSY STEP: ``daily_horoscopes`` rows with
``system <> 'western'`` are deleted before the old (zodiac_sign, date) unique key is restored.
The primary-chart dedupe in the upgrade is not reversible (the old extra primaries were invalid).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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
    # users
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS token_version INT NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS preferred_language VARCHAR(10) NOT NULL DEFAULT 'english'")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS astrology_system VARCHAR(10) NOT NULL DEFAULT 'vedic'")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS terms_accepted_at TIMESTAMPTZ")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS age_confirmed_at TIMESTAMPTZ")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_consent_at TIMESTAMPTZ")
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS ai_consent_withdrawn_at TIMESTAMPTZ")
    _add_check("users", "ck_users_language", "preferred_language IN ('english','hindi','hinglish')")
    _add_check("users", "ck_users_astrology_system", "astrology_system IN ('vedic','western')")
    _add_check("users", "ck_users_tier", "subscription_tier IN ('free','premium')")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_oauth ON users (oauth_provider, oauth_id) "
        "WHERE oauth_provider IS NOT NULL"
    )

    # birth_charts
    op.execute("ALTER TABLE birth_charts ADD COLUMN IF NOT EXISTS engine_version VARCHAR(20) NOT NULL DEFAULT '0.0.0'")
    _add_check(
        "birth_charts",
        "ck_chart_relationship",
        "relationship IN ('self','partner','friend','family','coworker','other')",
    )
    op.execute(
        """
        UPDATE birth_charts SET is_primary = false
        WHERE is_primary AND id NOT IN (
          SELECT DISTINCT ON (user_id) id FROM birth_charts
          WHERE is_primary ORDER BY user_id, created_at, id
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_birth_charts_one_primary ON birth_charts (user_id) WHERE is_primary")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_birth_charts_user_order ON birth_charts (user_id, is_primary DESC, created_at)"
    )

    # conversations: chart deletion must not delete or block chat history
    op.execute("ALTER TABLE conversations DROP CONSTRAINT IF EXISTS conversations_chart_id_fkey")
    op.execute(
        "ALTER TABLE conversations ADD CONSTRAINT conversations_chart_id_fkey "
        "FOREIGN KEY (chart_id) REFERENCES birth_charts(id) ON DELETE SET NULL"
    )
    _add_check("conversations", "ck_conv_status", "status IN ('active','archived')")
    op.execute("CREATE INDEX IF NOT EXISTS ix_conversations_user_updated ON conversations (user_id, updated_at DESC)")

    # messages
    _add_check("messages", "ck_msg_role", "role IN ('user','assistant')")
    op.execute("CREATE INDEX IF NOT EXISTS ix_messages_conv_created ON messages (conversation_id, created_at)")
    op.execute("DROP INDEX IF EXISTS ix_messages_created_at")

    # compatibility
    op.execute("CREATE INDEX IF NOT EXISTS ix_compat_user_created ON compatibility_reports (user_id, created_at DESC)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_compat_dedupe ON compatibility_reports "
        "(user_id, chart1_id, chart2_id, relationship_type, created_at DESC)"
    )
    _add_check("compatibility_reports", "ck_compat_score", "overall_score BETWEEN 0 AND 10")

    # horoscopes: allow a sidereal / moon-sign variant
    op.execute("ALTER TABLE daily_horoscopes ADD COLUMN IF NOT EXISTS system VARCHAR(10) NOT NULL DEFAULT 'western'")
    op.execute("ALTER TABLE daily_horoscopes DROP CONSTRAINT IF EXISTS uq_horoscope_sign_date")
    op.execute(
        """
        DO $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_horoscope_sign_date_system') THEN
            ALTER TABLE daily_horoscopes ADD CONSTRAINT uq_horoscope_sign_date_system UNIQUE (zodiac_sign, date, system);
          END IF;
        END $$;
        """
    )

    # quotas (atomic, Postgres-backed)
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS usage_counters (
          user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          kind         VARCHAR(30) NOT NULL,
          period       VARCHAR(10) NOT NULL,
          period_start DATE NOT NULL,
          count        INT NOT NULL DEFAULT 0,
          PRIMARY KEY (user_id, kind, period, period_start)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS usage_counters")

    # LOSSY: non-western horoscope rows cannot exist under the old unique key.
    op.execute("DELETE FROM daily_horoscopes WHERE system <> 'western'")
    op.execute("ALTER TABLE daily_horoscopes DROP CONSTRAINT IF EXISTS uq_horoscope_sign_date_system")
    op.execute(
        """
        DO $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_horoscope_sign_date') THEN
            ALTER TABLE daily_horoscopes ADD CONSTRAINT uq_horoscope_sign_date UNIQUE (zodiac_sign, date);
          END IF;
        END $$;
        """
    )
    op.execute("ALTER TABLE daily_horoscopes DROP COLUMN IF EXISTS system")

    op.execute("ALTER TABLE compatibility_reports DROP CONSTRAINT IF EXISTS ck_compat_score")
    op.execute("DROP INDEX IF EXISTS ix_compat_dedupe")
    op.execute("DROP INDEX IF EXISTS ix_compat_user_created")

    op.execute("CREATE INDEX IF NOT EXISTS ix_messages_created_at ON messages (created_at)")
    op.execute("DROP INDEX IF EXISTS ix_messages_conv_created")
    op.execute("ALTER TABLE messages DROP CONSTRAINT IF EXISTS ck_msg_role")

    op.execute("DROP INDEX IF EXISTS ix_conversations_user_updated")
    op.execute("ALTER TABLE conversations DROP CONSTRAINT IF EXISTS ck_conv_status")
    op.execute("ALTER TABLE conversations DROP CONSTRAINT IF EXISTS conversations_chart_id_fkey")
    op.execute(
        "ALTER TABLE conversations ADD CONSTRAINT conversations_chart_id_fkey "
        "FOREIGN KEY (chart_id) REFERENCES birth_charts(id)"
    )

    op.execute("DROP INDEX IF EXISTS ix_birth_charts_user_order")
    op.execute("DROP INDEX IF EXISTS uq_birth_charts_one_primary")
    op.execute("ALTER TABLE birth_charts DROP CONSTRAINT IF EXISTS ck_chart_relationship")
    op.execute("ALTER TABLE birth_charts DROP COLUMN IF EXISTS engine_version")

    op.execute("DROP INDEX IF EXISTS uq_users_oauth")
    for name in ("ck_users_tier", "ck_users_astrology_system", "ck_users_language"):
        op.execute(f"ALTER TABLE users DROP CONSTRAINT IF EXISTS {name}")
    for col in (
        "ai_consent_withdrawn_at",
        "ai_consent_at",
        "age_confirmed_at",
        "terms_accepted_at",
        "astrology_system",
        "preferred_language",
        "token_version",
    ):
        op.execute(f"ALTER TABLE users DROP COLUMN IF EXISTS {col}")
