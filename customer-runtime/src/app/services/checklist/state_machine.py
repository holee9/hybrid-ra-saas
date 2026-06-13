"""ChecklistItem state machine — SPEC-CHECKLIST-001.

# @MX:ANCHOR: [AUTO] validate_item_transition — checklist state guard
# @MX:REASON: [AUTO] All checklist item status changes flow through this; blocking waiver rule enforced here
"""

# Allowed transitions: current_status -> set of allowed next statuses
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"in_progress", "waived"},
    "in_progress": {"complete", "blocked"},
    "blocked": {"in_progress"},
    "complete": set(),   # terminal
    "waived": set(),     # terminal
}


class ChecklistStateError(ValueError):
    """Raised when a forbidden checklist item state transition is attempted."""


def validate_item_transition(current: str, new: str, blocking: bool) -> None:
    """Validate a checklist item status transition.

    Args:
        current: Current item status.
        new: Desired next status.
        blocking: Whether the item is required (blocking=True cannot be waived).

    Raises:
        ChecklistStateError: For any forbidden transition.
    """
    # REQ-CHECK-012: required items cannot be waived
    if new == "waived" and blocking:
        raise ChecklistStateError("Required items cannot be waived")

    allowed = ALLOWED_TRANSITIONS.get(current, set())
    if new not in allowed:
        raise ChecklistStateError(
            f"Transition {current}→{new} not allowed. Allowed: {sorted(allowed)}"
        )
