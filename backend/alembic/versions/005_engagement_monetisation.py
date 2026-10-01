"""Engagement and monetisation tables (architecture.md 4.4, v1)

Revision ID: 005
Revises: 004
Create Date: 2026-10-01

All user-owned tables CASCADE on user delete. ``deletion_log`` stores only a SHA-256 of the
user id (no PII). Downgrade drops every table created here (LOSSY for their contents).
``users.subscription_tier`` stays the denormalised flag; only the webhook handler writes it.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS push_subscriptions (
          id UUID PRIMARY KEY,
          user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          endpoint TEXT NOT NULL UNIQUE,
          p256dh TEXT NOT NULL,
          auth TEXT NOT NULL,
          user_agent VARCHAR(255),
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          last_success_at TIMESTAMPTZ
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_push_subscriptions_user ON push_subscriptions (user_id)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_prefs (
          user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
          daily_push BOOLEAN NOT NULL DEFAULT false,
          push_hour_local SMALLINT NOT NULL DEFAULT 7 CHECK (push_hour_local BETWEEN 0 AND 23),
          transit_alerts BOOLEAN NOT NULL DEFAULT false,
          weekly_email BOOLEAN NOT NULL DEFAULT false
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS subscriptions (
          id UUID PRIMARY KEY,
          user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          provider VARCHAR(20) NOT NULL DEFAULT 'razorpay',
          provider_sub_id VARCHAR(100) NOT NULL UNIQUE,
          plan VARCHAR(30) NOT NULL,
          status VARCHAR(20) NOT NULL,
          current_period_end TIMESTAMPTZ,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_subscriptions_user ON subscriptions (user_id)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS payment_events (
          id BIGSERIAL PRIMARY KEY,
          provider_event_id VARCHAR(100) NOT NULL UNIQUE,
          payload JSONB NOT NULL,
          received_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS deletion_log (
          id BIGSERIAL PRIMARY KEY,
          user_id_sha256 VARCHAR(64) NOT NULL,
          deleted_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    for table in ("deletion_log", "payment_events", "subscriptions", "notification_prefs", "push_subscriptions"):
        op.execute(f"DROP TABLE IF EXISTS {table}")
