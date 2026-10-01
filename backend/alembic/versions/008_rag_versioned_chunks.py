"""RAG: per-version chunk ids, chunk metadata, heading-weighted full-text index (ai-genai-specialist)

Revision ID: 008
Revises: 007
Create Date: 2026-10-01

- kb_chunks PK (id) -> (index_version, id). The re-index protocol (llm-integration.md 6.4) inserts
  version n+1 while n is live, and chunk ids are stable across versions, so the old PK made every
  re-index fail with a unique violation. Also enables rollback (keep n-1) without id collisions.
- kb_chunks.meta JSONB: per-chunk provenance (source title, author, tradition, tier, licence,
  language, quality score) shown on citation chips. Defaults to '{}'.
- content_tsv: heading_path now weighs 'A', body 'B' (a query naming "Saturn" or "Rohini" should
  prefer the chunk whose heading says so). Generated column, so it is rebuilt in place.

Idempotent. Downgrade: deletes every non-active index version (the old PK cannot hold two copies of
an id), restores PK(id), drops meta, restores the unweighted tsvector. LOSSY only for meta values and
the inactive index versions (both are rebuilt by `python -m app.rag.ingest`).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE kb_chunks DROP CONSTRAINT IF EXISTS kb_chunks_pkey")
    op.execute("ALTER TABLE kb_chunks ADD CONSTRAINT kb_chunks_pkey PRIMARY KEY (index_version, id)")
    op.execute("ALTER TABLE kb_chunks ADD COLUMN IF NOT EXISTS meta JSONB NOT NULL DEFAULT '{}'::jsonb")
    op.execute("DROP INDEX IF EXISTS ix_kb_chunks_tsv")
    op.execute("ALTER TABLE kb_chunks DROP COLUMN IF EXISTS content_tsv")
    op.execute(
        """
        ALTER TABLE kb_chunks ADD COLUMN content_tsv TSVECTOR GENERATED ALWAYS AS (
          setweight(to_tsvector('english', heading_path), 'A') || setweight(to_tsvector('english', content), 'B')
        ) STORED
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_chunks_tsv ON kb_chunks USING gin (content_tsv)")


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM kb_chunks WHERE index_version <> COALESCE(
          (SELECT value::int FROM kb_meta WHERE key = 'active_index_version'),
          (SELECT max(index_version) FROM kb_chunks))
        """
    )
    op.execute("ALTER TABLE kb_chunks DROP CONSTRAINT IF EXISTS kb_chunks_pkey")
    op.execute("ALTER TABLE kb_chunks ADD CONSTRAINT kb_chunks_pkey PRIMARY KEY (id)")
    op.execute("DROP INDEX IF EXISTS ix_kb_chunks_tsv")
    op.execute("ALTER TABLE kb_chunks DROP COLUMN IF EXISTS content_tsv")
    op.execute(
        "ALTER TABLE kb_chunks ADD COLUMN content_tsv TSVECTOR GENERATED ALWAYS AS "
        "(to_tsvector('english', heading_path || ' ' || content)) STORED"
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_kb_chunks_tsv ON kb_chunks USING gin (content_tsv)")
    op.execute("ALTER TABLE kb_chunks DROP COLUMN IF EXISTS meta")
