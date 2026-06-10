"""Create regulatory_documents table with content_hash UNIQUE index.

Revision ID: 0001
Revises:
Create Date: 2026-06-10 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "regulatory_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column("blob_path", sa.String(512), nullable=False),
        # SHA-256 hex is always 64 chars; UNIQUE enforces dedup at DB level (AC-002)
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_url", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_hash", name="uq_regulatory_documents_content_hash"),
    )
    op.create_index("ix_regulatory_documents_source", "regulatory_documents", ["source"])


def downgrade() -> None:
    op.drop_index("ix_regulatory_documents_source", table_name="regulatory_documents")
    op.drop_table("regulatory_documents")
