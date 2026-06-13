"""Finding CRUD and resolution service — SPEC-TRACEABILITY-001."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consistency_finding import ConsistencyFinding
from app.models.traceability_node import TraceabilityNode


class FindingResolveError(ValueError):
    """Raised when exception_approved resolution is missing justification."""


async def resolve_finding(
    finding_id: str,
    resolution: str,
    justification: str | None,
    db: AsyncSession,
) -> ConsistencyFinding:
    """Resolve a consistency finding.

    resolution: "resolved" | "exception_approved"
    Raises FindingResolveError if exception_approved without justification (REQ-TRACE-013).
    """
    finding = await db.get(ConsistencyFinding, finding_id)
    if finding is None:
        raise KeyError(f"Finding {finding_id} not found")

    if resolution == "exception_approved" and not justification:
        raise FindingResolveError(
            "justification is required for exception_approved resolution"
        )

    finding.status = resolution
    if justification:
        finding.justification = justification

    await db.flush()
    await db.refresh(finding)
    return finding


async def get_open_high_findings(
    document_ids: list[str], db: AsyncSession
) -> list[ConsistencyFinding]:
    """Return open high-severity findings for nodes in the given documents.

    Used by approval_guard.
    """
    # Get all node_ids for given documents
    node_stmt = select(TraceabilityNode.node_id).where(
        TraceabilityNode.document_id.in_(document_ids)
    )
    node_ids = list((await db.execute(node_stmt)).scalars().all())

    if not node_ids:
        return []

    stmt = select(ConsistencyFinding).where(
        ConsistencyFinding.status == "open",
        ConsistencyFinding.severity == "high",
        ConsistencyFinding.source_node_id.in_(node_ids),
    )
    return list((await db.execute(stmt)).scalars().all())
