"""SPEC-PERMISSION-001: User, ReviewItem, ReviewDecision, RoleAuditLog models."""
import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantMixin, TimestampMixin, new_id


# @MX:NOTE: [AUTO] Role values are the exhaustive RBAC role set for SPEC-PERMISSION-001.
# Adding a role here requires migration + RBAC policy update in require_role().
class UserRole(str, enum.Enum):
    practitioner = "practitioner"
    quality_manager = "quality_manager"
    admin = "admin"


# @MX:NOTE: [AUTO] ReviewItem status transitions are enforced by the decide endpoint.
# Status is append-only once terminal (approved/rejected/exception_approved).
class ReviewStatus(str, enum.Enum):
    pending = "pending"
    in_review = "in_review"
    approved = "approved"
    rejected = "rejected"
    exception_approved = "exception_approved"


class DecisionType(str, enum.Enum):
    approved = "approved"
    rejected = "rejected"
    exception_approved = "exception_approved"


class User(TenantMixin, TimestampMixin, Base):
    """Tenant-scoped user account with RBAC role."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.practitioner,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    submitted_items: Mapped[list["ReviewItem"]] = relationship(
        "ReviewItem",
        foreign_keys="ReviewItem.submitted_by",
        back_populates="submitter",
    )
    assigned_items: Mapped[list["ReviewItem"]] = relationship(
        "ReviewItem",
        foreign_keys="ReviewItem.assigned_to",
        back_populates="assignee",
    )
    decisions: Mapped[list["ReviewDecision"]] = relationship(
        "ReviewDecision", back_populates="decider"
    )


class ReviewItem(TenantMixin, TimestampMixin, Base):
    """A review request submitted by a user within a tenant."""

    __tablename__ = "review_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(String(4096), nullable=True)
    submitted_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    assigned_to: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True
    )
    status: Mapped[str] = mapped_column(
        Enum(ReviewStatus, name="review_status"),
        nullable=False,
        default=ReviewStatus.pending,
    )

    submitter: Mapped["User"] = relationship(
        "User", foreign_keys=[submitted_by], back_populates="submitted_items"
    )
    assignee: Mapped["User | None"] = relationship(
        "User", foreign_keys=[assigned_to], back_populates="assigned_items"
    )
    review_decisions: Mapped[list["ReviewDecision"]] = relationship(
        "ReviewDecision", back_populates="review_item"
    )


class ReviewDecision(Base):
    """Append-only audit trail of decisions on review items.

    # @MX:NOTE: [AUTO] ReviewDecision is intentionally append-only (no updated_at).
    # No UPDATE or DELETE operations are permitted — this is an immutable audit record.
    """

    __tablename__ = "review_decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    review_item_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("review_items.id"), nullable=False, index=True
    )
    decided_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    decision: Mapped[str] = mapped_column(
        Enum(DecisionType, name="decision_type"), nullable=False
    )
    rationale: Mapped[str] = mapped_column(String(4096), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )

    review_item: Mapped["ReviewItem"] = relationship(
        "ReviewItem", back_populates="review_decisions"
    )
    decider: Mapped["User"] = relationship("User", back_populates="decisions")


class RoleAuditLog(Base):
    """Immutable record of role changes for compliance audit trail."""

    __tablename__ = "role_audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    target_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    changed_by: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False
    )
    old_role: Mapped[str] = mapped_column(String(64), nullable=False)
    new_role: Mapped[str] = mapped_column(String(64), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=func.now()
    )
