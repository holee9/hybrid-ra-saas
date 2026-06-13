"""Pydantic schemas for checklist endpoints."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ChecklistItemOut(BaseModel):
    """Single checklist item output."""

    checklist_item_id: str
    section_id: str
    status: str
    blocking: bool
    evidence_required: bool

    model_config = ConfigDict(from_attributes=True)


class ChecklistOut(BaseModel):
    """Checklist response for a pack + product combination."""

    items: list[ChecklistItemOut]
    required_count: int
    blocking_count: int
