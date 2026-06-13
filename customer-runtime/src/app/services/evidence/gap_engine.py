"""Evidence gap auto-derivation engine — SPEC-EVIDENCE-001."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence_gap import EvidenceGap

if TYPE_CHECKING:
    from app.models.evidence_binder import EvidenceBinder
    from app.models.evidence_link import EvidenceLink

# Stub high-risk controls — mirrors STUB_SECTIONS pattern from checklist
STUB_HIGH_RISK_CONTROLS: list[dict] = [
    {"entity_id": "rc-001", "entity_type": "risk_control", "is_high_risk": True},
    {"entity_id": "rc-002", "entity_type": "risk_control", "is_high_risk": False},
]


# @MX:ANCHOR: [AUTO] Gap auto-surfacing — called on every binder GET and after link/file changes
# @MX:REASON: Gaps must always reflect the current link set; stale gaps mislead auditors
async def evaluate_gaps(
    binder: "EvidenceBinder",
    links: list["EvidenceLink"],
    db: AsyncSession,
) -> list[EvidenceGap]:
    """Delete existing gaps for binder, derive fresh gaps, insert, and return them.

    Logic:
    - For each STUB_HIGH_RISK_CONTROLS entry:
      - is_high_risk=True + no 'verifies' link → critical gap (unverified_high_risk)
      - any link present but no 'verifies' → high gap (unlinked_risk_control)
    """
    # Clear stale gaps
    await db.execute(
        delete(EvidenceGap).where(EvidenceGap.binder_id == binder.binder_id)
    )
    await db.flush()

    now = datetime.now(timezone.utc)
    new_gaps: list[EvidenceGap] = []

    for rc in STUB_HIGH_RISK_CONTROLS:
        entity_id = rc["entity_id"]
        is_high_risk = rc["is_high_risk"]

        verifying_links = [
            lnk for lnk in links
            if lnk.source_entity_id == entity_id and lnk.link_type == "verifies"
        ]
        any_links = [lnk for lnk in links if lnk.source_entity_id == entity_id]

        if is_high_risk and not verifying_links:
            gap = EvidenceGap(
                gap_id=str(uuid.uuid4()),
                binder_id=binder.binder_id,
                entity_type=rc["entity_type"],
                entity_id=entity_id,
                gap_type="unverified_high_risk",
                severity="critical",
                surfaced_at=now,
            )
            db.add(gap)
            new_gaps.append(gap)
        elif any_links and not verifying_links:
            gap = EvidenceGap(
                gap_id=str(uuid.uuid4()),
                binder_id=binder.binder_id,
                entity_type=rc["entity_type"],
                entity_id=entity_id,
                gap_type="unlinked_risk_control",
                severity="high",
                surfaced_at=now,
            )
            db.add(gap)
            new_gaps.append(gap)

    await db.flush()
    return new_gaps
