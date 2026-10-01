"""Align RAG / usage tables with app/rag and app/llm (ai-genai-specialist contract)

Revision ID: 006
Revises: 005
Create Date: 2026-10-01

- kb_key_embeddings: add ``embedding_model`` and make the PK (index_version, key) so the
  per-version lookup ``WHERE index_version = :v AND key = :k`` and version swaps use the PK.
- llm_usage: add nullable ``error`` (provider error class / short reason, never raw SDK text).

Idempotent. Downgrade restores the 004 shape; LOSSY only for the two added columns' values.
"""
from typing import Sequence, Union

from alembic import op

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE kb_key_embeddings ADD COLUMN IF NOT EXISTS embedding_model TEXT")
    op.execute("ALTER TABLE kb_key_embeddings DROP CONSTRAINT IF EXISTS kb_key_embeddings_pkey")
    op.execute("ALTER TABLE kb_key_embeddings ADD CONSTRAINT kb_key_embeddings_pkey PRIMARY KEY (index_version, key)")
    op.execute("ALTER TABLE llm_usage ADD COLUMN IF NOT EXISTS error TEXT NULL")


def downgrade() -> None:
    op.execute("ALTER TABLE llm_usage DROP COLUMN IF EXISTS error")
    op.execute("ALTER TABLE kb_key_embeddings DROP CONSTRAINT IF EXISTS kb_key_embeddings_pkey")
    op.execute("ALTER TABLE kb_key_embeddings ADD CONSTRAINT kb_key_embeddings_pkey PRIMARY KEY (key, index_version)")
    op.execute("ALTER TABLE kb_key_embeddings DROP COLUMN IF EXISTS embedding_model")
