from config import settings

# OpenAI configuration
OPENAI_DEFAULT_MODEL = "gpt-5-mini"

# Scraper configuration
SCRAPER_DEFAULT_TIMEOUT = 10
# Concurrency cap for parallel page fetches during details scraping
SCRAPER_MAX_CONCURRENCY = 6

# Details aggregation budget to avoid excessive prompt payloads
DETAILS_MAX_CHARS = 30_000

# Logging verbosity for scraper/link processing
SCRAPER_LOG_VERBOSE = bool(getattr(settings, "scraper_log_verbose", False))


def get_base_headers(accept_language_override: str | None = None) -> dict:
    """Build base HTTP headers with optional Accept-Language override.

    If no override is provided, uses `settings.scraper_accept_language`.
    """
    accept_language = (
        accept_language_override if accept_language_override else settings.scraper_accept_language
    )

    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/123.0.0.0 Safari/537.36"
        ),
        "Accept-Language": accept_language,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
