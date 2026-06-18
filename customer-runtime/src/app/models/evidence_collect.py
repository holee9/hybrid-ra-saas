"""EvidenceCollect ORM model — BFF API (Issue #47)."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


def _now() -> datetime:
    return datetime.now(timezone.utc)


class EvidenceCollect(Base, TimestampMixin):
    """Stores evidence collection results for BFF API consumers (e.g. ra-med-bot).

    # @MX:ANCHOR: [AUTO] Evidence BFF persistence boundary — collect_id is the stable
    #             external handle referenced by synthesize and export endpoints.
    # @MX:REASON: fan_in >= 3 (collect POST, GET /{id}, synthesize POST, export GET)
    """

    __tablename__ = "evidence_collect"

    collect_id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False)
    document_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    items: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    synthesis: Mapped[str | None] = mapped_column(Text, nullable=True, default=None)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="collected")
