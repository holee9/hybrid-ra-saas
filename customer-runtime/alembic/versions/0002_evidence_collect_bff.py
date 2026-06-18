"""feat: evidence_collect table for BFF API.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-18 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "evidence_collect",
        sa.Column("collect_id", sa.String(36), primary_key=True),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("evidence_type", sa.String(64), nullable=False),
        sa.Column("document_ids", sa.JSON(), nullable=False),
        sa.Column("items", sa.JSON(), nullable=False),
        sa.Column("synthesis", sa.Text(), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="collected"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("evidence_collect")
