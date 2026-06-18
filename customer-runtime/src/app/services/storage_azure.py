"""AzureBlobAdapter — StoragePort implementation backed by Azure Blob Storage.

Activate by setting STORAGE_BACKEND=azure in environment.
Requires azure-storage-blob package and AZURE_STORAGE_CONNECTION_STRING env var.
"""
from __future__ import annotations

import os


class AzureBlobAdapter:
    """Implements StoragePort using Azure Blob Storage."""

    def __init__(self) -> None:
        try:
            from azure.storage.blob.aio import BlobServiceClient  # type: ignore[import]
        except ImportError as exc:
            raise ImportError(
                "azure-storage-blob is required for AzureBlobAdapter. "
                "Install with: pip install azure-storage-blob"
            ) from exc

        connection_string = os.environ.get("AZURE_STORAGE_CONNECTION_STRING", "")
        self._container = os.environ.get("AZURE_STORAGE_CONTAINER", "documents")
        self._client = BlobServiceClient.from_connection_string(connection_string)

    async def upload(
        self, key: str, data: bytes, content_type: str = "application/octet-stream"
    ) -> str:
        """Upload bytes to Azure Blob and return the blob key."""
        async with self._client:
            container = self._client.get_container_client(self._container)
            blob = container.get_blob_client(key)
            await blob.upload_blob(data, overwrite=True, content_settings={"content_type": content_type})
        return key

    async def download(self, key: str) -> bytes:
        """Download blob bytes by key."""
        async with self._client:
            container = self._client.get_container_client(self._container)
            blob = container.get_blob_client(key)
            stream = await blob.download_blob()
            return await stream.readall()

    async def delete(self, key: str) -> None:
        """Delete blob by key."""
        async with self._client:
            container = self._client.get_container_client(self._container)
            blob = container.get_blob_client(key)
            await blob.delete_blob()

    async def exists(self, key: str) -> bool:
        """Return True if the blob exists."""
        async with self._client:
            container = self._client.get_container_client(self._container)
            blob = container.get_blob_client(key)
            return await blob.exists()
