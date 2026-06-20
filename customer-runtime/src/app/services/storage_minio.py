"""MinioAdapter — thin StoragePort wrapper over the existing StorageService.

Existing callers of StorageService / create_storage_service() are unaffected.
"""
from __future__ import annotations

from app.services.storage import StorageService, create_storage_service


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

    async def delete(self, key: str) -> None:
        """Delete object by key (no-op stub — StorageService has no delete yet)."""
        # StorageService does not expose delete; implement directly via boto3 client.
        self._service._client.delete_object(
            Bucket=self._service._bucket, Key=key
        )

    async def exists(self, key: str) -> bool:
        """Return True if the object key exists in MinIO."""
        try:
            self._service._client.head_object(
                Bucket=self._service._bucket, Key=key
            )
            return True
        except Exception:
            return False
