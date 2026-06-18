"""Storage backend factory — returns the appropriate StoragePort adapter.

# @MX:NOTE: [AUTO] StoragePort — unified interface. Switch backend via STORAGE_BACKEND env var.
"""
from app.core.storage import StoragePort


def get_storage_backend() -> StoragePort:
    """Return MinioAdapter when STORAGE_BACKEND=minio, else MinioAdapter (default).

    Both adapters wrap the existing StorageService; no existing callers are broken.
    """
    from app.config import Settings

    settings = Settings()
    backend = getattr(settings, "storage_backend", "minio")

    if backend == "azure":
        from app.services.storage_azure import AzureBlobAdapter

        return AzureBlobAdapter()
    else:
        from app.services.storage_minio import MinioAdapter

        return MinioAdapter()
