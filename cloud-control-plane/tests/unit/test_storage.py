"""Unit tests for Blob storage service (T-014, REQ-001/002).

Uses a mock boto3 client — no real Azure/S3 connection.
"""
from datetime import date
from unittest.mock import MagicMock

import pytest


def _make_mock_s3_client() -> MagicMock:
    client = MagicMock()
    client.put_object = MagicMock(return_value={"ResponseMetadata": {"HTTPStatusCode": 200}})
    return client


@pytest.mark.asyncio
async def test_upload_returns_blob_path():
    """upload_document returns the blob path matching the naming convention."""
    from app.services.storage import StorageService

    mock_client = _make_mock_s3_client()
    svc = StorageService(s3_client=mock_client, bucket="test-container")

    blob_path = await svc.upload_document(
        source="fda",
        filename="guidance.pdf",
        content=b"PDF bytes",
        fetch_date=date(2026, 6, 10),
    )

    assert blob_path == "regulatory-docs/fda/2026-06-10/guidance.pdf"


@pytest.mark.asyncio
async def test_upload_blob_path_convention():
    """Path must follow regulatory-docs/{source}/{YYYY-MM-DD}/{filename} (REQ-002)."""
    from app.services.storage import StorageService

    mock_client = _make_mock_s3_client()
    svc = StorageService(s3_client=mock_client, bucket="test-container")

    cases = [
        ("fda", "doc.pdf", date(2026, 1, 5), "regulatory-docs/fda/2026-01-05/doc.pdf"),
        ("mfds", "file.pdf", date(2025, 12, 31), "regulatory-docs/mfds/2025-12-31/file.pdf"),
        ("eu-mdr", "mdr.pdf", date(2026, 6, 10), "regulatory-docs/eu-mdr/2026-06-10/mdr.pdf"),
    ]

    for source, filename, fetch_date, expected_path in cases:
        result = await svc.upload_document(
            source=source,
            filename=filename,
            content=b"bytes",
            fetch_date=fetch_date,
        )
        assert result == expected_path, f"Expected {expected_path!r}, got {result!r}"


@pytest.mark.asyncio
async def test_upload_calls_put_object_with_correct_args():
    """put_object is called with correct key and body."""
    from app.services.storage import StorageService

    mock_client = _make_mock_s3_client()
    svc = StorageService(s3_client=mock_client, bucket="docs-container")
    content = b"raw PDF"

    await svc.upload_document(
        source="fda",
        filename="guidance.pdf",
        content=content,
        fetch_date=date(2026, 6, 10),
    )

    mock_client.put_object.assert_called_once()
    call_kwargs = mock_client.put_object.call_args[1]

    assert call_kwargs["Key"] == "regulatory-docs/fda/2026-06-10/guidance.pdf"
    assert call_kwargs["Body"] == content
    assert call_kwargs["Bucket"] == "docs-container"


@pytest.mark.asyncio
async def test_upload_does_not_write_to_postgres():
    """StorageService must only call s3_client — no DB writes (FR-210)."""
    from app.services.storage import StorageService

    mock_client = _make_mock_s3_client()
    svc = StorageService(s3_client=mock_client, bucket="test")

    # If StorageService held a DB session we'd detect it here;
    # verify the object has no session attribute.
    assert not hasattr(svc, "_session"), (
        "StorageService must not hold a DB session — raw bytes never go to PostgreSQL"
    )

    await svc.upload_document(
        source="fda",
        filename="doc.pdf",
        content=b"bytes",
        fetch_date=date(2026, 6, 10),
    )

    # Only s3_client.put_object should have been called
    mock_client.put_object.assert_called_once()
