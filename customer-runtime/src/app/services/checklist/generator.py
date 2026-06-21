"""ChecklistSnapshot generator — SPEC-CHECKLIST-001.

# @MX:ANCHOR: [AUTO] generate_checklist — snapshot creation entry point
# @MX:REASON: [AUTO] Called by router and tests; orchestrates items, sync, gaps, and count updates
"""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checklist_item import ChecklistItem
from app.models.checklist_snapshot import ChecklistSnapshot
from app.models.gap_finding import GapFinding
from app.services.checklist import authoring_sync, gap_engine
from app.services.template_client import TemplateAPIError, fetch_template_sections  # noqa: F401

logger = logging.getLogger(__name__)


async def _fetch_sections(pack_id: str) -> list[dict]:
    """Fetch template sections for pack_id via the live Template API.

    Raises:
        TemplateAPIError: When TEMPLATE_API_URL is not configured or the call fails.
            No stub fallback — callers must handle the error explicitly.
    """
    return await fetch_template_sections(
        pack_id,
        endpoint_path="/template-packs/{pack_id}",
    )


async def generate_checklist(
    pack_id: str,
    session_id: str | None,
    db: AsyncSession,
) -> ChecklistSnapshot:
    """Create a ChecklistSnapshot with items and gaps.

    Steps:
    1. Fetch sections for pack_id from live Template API
    2. Create ChecklistSnapshot (status="draft")
    3. Create ChecklistItem per section
    4. If session_id provided, run authoring_sync
    5. Run gap_engine.derive_gaps → create GapFinding records
    6. Update snapshot aggregate counts
    7. Commit and return snapshot

    Args:
        pack_id: Template pack identifier.
        session_id: Optional linked AuthoringSession.session_id.
        db: Async database session.

    Returns:
        Persisted ChecklistSnapshot instance.

    Raises:
        TemplateAPIError: When TEMPLATE_API_URL is not configured or the live call fails.
    """
    sections = await _fetch_sections(pack_id)

    now = datetime.now(timezone.utc)
    snapshot = ChecklistSnapshot(
        snapshot_id=str(uuid.uuid4()),
        session_id=session_id,
        pack_id=pack_id,
        generated_at=now,
        total_items=0,
        complete_items=0,
        blocking_gaps_count=0,
        status="draft",
    )
    db.add(snapshot)
    await db.flush()  # Assign PK before creating children

    # Create items
    items: list[ChecklistItem] = []
    for sec in sections:
        item = ChecklistItem(
            checklist_item_id=f"{snapshot.snapshot_id}:{sec['section_id']}",
            snapshot_id=snapshot.snapshot_id,
            section_id=sec["section_id"],
            status="pending",
            blocking=sec.get("blocking", False),
            evidence_required=sec.get("evidence_required", False),
            evidence_satisfied=False,
        )
        db.add(item)
        items.append(item)

    await db.flush()

    # Sync with authoring session if provided
    if session_id:
        try:
            await authoring_sync.sync_from_authoring(session_id, items, db)
        except Exception as exc:  # Session may not exist in local/test mode
            logger.warning("authoring_sync skipped (session_id=%s): %s", session_id, exc)

    # Derive gaps
    gap_dicts = gap_engine.derive_gaps(items)
    for gd in gap_dicts:
        gap = GapFinding(
            gap_id=str(uuid.uuid4()),
            snapshot_id=snapshot.snapshot_id,
            section_id=gd["section_id"],
            gap_type=gd["gap_type"],
            severity=gd["severity"],
            description=gd["description"],
            suggested_action=gd.get("suggested_action"),
        )
        db.add(gap)

    # Update aggregate counts
    snapshot.total_items = len(items)
    snapshot.complete_items = sum(1 for i in items if i.status == "complete")
    snapshot.blocking_gaps_count = sum(
        1 for gd in gap_dicts if gd["severity"] == "blocking"
    )

    await db.commit()
    await db.refresh(snapshot)
    return snapshot
