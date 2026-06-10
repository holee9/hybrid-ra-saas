"""Blob storage service for raw regulatory documents (REQ-001, REQ-002).

Uploads raw bytes to Azure Blob (S3-compatible) at path:
  regulatory-docs/{source}/{YYYY-MM-DD}/{filename}

Raw bytes are NEVER written to PostgreSQL (FR-210 / REQ-CRAWLER-004).

# @MX:NOTE: [AUTO] Blob path contract: regulatory-docs/{source}/{YYYY-MM-DD}/{filename}.
#           source ∈ {fda, mfds, eu-mdr}. Changing this convention breaks AC-001 queries.
"""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any


class StorageService:
    """Upload documents to S3-compatible Blob storage.

    # @MX:ANCHOR: [AUTO] Public upload contract (REQ-002, AC-001).
    # @MX:REASON: Called by orchestrator per new document; also test fixtures.
    """

    def __init__(self, s3_client: Any, bucket: str) -> None:
        self._s3_client = s3_client
        self._bucket = bucket

    async def upload_document(
        self,
        source: str,
        filename: str,
        content: bytes,
        fetch_date: date,
    ) -> str:
        """Upload raw bytes to Blob and return the storage path.

        Path format: regulatory-docs/{source}/{YYYY-MM-DD}/{filename}
        Returns the blob_path string for metadata row insertion.
        """
        date_str = fetch_date.strftime("%Y-%m-%d")
        blob_path = f"regulatory-docs/{source}/{date_str}/{filename}"

        # Wrap synchronous boto3 call in a thread to avoid blocking the event loop
        await asyncio.to_thread(
            self._s3_client.put_object,
            Bucket=self._bucket,
            Key=blob_path,
            Body=content,
        )

        return blob_path


def make_storage_service(settings: Any) -> StorageService:
    """Factory: build StorageService from application Settings."""
    import boto3

    s3_client = boto3.client(
        "s3",
        endpoint_url=(f"https://{settings.blob_account_name}.blob.core.windows.net"),
        aws_access_key_id=settings.blob_account_name,
        aws_secret_access_key=settings.blob_account_key,
    )
    return StorageService(s3_client=s3_client, bucket=settings.blob_container_name)
