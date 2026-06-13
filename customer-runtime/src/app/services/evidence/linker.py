"""EvidenceLink CRUD service — SPEC-EVIDENCE-001."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence_link import EvidenceLink

logger = logging.getLogger(__name__)

VALID_SOURCE_TYPES = {"requirement", "risk_control", "test", "ifu_section", "checklist_item"}
VALID_TARGET_TYPES = {"file", "traceability_node", "external_url"}
VALID_LINK_TYPES = {"satisfies", "verifies", "supports", "warns_about"}


async def create_link(
    binder_id: str,
    source_entity_type: str,
    source_entity_id: str,
    target_entity_type: str,
    target_ref: str,
    link_type: str,
    db: AsyncSession,
) -> EvidenceLink:
    """Validate enum fields, insert EvidenceLink, and return it."""
    if source_entity_type not in VALID_SOURCE_TYPES:
        raise ValueError(
            f"Invalid source_entity_type '{source_entity_type}'. "
            f"Must be one of {sorted(VALID_SOURCE_TYPES)}."
        )
    if target_entity_type not in VALID_TARGET_TYPES:
        raise ValueError(
            f"Invalid target_entity_type '{target_entity_type}'. "
            f"Must be one of {sorted(VALID_TARGET_TYPES)}."
        )
    if link_type not in VALID_LINK_TYPES:
        raise ValueError(
            f"Invalid link_type '{link_type}'. "
            f"Must be one of {sorted(VALID_LINK_TYPES)}."
        )

    link = EvidenceLink(
        link_id=str(uuid.uuid4()),
        binder_id=binder_id,
        source_entity_type=source_entity_type,
        source_entity_id=source_entity_id,
        target_entity_type=target_entity_type,
        target_ref=target_ref,
        link_type=link_type,
        created_at=datetime.now(timezone.utc),
    )
    db.add(link)
    await db.flush()
    await db.refresh(link)
    logger.info("Created evidence link %s for binder %s", link.link_id, binder_id)
    return link


async def delete_link(binder_id: str, link_id: str, db: AsyncSession) -> None:
    """Delete an EvidenceLink by binder_id + link_id."""
    await db.execute(
        delete(EvidenceLink).where(
            EvidenceLink.link_id == link_id,
            EvidenceLink.binder_id == binder_id,
        )
    )
    await db.flush()
    logger.info("Deleted evidence link %s from binder %s", link_id, binder_id)
