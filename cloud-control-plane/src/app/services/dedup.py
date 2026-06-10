"""SHA-256 deduplication service (REQ-003, REQ-003b, AC-002).

Computes SHA-256 hash of raw document bytes and checks against
the regulatory_documents.content_hash column.
"""
from __future__ import annotations

import hashlib

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.regulatory_document import RegulatoryDocument


class DedupService:
    """Check document uniqueness by SHA-256 hash.

    # @MX:ANCHOR: [AUTO] Public contract for dedup checks (REQ-003, AC-002).
    # @MX:REASON: Called by orchestrator per document; also used by test fixtures.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def compute_hash(self, data: bytes) -> str:
        """Return SHA-256 hex digest of raw bytes."""
        return hashlib.sha256(data).hexdigest()

    async def is_duplicate(self, content_hash: str) -> bool:
        """Return True if content_hash already exists in regulatory_documents."""
        result = await self._session.execute(
            sa.select(RegulatoryDocument.id).where(
                RegulatoryDocument.content_hash == content_hash
            )
        )
        return result.scalar_one_or_none() is not None
