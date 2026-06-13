"""SPEC-PERMISSION-001: /review-items endpoints."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_user, get_db, require_role
from app.models.user import DecisionType, ReviewDecision, ReviewItem, ReviewStatus, User
from app.schemas.permission import (
    ReviewDecisionCreate,
    ReviewDecisionOut,
    ReviewItemAssign,
    ReviewItemCreate,
    ReviewItemOut,
)

router = APIRouter(prefix="/review-items", tags=["review-items"])


@router.get("", response_model=list[ReviewItemOut])
async def list_review_items(
    status_filter: str | None = Query(default=None, alias="status"),
    assigned_to: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ReviewItemOut]:
    """List review items in the current tenant. All authenticated users may call this."""
    stmt = select(ReviewItem).where(ReviewItem.tenant_id == current_user.tenant_id)
    if status_filter:
        stmt = stmt.where(ReviewItem.status == status_filter)
    if assigned_to:
        stmt = stmt.where(ReviewItem.assigned_to == assigned_to)
    result = await db.execute(stmt)
    items = result.scalars().all()
    return [ReviewItemOut.model_validate(i) for i in items]


@router.post("", response_model=ReviewItemOut, status_code=status.HTTP_201_CREATED)
async def create_review_item(
    body: ReviewItemCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewItemOut:
    """Create a new review item. Any authenticated user may submit."""
    item = ReviewItem(
        tenant_id=current_user.tenant_id,
        title=body.title,
        description=body.description,
        submitted_by=current_user.id,
        status=ReviewStatus.pending,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return ReviewItemOut.model_validate(item)


@router.put(
    "/{item_id}/assign",
    response_model=ReviewItemOut,
    dependencies=[Depends(require_role("quality_manager", "admin"))],
)
async def assign_review_item(
    item_id: str,
    body: ReviewItemAssign,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewItemOut:
    """Assign a review item to a user. Requires quality_manager or admin role."""
    result = await db.execute(
        select(ReviewItem).where(
            ReviewItem.id == item_id,
            ReviewItem.tenant_id == current_user.tenant_id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review item not found")

    # Verify assignee is in same tenant
    assignee_result = await db.execute(
        select(User).where(User.id == body.assigned_to, User.tenant_id == current_user.tenant_id)
    )
    if assignee_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignee not found in tenant")

    item.assigned_to = body.assigned_to
    item.status = ReviewStatus.in_review
    await db.flush()
    await db.refresh(item)
    return ReviewItemOut.model_validate(item)


@router.post(
    "/{item_id}/decide",
    response_model=ReviewDecisionOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("quality_manager", "admin"))],
)
async def decide_review_item(
    item_id: str,
    body: ReviewDecisionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ReviewDecisionOut:
    """Record a decision on a review item (append-only).

    # @MX:ANCHOR: [AUTO] Conflict-of-interest guard — approved/exception_approved
    # @MX:REASON: Business rule: a submitter cannot approve their own submitted item.
    """
    result = await db.execute(
        select(ReviewItem).where(
            ReviewItem.id == item_id,
            ReviewItem.tenant_id == current_user.tenant_id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review item not found")

    # Conflict-of-interest guard: approved/exception_approved decisions
    approving_decisions = {DecisionType.approved.value, DecisionType.exception_approved.value}
    if body.decision in approving_decisions and item.submitted_by == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict of interest: cannot approve your own submitted item",
        )

    decision = ReviewDecision(
        review_item_id=item.id,
        decided_by=current_user.id,
        decision=body.decision,
        rationale=body.rationale,
        decided_at=datetime.now(timezone.utc),
    )
    db.add(decision)

    # Update item status to match decision
    item.status = body.decision  # maps directly: approved/rejected/exception_approved

    await db.flush()
    await db.refresh(decision)
    return ReviewDecisionOut.model_validate(decision)
