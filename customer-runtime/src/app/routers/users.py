"""SPEC-PERMISSION-001: /users endpoints."""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.deps import get_current_user, get_db, require_role
from app.models.user import RoleAuditLog, User
from app.schemas.permission import UserCreate, UserOut, UserRoleUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)) -> UserOut:
    """Return the authenticated user's profile."""
    return UserOut.model_validate(current_user)


@router.get(
    "",
    response_model=list[UserOut],
    dependencies=[Depends(require_role("admin"))],
)
async def list_users(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[UserOut]:
    """List all users in the current tenant. Requires admin role."""
    result = await db.execute(
        select(User).where(User.tenant_id == current_user.tenant_id)
    )
    users = result.scalars().all()
    return [UserOut.model_validate(u) for u in users]


@router.post(
    "",
    response_model=UserOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role("admin"))],
)
async def create_user(
    body: UserCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """Create a new user in the current tenant. Requires admin role."""
    existing = await db.execute(
        select(User).where(User.email == body.email, User.tenant_id == current_user.tenant_id)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists in this tenant",
        )

    user = User(
        tenant_id=current_user.tenant_id,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.put(
    "/{user_id}/role",
    response_model=UserOut,
    dependencies=[Depends(require_role("admin"))],
)
async def update_user_role(
    user_id: str,
    body: UserRoleUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """Change a user's role and write an audit log entry. Requires admin role."""
    result = await db.execute(
        select(User).where(User.id == user_id, User.tenant_id == current_user.tenant_id)
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    old_role = target.role
    target.role = body.role

    log = RoleAuditLog(
        tenant_id=current_user.tenant_id,
        target_user_id=target.id,
        changed_by=current_user.id,
        old_role=old_role,
        new_role=body.role,
        changed_at=datetime.now(timezone.utc),
    )
    db.add(log)
    await db.flush()
    await db.refresh(target)
    return UserOut.model_validate(target)
