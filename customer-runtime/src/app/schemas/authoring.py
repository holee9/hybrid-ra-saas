"""Pydantic schemas for SPEC-AUTHORING-001 Guided Authoring Workspace."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class SessionCreate(BaseModel):
    product_profile_id: str
    pack_id: str
    created_by: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SessionOut(BaseModel):
    session_id: str
    status: str
    total_sections: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SectionEntryOut(BaseModel):
    entry_id: str
    status: str
    content: str | None = None
    ai_draft: str | None = None
    ai_draft_confidence: float | None = None
    ai_draft_sources: list[str] | None = None
    ai_draft_verified: bool = False

    model_config = ConfigDict(from_attributes=True)


class SectionWithEntry(BaseModel):
    section_id: str
    section_key: str
    title: str
    required: bool
    instructions: str | None = None
    placeholder: str | None = None
    sort_order: int
    entry: SectionEntryOut

    model_config = ConfigDict(from_attributes=True)


class EntryPatch(BaseModel):
    content: str | None = None
    status: str | None = None
    skip_reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ExportRequest(BaseModel):
    format: str  # "docx" | "json"

    model_config = ConfigDict(from_attributes=True)
