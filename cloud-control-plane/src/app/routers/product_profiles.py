"""Product profiles router — device registration endpoint."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_async_session
from app.models.product_profile import ProductProfile
from app.schemas.product_profile import ProductProfileCreate, ProductProfileOut

router = APIRouter(prefix="/product-profiles", tags=["product-profiles"])


@router.post("", response_model=ProductProfileOut, status_code=201)
async def create_product_profile(
    body: ProductProfileCreate,
    db: AsyncSession = Depends(get_async_session),
) -> ProductProfileOut:
    """Register a new product profile.

    Returns 201 with product_id and created_at.
    Returns 422 if device_name is missing (Pydantic validation).
    """
    profile = ProductProfile(
        product_id=str(uuid.uuid4()),
        device_name=body.device_name,
        classification=body.classification,
        intended_use=body.intended_use,
        target_market=body.target_market,
        technology_type=body.technology_type,
        device_family=body.device_family,
        software_in_device=body.software_in_device,
    )
    db.add(profile)
    await db.flush()
    return ProductProfileOut.model_validate(profile)
