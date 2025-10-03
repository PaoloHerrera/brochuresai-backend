from pydantic_settings import SettingsConfigDict

from config import Settings


def test_env_aliases_and_parsing(monkeypatch):
    # OpenAI API
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")

    # Brochures quota
    monkeypatch.setenv("MAX_BROCHURES_PER_USER", "5")

    # App environment flags
    monkeypatch.setenv("DEV_MODE", "false")
    monkeypatch.setenv("FILE_LOGGING", "true")
    monkeypatch.setenv("TRUST_PROXY", "true")

    # Rate limiting
    monkeypatch.setenv("RATE_LIMIT_MAX_PER_MINUTE", "15")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "120")

    # Playwright settings
    monkeypatch.setenv("PLAYWRIGHT_MAX_CONCURRENCY", "4")
    monkeypatch.setenv("PLAYWRIGHT_PDF_TIMEOUT_MS", "45000")
    monkeypatch.setenv("PLAYWRIGHT_DISABLE_JS", "false")

    # Scraper headers
    monkeypatch.setenv("SCRAPER_ACCEPT_LANGUAGE", "es-ES,es;q=0.9")

    # Cache compression
    monkeypatch.setenv("CACHE_COMPRESS", "true")
    monkeypatch.setenv("CACHE_COMPRESSION_ALGO", "gzip")
    monkeypatch.setenv("CACHE_COMPRESS_MIN_BYTES", "2048")

    s = Settings()

    assert s.openai_api_key == "sk-test-123"
    assert s.max_brochures_per_user == 5

    # Booleans parsed correctly
    assert s.dev_mode is False
    assert s.file_logging is True
    assert s.trust_proxy is True

    # Rate limiting values
    assert s.rate_limit_max_per_minute == 15
    assert s.rate_limit_window_seconds == 120

    # Playwright values
    assert s.playwright_max_concurrency == 4
    assert s.playwright_pdf_timeout_ms == 45000
    assert s.playwright_disable_js is False

    # Scraper header default/override
    assert s.scraper_accept_language.startswith("es-ES")

    # Cache compression settings
    assert s.cache_compress is True
    assert s.cache_compression_algo == "gzip"
    assert s.cache_compress_min_bytes == 2048


class EphemeralSettings(Settings):
    # Disable reading .env to make defaults test stable
    model_config = SettingsConfigDict(env_file=None)


def test_defaults_when_env_missing(monkeypatch):
    # Ensure env vars are absent to validate defaults
    for key in [
        "OPENAI_API_KEY",
        "MAX_BROCHURES_PER_USER",
        "DEV_MODE",
        "FILE_LOGGING",
        "RATE_LIMIT_MAX_PER_MINUTE",
        "RATE_LIMIT_WINDOW_SECONDS",
        "TRUST_PROXY",
        "PLAYWRIGHT_MAX_CONCURRENCY",
        "PLAYWRIGHT_PDF_TIMEOUT_MS",
        "PLAYWRIGHT_DISABLE_JS",
        "SCRAPER_ACCEPT_LANGUAGE",
        "CACHE_COMPRESS",
        "CACHE_COMPRESSION_ALGO",
        "CACHE_COMPRESS_MIN_BYTES",
    ]:
        monkeypatch.delenv(key, raising=False)

    s = EphemeralSettings()

    assert s.max_brochures_per_user == 3
    assert s.dev_mode is True
    assert s.file_logging is False
    assert s.rate_limit_max_per_minute == 10
    assert s.rate_limit_window_seconds == 60
    assert s.trust_proxy is False
    assert s.playwright_max_concurrency == 2
    assert s.playwright_pdf_timeout_ms == 30000
    assert s.playwright_disable_js is True
    assert s.scraper_accept_language == "en-US,en;q=0.9"
    assert s.cache_compress is False
    assert s.cache_compression_algo == "gzip"
    assert s.cache_compress_min_bytes == 10240
