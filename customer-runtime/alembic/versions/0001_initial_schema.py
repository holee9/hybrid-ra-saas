"""Initial schema — all 9 tables + pgvector extension + ivfflat index.

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # 2. products
    op.create_table(
        "products",
        sa.Column("product_id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("product_family", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_products_tenant_id", "products", ["tenant_id"])

    # 3. evidences (before controls — controls FK → evidences)
    op.create_table(
        "evidences",
        sa.Column("evidence_id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("test_report_ref", sa.String(512), nullable=True),
        sa.Column("result_value", sa.Text(), nullable=True),
        sa.Column("acceptance_criteria", sa.Text(), nullable=True),
        sa.Column("file_ref", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_evidences_tenant_id", "evidences", ["tenant_id"])

    # 4. controls
    op.create_table(
        "controls",
        sa.Column("control_id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("control_type", sa.String(100), nullable=False),
        sa.Column("linked_srs", sa.Text(), nullable=True),
        sa.Column("linked_ifu_warning", sa.Text(), nullable=True),
        sa.Column(
            "verification_id",
            sa.String(36),
            sa.ForeignKey("evidences.evidence_id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_controls_tenant_id", "controls", ["tenant_id"])

    # 5. documents (before parse_jobs — parse_jobs FK → documents)
    op.create_table(
        "documents",
        sa.Column("doc_id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.product_id"), nullable=False),
        sa.Column("doc_type", sa.String(100), nullable=False),
        sa.Column("version", sa.String(50), nullable=True),
        sa.Column("owner", sa.String(255), nullable=True),
        sa.Column("source_file_hash", sa.String(64), nullable=True),
        sa.Column("storage_key", sa.String(512), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "uploaded", "parsing", "needs_correction", "ready_for_check",
                "approved", "rejected",
                name="documentstatus",
            ),
            nullable=False,
            server_default="uploaded",
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_documents_tenant_id", "documents", ["tenant_id"])

    # 6. risks
    op.create_table(
        "risks",
        sa.Column("risk_id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.product_id"), nullable=False),
        sa.Column("hazard", sa.Text(), nullable=False),
        sa.Column("hazardous_situation", sa.Text(), nullable=True),
        sa.Column("harm", sa.Text(), nullable=True),
        sa.Column("risk_level", sa.String(50), nullable=True),
        sa.Column(
            "control_id",
            sa.String(36),
            sa.ForeignKey("controls.control_id"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_risks_tenant_id", "risks", ["tenant_id"])

    # 7. findings
    op.create_table(
        "findings",
        sa.Column("finding_id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("product_id", sa.String(36), sa.ForeignKey("products.product_id"), nullable=False),
        sa.Column("severity", sa.String(50), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("evidence_links", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("reviewer_status", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_findings_tenant_id", "findings", ["tenant_id"])

    # 8. audit_events
    op.create_table(
        "audit_events",
        sa.Column("event_id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("user_id", sa.String(36), nullable=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("timestamp", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("before_hash", sa.String(64), nullable=True),
        sa.Column("after_hash", sa.String(64), nullable=True),
    )
    op.create_index("ix_audit_events_tenant_id", "audit_events", ["tenant_id"])

    # 9. parse_jobs
    op.create_table(
        "parse_jobs",
        sa.Column("job_id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("doc_id", sa.String(36), sa.ForeignKey("documents.doc_id"), nullable=False),
        sa.Column(
            "status",
            sa.Enum("pending", "running", "done", "failed", name="parsejobstatus"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("result_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
    )
    op.create_index("ix_parse_jobs_tenant_id", "parse_jobs", ["tenant_id"])

    # 10. requirements (with pgvector embedding)
    op.create_table(
        "requirements",
        sa.Column("req_id", sa.String(36), primary_key=True),
        sa.Column("tenant_id", sa.String(64), nullable=False),
        sa.Column("source", sa.String(255), nullable=True),
        sa.Column("clause_ref", sa.String(100), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("product_family", sa.String(100), nullable=True),
        sa.Column("severity", sa.String(50), nullable=True),
        sa.Column("embedding", sa.Text(), nullable=True),  # placeholder, replaced below
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("NOW()"), nullable=False),
    )
    # Replace TEXT placeholder with actual vector type
    op.execute("ALTER TABLE requirements ALTER COLUMN embedding TYPE vector(384) USING embedding::vector")
    op.create_index("ix_requirements_tenant_id", "requirements", ["tenant_id"])
    # ivfflat index for ANN search
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_requirements_embedding_ivfflat "
        "ON requirements USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )


def downgrade() -> None:
    op.drop_table("requirements")
    op.drop_table("parse_jobs")
    op.drop_table("audit_events")
    op.drop_table("findings")
    op.drop_table("risks")
    op.drop_table("documents")
    op.drop_table("controls")
    op.drop_table("evidences")
    op.drop_table("products")
    op.execute("DROP TYPE IF EXISTS documentstatus")
    op.execute("DROP TYPE IF EXISTS parsejobstatus")
    op.execute("DROP EXTENSION IF EXISTS vector")
