"""Unit tests for StorageService — T-020 coverage gap fill.

All tests use mocked boto3 client. No Docker required.
"""
from unittest.mock import MagicMock


def test_upload_file_calls_upload_fileobj():
    """upload_file calls client.upload_fileobj with correct bucket and full key."""
    from app.services.storage import StorageService

    mock_client = MagicMock()
    svc = StorageService(client=mock_client, bucket="test-bucket")

    key = svc.upload_file(tenant="t1", key="doc-001.docx", data=b"hello bytes")

    assert key == "t1/doc-001.docx"
    mock_client.upload_fileobj.assert_called_once()
    call_args = mock_client.upload_fileobj.call_args
    # Second arg is bucket, third is full_key
    assert call_args[0][1] == "test-bucket"
    assert call_args[0][2] == "t1/doc-001.docx"


def test_upload_file_wraps_bytes_in_bytesio():
    """upload_file wraps the raw bytes in BytesIO before passing to client."""
    from app.services.storage import StorageService

    mock_client = MagicMock()
    svc = StorageService(client=mock_client, bucket="test-bucket")
    svc.upload_file(tenant="t1", key="file.docx", data=b"content")

    call_args = mock_client.upload_fileobj.call_args
    fileobj = call_args[0][0]
    assert hasattr(fileobj, "read"), "First arg must be a file-like object"
    assert fileobj.read() == b"content"


def test_get_file_returns_bytes():
    """get_file returns bytes downloaded from storage."""
    from app.services.storage import StorageService

    expected_bytes = b"file content here"

    def fake_download(bucket, key, buf):
        buf.write(expected_bytes)

    mock_client = MagicMock()
    mock_client.download_fileobj.side_effect = fake_download

    svc = StorageService(client=mock_client, bucket="test-bucket")
    result = svc.get_file(tenant="t1", key="doc-001.docx")

    assert result == expected_bytes


def test_get_file_uses_tenant_prefixed_key():
    """get_file constructs full key as tenant/key."""
    from app.services.storage import StorageService

    mock_client = MagicMock()
    mock_client.download_fileobj.side_effect = lambda b, k, buf: None

    svc = StorageService(client=mock_client, bucket="bucket")
    svc.get_file(tenant="t1", key="doc.docx")

    call_args = mock_client.download_fileobj.call_args
    assert call_args[0][1] == "t1/doc.docx"


def test_upload_returns_full_key_string():
    """upload_file returns the full storage key string."""
    from app.services.storage import StorageService

    mock_client = MagicMock()
    svc = StorageService(client=mock_client, bucket="bucket")
    key = svc.upload_file(tenant="acme-corp", key="report.xlsx", data=b"x")
    assert key == "acme-corp/report.xlsx"


def test_create_storage_service_builds_from_settings(monkeypatch):
    """create_storage_service builds a StorageService using Settings."""
    import os
    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://u:p@localhost/db")
    os.environ.setdefault("JWT_SECRET", "test-secret-32-bytes-minimum-here!")
    os.environ.setdefault("MINIO_ENDPOINT", "http://minio:9000")
    os.environ.setdefault("MINIO_BUCKET", "ra-documents")
    os.environ.setdefault("MINIO_USER", "minioadmin")
    os.environ.setdefault("MINIO_PASSWORD", "minioadmin")
    os.environ.setdefault("OLLAMA_ENDPOINT", "http://ollama:11434")
    os.environ.setdefault("OLLAMA_MODEL", "llama3.1:8b")
    os.environ.setdefault("CLOUD_SYNC_ENDPOINT", "https://sync.example.com")
    os.environ.setdefault("CORS_ORIGINS", "http://localhost:8080")

    from unittest.mock import patch, MagicMock
    mock_boto3 = MagicMock()

    with patch("app.services.storage.boto3", mock_boto3):
        from app.services.storage import create_storage_service
        svc = create_storage_service()

    assert svc is not None
    mock_boto3.client.assert_called_once()
    call_kwargs = mock_boto3.client.call_args[1]
    assert call_kwargs["endpoint_url"] == "http://minio:9000"
