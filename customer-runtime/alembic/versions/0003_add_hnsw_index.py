"""Add pgvector HNSW index on requirements.embedding

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-18
"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # CONCURRENTLY is not supported inside a transaction block.
    # Alembic wraps migrations in a transaction by default; use op.execute directly.
    op.execute("""
        CREATE INDEX IF NOT EXISTS requirements_embedding_hnsw_idx
        ON requirements
        USING hnsw (embedding vector_cosine_ops)
        WITH (m = 16, ef_construction = 64)
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS requirements_embedding_hnsw_idx")
