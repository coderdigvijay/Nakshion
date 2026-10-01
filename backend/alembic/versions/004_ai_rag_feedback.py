"""AI, RAG and feedback tables (architecture.md 4.3, llm-integration.md 6.4)

Revision ID: 004
Revises: 003
Create Date: 2026-10-01

Requires the pgvector extension to be *available* on the server (Neon: yes; local Postgres:
install pgvector). ``CREATE EXTENSION IF NOT EXISTS vector`` needs a role allowed to create it.

Downgrade drops every table created here (LOSSY for llm_usage history, feedback, personal
readings and the KB index; the KB index is rebuildable with scripts/index_kb.py). The
``vector`` extension is left installed (other objects may depend on it).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS kb_chunks (
          id              TEXT PRIMARY KEY,
          index_version   INT  NOT NULL,
          file            TEXT NOT NULL,
          heading_path    TEXT NOT NULL,
          system          TEXT NOT NULL CHECK (system IN ('vedic','western','both','excluded')),
          topics          TEXT[] NOT NULL DEFAULT '{}',
          entities        TEXT[] NOT NULL DEFAULT '{}',
          content         TEXT NOT NULL,
          content_tsv     TSVECTOR GENERATED ALWAYS AS (to_tsvector('english', heading_path || ' ' || content)) STORED,
          embedding       VECTOR(384) NOT NULL,
          embedding_model TEXT NOT NULL,
          content_sha256  TEXT NOT NULL,
          indexed_at      TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_chunks_hnsw ON kb_chunks USING hnsw (embedding vector_cosine_ops)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_chunks_tsv ON kb_chunks USING gin (content_tsv)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_chunks_version_system ON kb_chunks (index_version, system)")
    op.execute("CREATE TABLE IF NOT EXISTS kb_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS kb_key_embeddings (
          key           TEXT NOT NULL,
          index_version INT  NOT NULL,
          embedding     VECTOR(384) NOT NULL,
          PRIMARY KEY (key, index_version)
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_usage (
          id BIGSERIAL PRIMARY KEY,
          user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
          task VARCHAR(30) NOT NULL,
          provider VARCHAR(20) NOT NULL,
          model VARCHAR(60) NOT NULL,
          prompt_version VARCHAR(20) NOT NULL,
          input_tokens INT NOT NULL,
          cached_input_tokens INT NOT NULL DEFAULT 0,
          output_tokens INT NOT NULL,
          cost_usd NUMERIC(10,6) NOT NULL,
          latency_ms INT NOT NULL,
          outcome VARCHAR(12) NOT NULL,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_llm_usage_created ON llm_usage (created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_llm_usage_user_created ON llm_usage (user_id, created_at)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS message_feedback (
          message_id UUID PRIMARY KEY REFERENCES messages(id) ON DELETE CASCADE,
          user_id    UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          rating     VARCHAR(4) NOT NULL CHECK (rating IN ('up','down')),
          reason     VARCHAR(20),
          comment    VARCHAR(500),
          created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_message_feedback_user ON message_feedback (user_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS personal_readings (
          user_id      UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          chart_id     UUID NULL REFERENCES birth_charts(id) ON DELETE SET NULL,
          date         DATE NOT NULL,
          system       VARCHAR(10) NOT NULL,
          reading      JSONB NOT NULL,
          generated_by VARCHAR(10) NOT NULL,
          created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
          PRIMARY KEY (user_id, date, system)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_personal_readings_date ON personal_readings (date)")


def downgrade() -> None:
    for table in ("personal_readings", "message_feedback", "llm_usage", "kb_key_embeddings", "kb_meta", "kb_chunks"):
        op.execute(f"DROP TABLE IF EXISTS {table}")
