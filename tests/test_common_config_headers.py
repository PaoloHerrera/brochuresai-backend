from services.common.config import get_base_headers


def test_get_base_headers_uses_override(monkeypatch):
    # Asegurar que el override tiene prioridad sobre el valor por defecto
    monkeypatch.setattr(
        "services.common.config.settings.scraper_accept_language",
        "en-US,en;q=0.9",
        raising=False,
    )

    headers = get_base_headers("fr-FR,fr;q=0.8")
    assert headers["Accept-Language"] == "fr-FR,fr;q=0.8"


def test_get_base_headers_uses_default_when_none_or_empty(monkeypatch):
    # Si override es None o vacío, usar el valor de settings
    monkeypatch.setattr(
        "services.common.config.settings.scraper_accept_language",
        "es-ES,es;q=0.9",
        raising=False,
    )

    h_none = get_base_headers(None)
    h_empty = get_base_headers("")
    assert h_none["Accept-Language"] == "es-ES,es;q=0.9"
    assert h_empty["Accept-Language"] == "es-ES,es;q=0.9"


def test_get_base_headers_contains_expected_keys():
    headers = get_base_headers("en-US,en;q=0.9")
    for key in (
        "User-Agent",
        "Accept-Language",
        "Accept",
        "Connection",
        "Upgrade-Insecure-Requests",
    ):
        assert key in headers
    # User-Agent debe parecerse a un navegador moderno
    assert "Mozilla/5.0" in headers["User-Agent"]
