"""Application configuration via pydantic-settings."""
from typing import List
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        # Normalize driver: asyncpg requires postgresql+asyncpg:// scheme
        if v.startswith("postgresql://"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        # asyncpg uses ssl=require, not sslmode=require (psycopg2 syntax)
        v = v.replace("sslmode=require", "ssl=require")
        v = v.replace("sslmode=verify-full", "ssl=require")
        v = v.replace("sslmode=verify-ca", "ssl=require")
        v = v.replace("sslmode=disable", "ssl=False")
        return v

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

    # Regula SaaS API key (GAP-02: server-to-server auth)
    # Set to a strong random value; ra-med-bot sends this as X-Regula-API-Key header.
    regula_api_key: str = ""

    # Comma-separated tenant IDs allowed to use Regula API key auth (GAP-02).
    # Empty = all tenants permitted.
    regula_allowed_tenants: str = ""

    @property
    def regula_allowed_tenants_set(self) -> set[str]:
        return {t.strip() for t in self.regula_allowed_tenants.split(",") if t.strip()}

    # Regula SaaS webhook URL for outbound audit event push (GAP-06).
    # When set, POST /audit/webhook forwards events to this URL.
    regula_audit_webhook_url: str = ""

    # Regula SaaS webhook URL for IFU parse result push (GAP-07).
    # When set, a completed parse job pushes structured IFU data to Regula.
    regula_ifu_webhook_url: str = ""
