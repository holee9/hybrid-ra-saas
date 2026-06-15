"""Section state machine for SPEC-AUTHORING-001.

# @MX:ANCHOR: [AUTO] section_state.validate_transition — state machine guard
# @MX:REASON: [AUTO] All section status changes flow through this; invalid transitions blocked here
"""
from fastapi import HTTPException


class StateTransitionError(HTTPException):
    """Raised when a forbidden section state transition is attempted."""

    def __init__(self, detail: str) -> None:
        super().__init__(status_code=400, detail=detail)


# Allowed transitions: current_status -> set of allowed next statuses
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "empty": {"ai_draft", "human_edited", "skipped"},
    "ai_draft": {"human_edited"},
    "human_edited": {"complete"},
    "complete": {"human_edited"},
    "skipped": {"empty"},
}


def validate_transition(current_status: str, new_status: str, is_required: bool) -> None:
    """Validate a section status transition.

    Args:
        current_status: Current section status.
        new_status: Desired next status.
        is_required: Whether the section is required (cannot be skipped).

    Raises:
        StateTransitionError: For any forbidden transition.
    """
    allowed = ALLOWED_TRANSITIONS.get(current_status, set())

    if new_status not in allowed:
        raise StateTransitionError(
            f"Transition from '{current_status}' to '{new_status}' is not allowed. "
            f"Allowed: {sorted(allowed)}"
        )

    # REQ-AUTHOR-014: required sections cannot be skipped
    if new_status == "skipped" and is_required:
        raise StateTransitionError(
            "Required sections cannot be skipped."
        )
