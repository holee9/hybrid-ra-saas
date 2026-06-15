"""Pydantic schemas for traceability endpoints — SPEC-TRACEABILITY-001."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class ScanRequest(BaseModel):
    document_id: str | None = None  # None = scan all stub docs


class ScanResult(BaseModel):
    scan_id: str
    nodes_scanned: int
    edges_created: int
    findings_created: int


class NodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    node_id: str
    document_id: str
    section_id: str | None
    node_type: str
    content_hash: str
    created_at: datetime


class EdgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    edge_id: str
    source_node_id: str
    target_node_id: str
    edge_type: str
    confidence: float | None
    created_by: str
    created_at: datetime


class FindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    finding_id: str
    finding_type: str
    severity: str
    source_node_id: str
    target_node_id: str | None
    description: str
    status: str
    justification: str | None
    confidence: float | None
    created_at: datetime


class ResolveRequest(BaseModel):
    resolution: str  # "resolved" | "exception_approved"
    justification: str | None = None


class ImpactRequest(BaseModel):
    node_id: str
    change_summary: str


class ImpactAnalysisOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_id: str
    trigger_node_id: str
    trigger_change_summary: str
    affected_nodes: list[dict[str, Any]]
    created_at: datetime


class GraphOut(BaseModel):
    nodes: list[NodeOut]
    edges: list[EdgeOut]
