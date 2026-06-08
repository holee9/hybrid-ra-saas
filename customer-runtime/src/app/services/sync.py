"""Sync service — REQ-API-012 delta manifest generation.

Builds a tenant-scoped manifest of entity changes without exposing
sensitive document content (FR-210).

# @MX:ANCHOR: [AUTO] SyncService.build_manifest — public API boundary for cloud sync
# @MX:REASON: fan_in >= 3 (sync router, test_sync, future scheduled sync job)
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.requirement import Requirement
from app.models.control import Control


class SyncService:
    """Generates delta manifests for cloud sync without leaking customer data."""

    async def build_manifest(
        self,
        db: AsyncSession,
        tenant_id: str,
        since: str | None,
    ) -> dict[str, Any]:
        """Build a delta manifest for the tenant.

        Args:
            db: Async database session.
            tenant_id: Tenant scope for the query.
            since: ISO 8601 timestamp; if provided, only entities updated after this time
                   are included. None means return all entities.

        Returns:
            dict with keys: manifest_hash, generated_at, entries, total_count.
            Sensitive fields (storage_key, content, raw_text) are NEVER included (FR-210).
        """
        since_dt: datetime | None = None
        if since:
            since_dt = datetime.fromisoformat(since)
            if since_dt.tzinfo is None:
                since_dt = since_dt.replace(tzinfo=timezone.utc)

        all_entities = await self._fetch_entities(db=db, tenant_id=tenant_id)

        # Apply since filter
        if since_dt is not None:
            filtered = []
            for entity in all_entities:
                updated_at = entity["updated_at"]
                if isinstance(updated_at, datetime):
                    if updated_at.tzinfo is None:
                        updated_at = updated_at.replace(tzinfo=timezone.utc)
                    if updated_at > since_dt:
                        filtered.append(entity)
            entities = filtered
        else:
            entities = all_entities

        entries = [self._to_entry(e) for e in entities]

        # Compute manifest_hash from serialized entries
        entries_json = json.dumps(entries, default=str, sort_keys=True)
        manifest_hash = hashlib.sha256(entries_json.encode()).hexdigest()

        return {
            "manifest_hash": manifest_hash,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "entries": entries,
            "total_count": len(entries),
        }

    def _to_entry(self, entity: dict[str, Any]) -> dict[str, Any]:
        """Convert raw entity dict to a manifest entry.

        Computes version_hash from entity_id + updated_at (non-sensitive fields only).
        NEVER includes storage_key, content, raw_text, or other sensitive data (FR-210).
        """
        entity_id = entity["entity_id"]
        updated_at = entity["updated_at"]
        updated_at_str = updated_at.isoformat() if isinstance(updated_at, datetime) else str(updated_at)

        version_content = f"{entity_id}:{updated_at_str}"
        version_hash = hashlib.sha256(version_content.encode()).hexdigest()

        return {
            "entity_type": entity["entity_type"],
            "entity_id": entity_id,
            "version_hash": version_hash,
            "action": "updated",
            "updated_at": updated_at_str,
        }

    async def _fetch_entities(
        self,
        db: AsyncSession,
        tenant_id: str,
    ) -> list[dict[str, Any]]:
        """Query products, requirements, and controls for the tenant.

        # @MX:WARN: [AUTO] Full table scan per entity type — no pagination in MVP
        # @MX:REASON: Manifest is internal sync artifact; large tenants may need pagination in v2
        Returns only non-sensitive fields (entity_id, entity_type, updated_at).
        """
        entities: list[dict[str, Any]] = []

        # Products
        try:
            result = await db.execute(
                select(Product.product_id, Product.updated_at).where(
                    Product.tenant_id == tenant_id
                )
            )
            for row in result.all():
                entities.append({
                    "entity_type": "product",
                    "entity_id": row.product_id,
                    "updated_at": row.updated_at,
                })
        except Exception:  # noqa: BLE001
            pass

        # Requirements
        try:
            result = await db.execute(
                select(Requirement.req_id, Requirement.updated_at).where(
                    Requirement.tenant_id == tenant_id
                )
            )
            for row in result.all():
                entities.append({
                    "entity_type": "requirement",
                    "entity_id": row.req_id,
                    "updated_at": row.updated_at,
                })
        except Exception:  # noqa: BLE001
            pass

        # Controls
        try:
            result = await db.execute(
                select(Control.control_id, Control.updated_at).where(
                    Control.tenant_id == tenant_id
                )
            )
            for row in result.all():
                entities.append({
                    "entity_type": "control",
                    "entity_id": row.control_id,
                    "updated_at": row.updated_at,
                })
        except Exception:  # noqa: BLE001
            pass

        return entities
