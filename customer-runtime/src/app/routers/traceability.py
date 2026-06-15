"""Traceability router — SPEC-TRACEABILITY-001.

# @MX:NOTE: [AUTO] 5 endpoints: scan, findings list, graph, resolve finding, impact analysis
"""
from __future__ import annotations

import uuid
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db
from app.models.consistency_finding import ConsistencyFinding
from app.models.traceability_edge import TraceabilityEdge
from app.models.traceability_node import TraceabilityNode
from app.schemas.traceability import (
    EdgeOut,
    FindingOut,
    GraphOut,
    ImpactAnalysisOut,
    ImpactRequest,
    NodeOut,
    ResolveRequest,
    ScanRequest,
    ScanResult,
)
from app.services.traceability.finding_service import (
    FindingResolveError,
    resolve_finding,
)
from app.services.traceability.graph_builder import build_nodes
from app.services.traceability.impact_service import analyze_impact
from app.services.traceability.llm_detector import detect_semantic_mismatches
from app.services.traceability.rule_linker import apply_rule_links

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/traceability", tags=["traceability"])


@router.post("/scan", response_model=ScanResult)
async def scan_documents(
    body: ScanRequest,
    db: AsyncSession = Depends(get_db),
) -> ScanResult:
    """Scan stub documents, build nodes, apply rule links, run LLM detector."""
    # Count findings before scan
    findings_before = len(
        list((await db.execute(select(ConsistencyFinding))).scalars().all())
    )
    edges_before = len(
        list((await db.execute(select(TraceabilityEdge))).scalars().all())
    )

    nodes = await build_nodes(body.document_id, db)

    _ = await apply_rule_links(nodes, db)

    # Build node lookup for LLM detector
    node_map = {n.node_id: n for n in nodes}
    all_edges = list((await db.execute(select(TraceabilityEdge))).scalars().all())
    _ = await detect_semantic_mismatches(all_edges, node_map, db)

    await db.commit()

    # Count new edges and findings
    findings_after = len(
        list((await db.execute(select(ConsistencyFinding))).scalars().all())
    )
    edges_after = len(
        list((await db.execute(select(TraceabilityEdge))).scalars().all())
    )

    return ScanResult(
        scan_id=str(uuid.uuid4()),
        nodes_scanned=len(nodes),
        edges_created=edges_after - edges_before,
        findings_created=findings_after - findings_before,
    )


@router.get("/findings", response_model=list[FindingOut])
async def list_findings(
    status: Optional[str] = Query(default=None),
    severity: Optional[str] = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[FindingOut]:
    """List consistency findings with optional status and severity filters."""
    stmt = select(ConsistencyFinding)
    if status:
        stmt = stmt.where(ConsistencyFinding.status == status)
    if severity:
        stmt = stmt.where(ConsistencyFinding.severity == severity)
    findings = list((await db.execute(stmt)).scalars().all())
    return [FindingOut.model_validate(f) for f in findings]


@router.get("/graph", response_model=GraphOut)
async def get_graph(
    db: AsyncSession = Depends(get_db),
) -> GraphOut:
    """Return all nodes and edges for D3.js/cytoscape visualization."""
    nodes = list((await db.execute(select(TraceabilityNode))).scalars().all())
    edges = list((await db.execute(select(TraceabilityEdge))).scalars().all())
    return GraphOut(
        nodes=[NodeOut.model_validate(n) for n in nodes],
        edges=[EdgeOut.model_validate(e) for e in edges],
    )


@router.post("/findings/{finding_id}/resolve", response_model=FindingOut)
async def resolve_finding_endpoint(
    finding_id: str,
    body: ResolveRequest,
    db: AsyncSession = Depends(get_db),
) -> FindingOut:
    """Resolve a consistency finding. Requires justification for exception_approved."""
    try:
        finding = await resolve_finding(
            finding_id, body.resolution, body.justification, db
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Finding not found")
    except FindingResolveError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    await db.commit()
    return FindingOut.model_validate(finding)


@router.post("/impact", response_model=ImpactAnalysisOut)
async def impact_analysis_endpoint(
    body: ImpactRequest,
    db: AsyncSession = Depends(get_db),
) -> ImpactAnalysisOut:
    """Perform BFS impact analysis from the given node."""
    # Verify node exists
    node = await db.get(TraceabilityNode, body.node_id)
    if node is None:
        raise HTTPException(status_code=404, detail="Node not found")

    analysis = await analyze_impact(body.node_id, body.change_summary, db)
    await db.commit()
    await db.refresh(analysis)
    return ImpactAnalysisOut.model_validate(analysis)
