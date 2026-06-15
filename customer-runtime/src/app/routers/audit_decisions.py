"""SPEC-PERMISSION-001: GET /audit/decisions endpoint."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db, require_role
from app.models.user import ReviewDecision, ReviewItem, User
from app.schemas.permission import ReviewDecisionOut

router = APIRouter(prefix="/audit", tags=["audit-decisions"])


@router.get(
    "/decisions",
    response_model=list[ReviewDecisionOut],
    dependencies=[Depends(require_role("admin"))],
)
async def list_audit_decisions(
    review_item_id: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ReviewDecisionOut]:
    """Return all decisions in the current tenant. Admin only, paginated."""
    # Join through review_items to scope by tenant
    stmt = (
        select(ReviewDecision)
        .join(ReviewItem, ReviewDecision.review_item_id == ReviewItem.id)
        .where(ReviewItem.tenant_id == current_user.tenant_id)
    )
    if review_item_id:
        stmt = stmt.where(ReviewDecision.review_item_id == review_item_id)
    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    decisions = result.scalars().all()
    return [ReviewDecisionOut.model_validate(d) for d in decisions]
