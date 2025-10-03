from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

"""
This settings module uses Pydantic to manage configuration settings.
It loads environment variables from a .env file and provides a structured way to access them.
"""


class Settings(BaseSettings):
    # App environment flags
    dev_mode: bool = Field(default=True, alias="DEV_MODE")
    file_logging: bool = Field(default=False, alias="FILE_LOGGING")

    openai_api_key: Optional[str] = Field(default=None, alias="OPENAI_API_KEY")
    max_brochures_per_user: int = Field(default=3, alias="MAX_BROCHURES_PER_USER")
    # Rate limiting
    rate_limit_max_per_minute: int = Field(default=10, alias="RATE_LIMIT_MAX_PER_MINUTE")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")
    # Trust proxy headers (X-Forwarded-For / X-Real-IP) only if behind a trusted proxy
    trust_proxy: bool = Field(default=False, alias="TRUST_PROXY")
    # Playwright settings
    playwright_max_concurrency: int = Field(default=2, alias="PLAYWRIGHT_MAX_CONCURRENCY")
    playwright_pdf_timeout_ms: int = Field(default=30000, alias="PLAYWRIGHT_PDF_TIMEOUT_MS")
    playwright_disable_js: bool = Field(default=True, alias="PLAYWRIGHT_DISABLE_JS")
    scraper_accept_language: str = Field(default="en-US,en;q=0.9", alias="SCRAPER_ACCEPT_LANGUAGE")

    # Cache compression settings
    cache_compress: bool = Field(default=False, alias="CACHE_COMPRESS")
    cache_compression_algo: str = Field(default="gzip", alias="CACHE_COMPRESSION_ALGO")
    cache_compress_min_bytes: int = Field(default=10240, alias="CACHE_COMPRESS_MIN_BYTES")

    # Scraper/logging verbosity flag
    scraper_log_verbose: bool = Field(default=False, alias="SCRAPER_LOG_VERBOSE")

    # Pydantic v2 config dict: read .env and ignore unknown extras
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
