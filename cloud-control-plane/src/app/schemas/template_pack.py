"""Pydantic schemas for TemplatePack endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.product_profile import ProductProfileCreate


class ResolveRequest(BaseModel):
    """Request body for POST /template-packs/resolve."""

    product_id: str | None = None
    product_profile: ProductProfileCreate | None = None


class PackSummary(BaseModel):
    """Summary of a TemplatePack for list responses."""

    pack_id: str
    pathway_id: str
    device_family: str
    version: str
    status: str

    model_config = ConfigDict(from_attributes=True)


class SectionOut(BaseModel):
    """Section output within a document detail response."""

    section_id: str
    section_key: str
    title: str
    required: bool
    instructions: str | None = None
    placeholder: str | None = None
    source_reference_ids: list[str] = []
    is_internal: bool = False
    sort_order: int = 0
    applicability_rule_id: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SourceReferenceOut(BaseModel):
    """Source reference output."""

    ref_id: str
    regulation_name: str
    article: str | None = None
    url: str

    model_config = ConfigDict(from_attributes=True)


class DocumentOut(BaseModel):
    """Document output with sections."""

    document_id: str
    doc_type: str
    title: str
    required: bool
    export_format: str | None = None
    sort_order: int = 0
    sections: list[SectionOut] = []

    model_config = ConfigDict(from_attributes=True)


class PackDetail(BaseModel):
    """Full detail of a TemplatePack with documents/sections/source_refs."""

    pack_id: str
    pathway_id: str
    device_family: str
    version: str
    status: str
    documents: list[DocumentOut] = []
    source_references: list[SourceReferenceOut] = []

    model_config = ConfigDict(from_attributes=True)


class TemplatePackCreate(BaseModel):
    """Input schema for POST /template-packs (admin)."""

    pack_id: str
    pathway_id: str
    device_family: str
    version: str
    source_version: str | None = None
    status: str = "draft"
    documents: list[dict[str, Any]] = []


class TemplatePackCreateResponse(BaseModel):
    """Response for POST /template-packs."""

    pack_id: str
    version: str
