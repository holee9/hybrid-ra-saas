"""Evidence Binder Pydantic schemas — SPEC-EVIDENCE-001."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class BinderCreate(BaseModel):
    product_profile_id: str
    name: str
    pack_id: str | None = None


class BinderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    binder_id: str
    product_profile_id: str
    pack_id: str | None
    name: str
    status: str
    created_by: str
    sealed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BinderDetailOut(BinderOut):
    links: list[LinkOut] = []
    files: list[FileOut] = []
    gaps: list[GapOut] = []
    gaps_summary: dict = {}


class LinkCreate(BaseModel):
    source_entity_type: str
    source_entity_id: str
    target_entity_type: str
    target_ref: str
    link_type: str


class LinkOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    link_id: str
    binder_id: str
    source_entity_type: str
    source_entity_id: str
    target_entity_type: str
    target_ref: str
    link_type: str
    created_at: datetime


class FileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    file_id: str
    binder_id: str
    original_filename: str
    content_type: str
    size_bytes: int
    storage_ref: str
    sha256: str
    uploaded_at: datetime


class GapOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    gap_id: str
    binder_id: str
    entity_type: str
    entity_id: str
    gap_type: str
    severity: str
    surfaced_at: datetime


class ExportOut(BaseModel):
    binder_id: str
    filename: str
    size_bytes: int


# Resolve forward references
BinderDetailOut.model_rebuild()
