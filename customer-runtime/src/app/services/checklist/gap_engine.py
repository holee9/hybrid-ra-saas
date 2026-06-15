"""GapFinding derivation engine — SPEC-CHECKLIST-001."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.checklist_item import ChecklistItem

# Severity ordering for dedup: blocking > warning > info
_SEVERITY_RANK = {"blocking": 2, "warning": 1, "info": 0}


def derive_gaps(items: list["ChecklistItem"]) -> list[dict]:
    """Derive gap findings from a list of checklist items.

    Returns a list of gap dicts for bulk INSERT into gap_findings.
    Deduplication: one gap per (section_id, gap_type) — highest severity wins.

    Args:
        items: ChecklistItem instances to evaluate.

    Returns:
        List of dicts with keys: section_id, gap_type, severity, description, suggested_action.
    """
    # Accumulate: (section_id, gap_type) -> best gap dict
    best: dict[tuple[str, str], dict] = {}

    def _upsert(gap: dict) -> None:
        key = (gap["section_id"], gap["gap_type"])
        existing = best.get(key)
        if existing is None:
            best[key] = gap
        else:
            if _SEVERITY_RANK[gap["severity"]] > _SEVERITY_RANK[existing["severity"]]:
                best[key] = gap

    for item in items:
        is_complete = item.status == "complete"
        severity = "blocking" if item.blocking else "warning"

        # Gap 1: item not complete
        if not is_complete:
            _upsert({
                "section_id": item.section_id,
                "gap_type": "missing_content",
                "severity": severity,
                "description": f"Section '{item.section_id}' is not complete (status: {item.status}).",
                "suggested_action": "Complete the section content before finalizing.",
            })

        # Gap 2: evidence required but not satisfied
        if item.evidence_required and not item.evidence_satisfied:
            ev_severity = "blocking" if item.blocking else "warning"
            _upsert({
                "section_id": item.section_id,
                "gap_type": "no_evidence",
                "severity": ev_severity,
                "description": f"Section '{item.section_id}' requires evidence but none is provided.",
                "suggested_action": "Upload or link supporting evidence for this section.",
            })

        # Gap 3: reviewer has not reviewed non-complete items
        if not is_complete and (item.reviewer_status is None or item.reviewer_status == "pending"):
            _upsert({
                "section_id": item.section_id,
                "gap_type": "unreviewed",
                "severity": "warning",
                "description": f"Section '{item.section_id}' has not been reviewed.",
                "suggested_action": "Assign a reviewer to validate this section.",
            })

    return list(best.values())
