"""StoragePort — unified storage abstraction protocol."""
from typing import Protocol, runtime_checkable


@runtime_checkable
class StoragePort(Protocol):
    """Abstract storage interface. Switch backend via STORAGE_BACKEND env var."""

    async def upload(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        """Upload data and return the stored key."""
        ...

    async def download(self, key: str) -> bytes:
        """Download data by key."""
        ...

    async def delete(self, key: str) -> None:
        """Delete object by key."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        ...
