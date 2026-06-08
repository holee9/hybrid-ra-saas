"""Pydantic schemas for sync manifest — REQ-API-012."""
from pydantic import BaseModel


class ManifestEntry(BaseModel):
    """A single entity in the sync manifest."""

    entity_type: str
    entity_id: str
    version_hash: str
    action: str
    updated_at: str


class ManifestResponse(BaseModel):
    """Response schema for GET /sync/manifest."""

    manifest_hash: str
    generated_at: str
    entries: list[ManifestEntry]
    total_count: int
