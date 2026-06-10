"""Application configuration via pydantic-settings.

# @MX:ANCHOR: [AUTO] Public Settings contract — all crawler config flows through here.
# @MX:REASON: Called by main.py lifespan, database.py init_engine, and future crawler tasks.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # @MX:NOTE: [AUTO] extra="ignore" allows .env files with additional keys (e.g., CI secrets).
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str

    # Crawler source enable flags (REQ-CRAWLER-001)
    crawler_fda_enabled: bool = True
    crawler_mfds_enabled: bool = True
    crawler_eu_mdr_enabled: bool = True

    # Request timeout in seconds
    request_timeout: float = 30.0

    # Retry configuration (REQ-CRAWLER-005): 3 retries, exponential backoff 2s * 2^n
    retry_count: int = 3
    retry_backoff_initial: float = 2.0
    retry_backoff_multiplier: float = 2.0

    # Rate limiting: 1 request/second per source (REQ-CRAWLER-009)
    # @MX:NOTE: [AUTO] Per-source limit — each source has its own token bucket in P1.
    rate_limit_per_source: float = 1.0

    # Blob storage (Azure Blob — S3-compatible via boto3)
    blob_account_name: str
    blob_container_name: str
    blob_account_key: str

    # Application Insights for structured log shipping (REQ-CRAWLER-010)
    appinsights_connection_string: str
