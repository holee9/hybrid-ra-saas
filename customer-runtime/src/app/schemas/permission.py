"""SPEC-PERMISSION-001: Pydantic v2 request/response schemas."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    """POST /auth/login body."""
    model_config = ConfigDict(extra="forbid")

    email: str = Field(..., description="User email")
    password: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """JWT token response returned by /auth/login and /auth/refresh."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="TTL in seconds")
    refresh_token: str | None = Field(
        default=None, description="Opaque refresh token for POST /auth/refresh"
    )


class RefreshRequest(BaseModel):
    """POST /auth/refresh body."""
    model_config = ConfigDict(extra="forbid")

    refresh_token: str


class LogoutRequest(BaseModel):
    """POST /auth/logout body — revokes a refresh token."""
    model_config = ConfigDict(extra="forbid")

    refresh_token: str


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

class UserOut(BaseModel):
    """Public user representation — hashed_password is never included."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    """POST /users body (admin creates user)."""
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str = Field(..., min_length=8)
    role: str = "practitioner"


class UserRoleUpdate(BaseModel):
    """PUT /users/{id}/role body."""
    model_config = ConfigDict(extra="forbid")

    role: str


# ---------------------------------------------------------------------------
# Review Items
# ---------------------------------------------------------------------------

class ReviewItemCreate(BaseModel):
    """POST /review-items body."""
    model_config = ConfigDict(extra="forbid")

    title: str = Field(..., min_length=1, max_length=512)
    description: str | None = None


class ReviewItemOut(BaseModel):
    """Review item response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    title: str
    description: str | None
    submitted_by: str
    assigned_to: str | None
    status: str
    created_at: datetime
    updated_at: datetime


class ReviewItemAssign(BaseModel):
    """PUT /review-items/{id}/assign body."""
    model_config = ConfigDict(extra="forbid")

    assigned_to: str


# ---------------------------------------------------------------------------
# Review Decisions
# ---------------------------------------------------------------------------

class ReviewDecisionCreate(BaseModel):
    """POST /review-items/{id}/decide body."""
    model_config = ConfigDict(extra="forbid")

    decision: str = Field(..., description="approved | rejected | exception_approved")
    rationale: str = Field(..., min_length=1)


class ReviewDecisionOut(BaseModel):
    """Review decision response."""
    model_config = ConfigDict(from_attributes=True)

    id: str
    review_item_id: str
    decided_by: str
    decision: str
    rationale: str
    decided_at: datetime
