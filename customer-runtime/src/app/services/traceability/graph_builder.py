"""Graph builder — extracts TraceabilityNodes from stub documents.

# @MX:ANCHOR: [AUTO] build_nodes — called by scan endpoint, rule_linker, and impact service
# @MX:REASON: [AUTO] Fan-in >= 3: scan router, rule_linker.apply_rule_links, impact_service.analyze_impact
"""
import hashlib
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.traceability_node import TraceabilityNode

STUB_DOCUMENTS: list[dict[str, Any]] = [
    {
        "document_id": "doc-rms-001",
        "section_id": "sec-4.2",
        "node_type": "risk_control",
        "content": "Risk control for electrical hazard",
    },
    {
        "document_id": "doc-rms-001",
        "section_id": "sec-3.1",
        "node_type": "hazard",
        "content": "Electrical hazard identified",
    },
    {
        "document_id": "doc-srs-001",
        "section_id": "req-001",
        "node_type": "requirement",
        "content": "System shall isolate electrical components",
    },
    {
        "document_id": "doc-test-001",
        "section_id": "tc-001",
        "node_type": "test",
        "content": "Electrical isolation test procedure",
    },
]


async def build_nodes(
    document_id: str | None, db: AsyncSession
) -> list[TraceabilityNode]:
    """Extract and upsert TraceabilityNodes from stub documents.

    If document_id is provided, filter STUB_DOCUMENTS by it; otherwise use all.
    Nodes with unchanged content_hash are skipped (REQ-TRACE-002).
    """
    candidates = (
        [d for d in STUB_DOCUMENTS if d["document_id"] == document_id]
        if document_id
        else STUB_DOCUMENTS
    )

    result_nodes: list[TraceabilityNode] = []

    for doc in candidates:
        content_hash = hashlib.sha256(doc["content"].encode()).hexdigest()

        # Check if node with same document_id+section_id already exists
        stmt = select(TraceabilityNode).where(
            TraceabilityNode.document_id == doc["document_id"],
            TraceabilityNode.section_id == doc["section_id"],
        )
        existing = (await db.execute(stmt)).scalar_one_or_none()

        if existing is not None:
            if existing.content_hash == content_hash:
                # Unchanged — skip (REQ-TRACE-002 incremental update)
                result_nodes.append(existing)
                continue
            # Changed — delete old and insert new
            await db.delete(existing)
            await db.flush()

        node = TraceabilityNode(
            document_id=doc["document_id"],
            section_id=doc["section_id"],
            node_type=doc["node_type"],
            content_hash=content_hash,
        )
        db.add(node)
        result_nodes.append(node)

    await db.flush()

    # Re-query to get all nodes in DB after operation
    if document_id:
        stmt = select(TraceabilityNode).where(
            TraceabilityNode.document_id == document_id
        )
    else:
        stmt = select(TraceabilityNode)

    all_nodes = list((await db.execute(stmt)).scalars().all())
    return all_nodes
