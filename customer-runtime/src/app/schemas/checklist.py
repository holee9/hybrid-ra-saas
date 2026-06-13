"""Pydantic schemas for checklist endpoints — SPEC-CHECKLIST-001."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class GenerateRequest(BaseModel):
    pack_id: str
    session_id: str | None = None


class ChecklistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    checklist_item_id: str
    snapshot_id: str
    section_id: str
    status: str
    blocking: bool
    evidence_required: bool
    evidence_satisfied: bool
    reviewer_status: str | None
    waiver_justification: str | None


class GapFindingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    gap_id: str
    snapshot_id: str
    section_id: str
    gap_type: str
    severity: str
    description: str
    suggested_action: str | None
    resolved_at: datetime | None


class ChecklistSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_id: str
    session_id: str | None
    pack_id: str
    generated_at: datetime
    total_items: int
    complete_items: int
    blocking_gaps_count: int
    status: str


class ChecklistDetailOut(ChecklistSnapshotOut):
    items: list[ChecklistItemOut] = []
    gaps: list[GapFindingOut] = []


class ItemPatch(BaseModel):
    status: str


class WaiveRequest(BaseModel):
    justification: str


class ExportRequest(BaseModel):
    format: str  # json/xlsx/pdf


class ExportOut(BaseModel):
    export_id: str
    file_ref: str
    format: str


class SummaryOut(BaseModel):
    snapshot_id: str
    completion_pct: float
    blocking_gaps_count: int
    total_items: int
    complete_items: int
    status: str
