"""Traceability matrix export (ZIP bundle) — SPEC-TRACEABILITY-001."""
import io
import json
import zipfile
from typing import Any

from app.models.consistency_finding import ConsistencyFinding
from app.models.traceability_edge import TraceabilityEdge
from app.models.traceability_node import TraceabilityNode


async def export_matrix(
    nodes: list[TraceabilityNode],
    edges: list[TraceabilityEdge],
    findings: list[ConsistencyFinding],
) -> bytes:
    """Build and return ZIP bytes: manifest.json + nodes.json + edges.json + findings.json."""
    buf = io.BytesIO()

    nodes_data = [
        {
            "node_id": n.node_id,
            "document_id": n.document_id,
            "section_id": n.section_id,
            "node_type": n.node_type,
            "content_hash": n.content_hash,
            "created_at": n.created_at.isoformat() if n.created_at else None,
        }
        for n in nodes
    ]

    edges_data = [
        {
            "edge_id": e.edge_id,
            "source_node_id": e.source_node_id,
            "target_node_id": e.target_node_id,
            "edge_type": e.edge_type,
            "confidence": e.confidence,
            "created_by": e.created_by,
            "created_at": e.created_at.isoformat() if e.created_at else None,
        }
        for e in edges
    ]

    findings_data = [
        {
            "finding_id": f.finding_id,
            "finding_type": f.finding_type,
            "severity": f.severity,
            "source_node_id": f.source_node_id,
            "target_node_id": f.target_node_id,
            "description": f.description,
            "status": f.status,
            "justification": f.justification,
            "confidence": f.confidence,
            "created_at": f.created_at.isoformat() if f.created_at else None,
        }
        for f in findings
    ]

    manifest: dict[str, Any] = {
        "version": "1.0",
        "node_count": len(nodes),
        "edge_count": len(edges),
        "finding_count": len(findings),
    }

    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("manifest.json", json.dumps(manifest))
        zf.writestr("nodes.json", json.dumps(nodes_data))
        zf.writestr("edges.json", json.dumps(edges_data))
        zf.writestr("findings.json", json.dumps(findings_data))

    return buf.getvalue()
