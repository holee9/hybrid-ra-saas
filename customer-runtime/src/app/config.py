"""Application configuration via pydantic-settings."""
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str

    # JWT
    jwt_secret: str
    jwt_ttl_min: int = 60

    # MinIO
    minio_endpoint: str
    minio_bucket: str
    minio_user: str
    minio_password: str

    # Ollama
    ollama_endpoint: str
    ollama_model: str

    # Cloud Sync
    cloud_sync_endpoint: str

    # Rate limiting and workers
    rate_limit_per_min: int = 100
    api_workers: int = 2

    # CORS
    cors_origins: str

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_min_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("jwt_secret must be at least 32 characters")
        return v

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",")]
