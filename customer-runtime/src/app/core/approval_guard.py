"""Approval guard — blocks document approval if open high findings exist.

# @MX:ANCHOR: [AUTO] assert_no_blocking_findings — approval gate for all document workflows
# @MX:REASON: [AUTO] Critical path: called before any document approval action (REQ-TRACE-010)
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.traceability.finding_service import get_open_high_findings


class ApprovalBlockedError(ValueError):
    """Raised when open high-severity findings block document approval."""


async def assert_no_blocking_findings(
    document_ids: list[str], db: AsyncSession
) -> None:
    """Assert no open high-severity findings exist for the given documents.

    Raises ApprovalBlockedError with count if blocking findings exist.
    """
    findings = await get_open_high_findings(document_ids, db)
    if findings:
        raise ApprovalBlockedError(
            f"{len(findings)} open high-severity finding(s) block approval. "
            "Resolve or approve exceptions before proceeding."
        )
