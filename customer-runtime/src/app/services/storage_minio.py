"""MinioAdapter — thin StoragePort wrapper over the existing StorageService.

Existing callers of StorageService / create_storage_service() are unaffected.
"""
from __future__ import annotations

import logging

from app.services.storage import StorageService, create_storage_service

logger = logging.getLogger(__name__)


class MinioAdapter:
    """Implements StoragePort using the existing MinIO-backed StorageService."""

    def __init__(self, service: StorageService | None = None) -> None:
        self._service: StorageService = service or create_storage_service()

    async def upload(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        """Upload bytes; returns the full object key."""
        # StorageService.upload_file uses tenant/key layout; we treat key as full path.
        # Split on first '/' if present so tenant prefix is preserved, else use "_default".
        parts = key.split("/", 1)
        tenant, sub_key = (parts[0], parts[1]) if len(parts) == 2 else ("_default", key)
        return self._service.upload_file(tenant=tenant, key=sub_key, data=data)

    async def download(self, key: str) -> bytes:
        """Download bytes by full object key."""
        parts = key.split("/", 1)
        tenant, sub_key = (parts[0], parts[1]) if len(parts) == 2 else ("_default", key)
        return self._service.get_file(tenant=tenant, key=sub_key)

    # @MX:ANCHOR: [AUTO] Real MinIO delete — replaces no-op stub (SPEC-EVIDENCE-002).
    # @MX:REASON: REQ-EVIDENCE-002-005/006/008: real deletion, error propagation, audit log.
    async def delete(self, key: str) -> None:
        """Delete object from MinIO by full object key.

        REQ-EVIDENCE-002-005: real MinIO object deletion executed.
        REQ-EVIDENCE-002-006: MinIO delete failure propagated (not swallowed).
        REQ-EVIDENCE-002-008: deletion event logged in audit log.
        """
        try:
            self._service._client.delete_object(
                Bucket=self._service._bucket, Key=key
            )
            logger.info(
                "minio_delete_succeeded",
                extra={"object_key": key, "bucket": self._service._bucket},
            )
        except Exception as exc:
            logger.error(
                "minio_delete_failed",
                extra={
                    "object_key": key,
                    "bucket": self._service._bucket,
                    "error": str(exc),
                },
            )
            raise

    async def exists(self, key: str) -> bool:
        """Return True if the object key exists in MinIO."""
        try:
            self._service._client.head_object(
                Bucket=self._service._bucket, Key=key
            )
            return True
        except Exception:
            return False
