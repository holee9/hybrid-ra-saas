"""AuthoringSession → ChecklistItem status sync — SPEC-CHECKLIST-001."""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.models.checklist_item import ChecklistItem

logger = logging.getLogger(__name__)

# Maps AuthoringSectionEntry.status → ChecklistItem.status
AUTHORING_TO_CHECKLIST: dict[str, str] = {
    "empty": "pending",
    "ai_draft": "in_progress",
    "human_edited": "in_progress",
    "complete": "complete",
    "skipped": "waived",  # Only valid when blocking==False; see below
}


async def sync_from_authoring(
    session_id: str,
    items: list["ChecklistItem"],
    db: AsyncSession,
) -> None:
    """Map AuthoringSectionEntry statuses to ChecklistItem statuses.

    For skipped entries: uses "pending" instead of "waived" when item is blocking.

    Args:
        session_id: AuthoringSession.session_id to read entries from.
        items: ChecklistItem instances to update in-place.
        db: Async database session.
    """
    from app.models.authoring_section_entry import AuthoringSectionEntry

    result = await db.execute(
        select(AuthoringSectionEntry).where(
            AuthoringSectionEntry.session_id == session_id
        )
    )
    entries = result.scalars().all()
    entries_by_section: dict[str, str] = {e.section_id: e.status for e in entries}

    for item in items:
        authoring_status = entries_by_section.get(item.section_id)
        if authoring_status is None:
            continue  # No matching entry — leave item as-is

        mapped = AUTHORING_TO_CHECKLIST.get(authoring_status, "pending")

        # REQ-CHECK-012 guard: blocking items cannot be waived
        if mapped == "waived" and item.blocking:
            mapped = "pending"

        item.status = mapped
