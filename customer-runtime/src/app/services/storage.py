"""Storage service — wraps boto3 S3-compatible client."""
from typing import Any


class StorageService:
    """Uploads and retrieves files from MinIO/S3-compatible storage."""

    def __init__(self, client: Any, bucket: str) -> None:
        self._client = client
        self._bucket = bucket

    def upload_file(self, tenant: str, key: str, data: bytes) -> str:
        """Upload bytes to storage, return the full object key."""
        import io

        full_key = f"{tenant}/{key}"
        self._client.upload_fileobj(
            io.BytesIO(data),
            self._bucket,
            full_key,
        )
        return full_key

    def get_file(self, tenant: str, key: str) -> bytes:
        """Retrieve file bytes from storage."""
        import io

        full_key = f"{tenant}/{key}"
        buf = io.BytesIO()
        self._client.download_fileobj(self._bucket, full_key, buf)
        return buf.getvalue()


def create_storage_service() -> StorageService:
    """Create a StorageService from app settings."""
    import boto3
    from app.config import Settings

    settings = Settings()
    client = boto3.client(
        "s3",
        endpoint_url=settings.minio_endpoint,
        aws_access_key_id=settings.minio_user,
        aws_secret_access_key=settings.minio_password,
    )
    return StorageService(client=client, bucket=settings.minio_bucket)
