"""Binder lifecycle service — SPEC-EVIDENCE-001."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.evidence_binder import EvidenceBinder


class BinderSealedError(ValueError):
    """Raised when a mutation is attempted on a sealed binder."""


# @MX:ANCHOR: [AUTO] Sealed-binder immutability guard — called by file upload, link add/delete
# @MX:REASON: Binder sealing is a one-way operation; any bypass would corrupt audit trails
def assert_not_sealed(binder: EvidenceBinder) -> None:
    """Raise BinderSealedError if the binder is sealed."""
    if binder.status == "sealed":
        raise BinderSealedError(f"Binder {binder.binder_id} is sealed and cannot be modified.")


async def create_binder(
    product_profile_id: str,
    name: str,
    db: AsyncSession,
    pack_id: str | None = None,
) -> EvidenceBinder:
    """Insert a new draft EvidenceBinder and return it."""
    binder = EvidenceBinder(
        binder_id=str(uuid.uuid4()),
        product_profile_id=product_profile_id,
        pack_id=pack_id,
        name=name,
        status="draft",
        created_by="system",
    )
    db.add(binder)
    await db.flush()
    await db.refresh(binder)
    return binder


async def get_binder(binder_id: str, db: AsyncSession) -> EvidenceBinder | None:
    """Fetch a binder with links, files, and gaps eagerly loaded."""
    result = await db.execute(
        select(EvidenceBinder)
        .options(
            selectinload(EvidenceBinder.links),
            selectinload(EvidenceBinder.files),
            selectinload(EvidenceBinder.gaps),
        )
        .where(EvidenceBinder.binder_id == binder_id)
    )
    return result.scalar_one_or_none()


async def seal_binder(binder_id: str, db: AsyncSession) -> EvidenceBinder:
    """Set status='sealed' and record sealed_at timestamp."""
    result = await db.execute(
        select(EvidenceBinder).where(EvidenceBinder.binder_id == binder_id)
    )
    binder = result.scalar_one_or_none()
    if binder is None:
        raise ValueError(f"Binder {binder_id} not found.")
    binder.status = "sealed"
    binder.sealed_at = datetime.now(timezone.utc)
    await db.flush()
    await db.refresh(binder)
    return binder
