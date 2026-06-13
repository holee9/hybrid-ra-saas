"""Pydantic schemas for ProductProfile endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProductProfileCreate(BaseModel):
    """Input schema for creating a ProductProfile."""

    device_name: str
    classification: str | None = None
    intended_use: str | None = None
    target_market: list[str] = []
    technology_type: str | None = None
    device_family: str | None = None
    software_in_device: bool = False

    model_config = ConfigDict(from_attributes=True)


class ProductProfileOut(BaseModel):
    """Response schema after creating a ProductProfile."""

    product_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
