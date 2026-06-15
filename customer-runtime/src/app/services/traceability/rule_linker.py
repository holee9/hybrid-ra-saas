"""Rule-based edge creation and consistency finding generation.

# @MX:ANCHOR: [AUTO] apply_rule_links — called by scan router and llm_detector
# @MX:REASON: [AUTO] Public API boundary: creates both edges and ConsistencyFindings from rule engine
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.consistency_finding import ConsistencyFinding
from app.models.traceability_edge import TraceabilityEdge
from app.models.traceability_node import TraceabilityNode


async def apply_rule_links(
    nodes: list[TraceabilityNode], db: AsyncSession
) -> list[TraceabilityEdge]:
    """Apply rule-based edges and generate consistency findings.

    Rules:
    - hazard node -> risk_control node in same document => "mitigates" edge
    - risk_control node -> test node => "verifies" edge
    Missing chains => ConsistencyFinding(finding_type="missing_link", severity="high")
    Orphan nodes => ConsistencyFinding(finding_type="orphan_node", severity="medium")
    """
    created_edges: list[TraceabilityEdge] = []

    # Index nodes by type and document
    by_type_and_doc: dict[str, list[TraceabilityNode]] = {}
    for node in nodes:
        key = f"{node.node_type}:{node.document_id}"
        by_type_and_doc.setdefault(key, []).append(node)

    # Track node_ids that get edges
    nodes_with_edges: set[str] = set()

    # Rule 1: hazard → risk_control (same document) => mitigates
    for node in nodes:
        if node.node_type != "hazard":
            continue
        controls = by_type_and_doc.get(f"risk_control:{node.document_id}", [])
        if controls:
            for ctrl in controls:
                edge = await _upsert_edge(
                    node.node_id, ctrl.node_id, "mitigates", "rule", None, db
                )
                if edge:
                    created_edges.append(edge)
                    nodes_with_edges.add(node.node_id)
                    nodes_with_edges.add(ctrl.node_id)
        else:
            # Missing risk_control for this hazard
            finding = ConsistencyFinding(
                finding_type="missing_link",
                severity="high",
                source_node_id=node.node_id,
                target_node_id=None,
                description=(
                    f"Hazard node {node.node_id} in document {node.document_id} "
                    "has no corresponding risk_control node."
                ),
                status="open",
            )
            db.add(finding)

    # Rule 2: risk_control → test => verifies
    all_tests = [n for n in nodes if n.node_type == "test"]
    for node in nodes:
        if node.node_type != "risk_control":
            continue
        if all_tests:
            for test_node in all_tests:
                edge = await _upsert_edge(
                    node.node_id, test_node.node_id, "verifies", "rule", None, db
                )
                if edge:
                    created_edges.append(edge)
                    nodes_with_edges.add(node.node_id)
                    nodes_with_edges.add(test_node.node_id)
        else:
            finding = ConsistencyFinding(
                finding_type="missing_link",
                severity="high",
                source_node_id=node.node_id,
                target_node_id=None,
                description=(
                    f"Risk control node {node.node_id} has no verifying test node."
                ),
                status="open",
            )
            db.add(finding)

    # Orphan detection: nodes with 0 incoming AND 0 outgoing edges after rule linking
    for node in nodes:
        if node.node_id not in nodes_with_edges:
            # Check DB for any existing edges
            has_edge = await _node_has_any_edge(node.node_id, db)
            if not has_edge:
                finding = ConsistencyFinding(
                    finding_type="orphan_node",
                    severity="medium",
                    source_node_id=node.node_id,
                    target_node_id=None,
                    description=(
                        f"Node {node.node_id} (type={node.node_type}) "
                        "has no incoming or outgoing edges."
                    ),
                    status="open",
                )
                db.add(finding)

    await db.flush()
    return created_edges


async def _upsert_edge(
    source_id: str,
    target_id: str,
    edge_type: str,
    created_by: str,
    confidence: float | None,
    db: AsyncSession,
) -> TraceabilityEdge | None:
    """Create edge if it does not already exist."""
    stmt = select(TraceabilityEdge).where(
        TraceabilityEdge.source_node_id == source_id,
        TraceabilityEdge.target_node_id == target_id,
        TraceabilityEdge.edge_type == edge_type,
    )
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        return None

    edge = TraceabilityEdge(
        source_node_id=source_id,
        target_node_id=target_id,
        edge_type=edge_type,
        confidence=confidence,
        created_by=created_by,
    )
    db.add(edge)
    return edge


async def _node_has_any_edge(node_id: str, db: AsyncSession) -> bool:
    """Return True if node participates in any edge."""
    stmt = select(TraceabilityEdge).where(
        (TraceabilityEdge.source_node_id == node_id)
        | (TraceabilityEdge.target_node_id == node_id)
    )
    result = (await db.execute(stmt)).first()
    return result is not None
