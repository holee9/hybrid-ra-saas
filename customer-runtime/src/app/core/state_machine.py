"""DocumentStatus transition validator."""
from app.models.document import DocumentStatus

# Valid transitions: current -> set of allowed next states
_TRANSITIONS: dict[DocumentStatus, set[DocumentStatus]] = {
    DocumentStatus.UPLOADED: {DocumentStatus.PARSING},
    DocumentStatus.PARSING: {
        DocumentStatus.NEEDS_CORRECTION,
        DocumentStatus.READY_FOR_CHECK,
        DocumentStatus.REJECTED,
    },
    DocumentStatus.NEEDS_CORRECTION: {DocumentStatus.PARSING, DocumentStatus.REJECTED},
    DocumentStatus.READY_FOR_CHECK: {DocumentStatus.APPROVED, DocumentStatus.REJECTED},
    DocumentStatus.APPROVED: set(),
    DocumentStatus.REJECTED: set(),
}


def validate_transition(current: DocumentStatus, new: DocumentStatus) -> None:
    """Raise ValueError if the transition current -> new is not allowed."""
    allowed = _TRANSITIONS.get(current, set())
    if new not in allowed:
        raise ValueError(
            f"Invalid transition: {current.value} -> {new.value}. "
            f"Allowed: {[s.value for s in allowed]}"
        )
