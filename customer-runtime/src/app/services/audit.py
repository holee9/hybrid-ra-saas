"""Audit service — records append-only audit events."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent
from app.models.base import new_id


class AuditService:
    async def record(
        self,
        db: AsyncSession,
        tenant_id: str,
        user_id: str,
        action: str,
        before_hash: str | None = None,
        after_hash: str | None = None,
    ) -> AuditEvent:
        """Append a new audit event. AuditEvent UPDATE/DELETE will raise RuntimeError."""
        event = AuditEvent(
            event_id=new_id(),
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            before_hash=before_hash,
            after_hash=after_hash,
        )
        db.add(event)
        await db.flush()
        return event
