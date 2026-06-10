"""RegulatoryDocument ORM model.

Stores metadata for fetched regulatory documents.
Raw document bytes are NEVER stored in PostgreSQL (FR-210 / REQ-CRAWLER-004).

# @MX:ANCHOR: [AUTO] Public contract for regulatory document metadata schema.
# @MX:REASON: Referenced by crawler orchestrator, dedup service, and alembic migration.
#             content_hash UNIQUE index is the DB-level duplicate guard (AC-002).
"""
from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class RegulatoryDocument(TimestampMixin, Base):
    """Metadata row for a single fetched regulatory document.

    Columns
    -------
    id            -- Auto-incremented surrogate key.
    source        -- Origin: "fda" | "mfds" | "eu-mdr" (REQ-CRAWLER-002).
    blob_path     -- Azure Blob path: regulatory-docs/{source}/{YYYY-MM-DD}/{filename}.
    content_hash  -- SHA-256 hex digest of raw bytes (UNIQUE — dedup guard, AC-002).
    fetched_at    -- UTC timestamp when the document was fetched.
    source_url    -- Original URL the document was retrieved from.

    Intentionally absent
    --------------------
    raw content / body / text — FR-210 prohibits storing raw bytes in PostgreSQL.
    """

    __tablename__ = "regulatory_documents"

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)

    source: Mapped[str] = mapped_column(sa.String(32), nullable=False, index=True)

    blob_path: Mapped[str] = mapped_column(sa.String(512), nullable=False)

    # @MX:NOTE: [AUTO] SHA-256 hex string is always 64 chars. UNIQUE enforces dedup at DB level.
    content_hash: Mapped[str] = mapped_column(
        sa.String(64),
        nullable=False,
        unique=True,
    )

    fetched_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=False)

    source_url: Mapped[Optional[str]] = mapped_column(sa.String(1024), nullable=True)
