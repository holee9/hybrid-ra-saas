"""Application configuration via pydantic-settings.

# @MX:ANCHOR: [AUTO] Public Settings contract — all crawler config flows through here.
# @MX:REASON: Called by main.py lifespan, database.py init_engine, and future crawler tasks.
"""

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # @MX:NOTE: [AUTO] extra="ignore" allows .env files with additional keys (e.g., CI secrets).
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str

    @field_validator("database_url")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        # Azure Key Vault stores plain postgresql:// — asyncpg requires postgresql+asyncpg://
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        if v.startswith("postgres://"):
            return v.replace("postgres://", "postgresql+asyncpg://", 1)
        return v

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

    # Crawler source URLs (configurable to survive HTML structure changes)
    # @MX:NOTE: [AUTO] Default values point to live endpoints; override via env for testing.
    fda_listing_url: str = "https://www.fda.gov/safety/recalls-market-withdrawals-safety-alerts"
    fda_media_prefix: str = "/media/"
    mfds_listing_url: str = "https://www.mfds.go.kr/brd/m_218/list.do"
    mfds_doc_prefix: str = "/brd/"
    eu_mdr_listing_url: str = "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32017R0745"
    eu_mdr_doc_prefix: str = "/legal-content/"
