from services.common.link_utils import (
    filter_social_media_links,
    is_http_url,
    is_irrelevant_link,
    is_private_ip,
    normalize_url,
)


def test_is_http_url_true_for_http_https():
    assert is_http_url("http://example.com")
    assert is_http_url("https://example.com/path")


def test_is_http_url_false_for_non_http():
    assert not is_http_url("mailto:foo@bar.com")
    assert not is_http_url("javascript:void(0)")
    assert not is_http_url("ftp://example.com/file")


def test_is_private_ip_detection():
    assert is_private_ip("127.0.0.1")
    assert is_private_ip("localhost")
    assert is_private_ip("192.168.1.10")
    assert is_private_ip("example.local")
    # Public IP should not be treated as private
    assert not is_private_ip("8.8.8.8")


def test_is_irrelevant_link_filters_common_assets_and_paths():
    base = "example.com"
    assert is_irrelevant_link("https://example.com/style.css", base)
    assert is_irrelevant_link("https://example.com/feed.xml", base)
    assert is_irrelevant_link("https://example.com/wp-admin", base)
    assert is_irrelevant_link("https://example.com/robots.txt", base)
    assert not is_irrelevant_link("https://example.com/about", base)


def test_normalize_url_removes_trailing_slash_and_fragment_and_lowercases():
    assert normalize_url("https://EXAMPLE.com/About/") == "https://example.com/about"
    assert normalize_url("https://example.com/about#team") == "https://example.com/about"


def test_filter_social_media_links_separates_and_deduplicates():
    company_domain = "example.com"
    links = [
        "https://example.com/about",
        "https://example.com/wp-admin",
        "https://example.com/style.css",
        "https://twitter.com/CompanyX",
        "https://www.linkedin.com/company/companyx/",
        "https://github.com/companyx",
        "https://example.com/about#team",
        "https://EXAMPLE.com/About/",
        "mailto:foo@bar.com",
    ]

    info_links, social_links = filter_social_media_links(links, company_domain)

    # Info links should include a single deduped about page
    assert len([u for u in info_links if "example.com/about" in u.lower()]) == 1

    # Social links should include the specific profiles
    assert any("twitter.com/" in u for u in social_links)
    assert any("linkedin.com/company/" in u for u in social_links)
    assert any("github.com/" in u for u in social_links)


def test_filter_internal_and_company_social_only():
    company_domain = "example.com"
    links = [
        # Internos relevantes
        "https://example.com/about",
        "https://sub.example.com/team",
        # Interno irrelevante
        "https://example.com/login",
        # Externo no social (debe descartarse)
        "https://other.com/about",
        # Sociales válidos (perfiles/canales)
        "https://twitter.com/ExampleCo",
        "https://github.com/companyx",
        # Sociales genéricos/invalidos (deben descartarse)
        "https://linkedin.com/feed",
        "https://facebook.com/pages/create",
        "https://instagram.com/",
        "https://x.com/intent/tweet",
    ]

    info_links, social_links = filter_social_media_links(links, company_domain)

    # Solo deben conservarse enlaces informativos internos (mismo dominio o subdominios)
    assert any("example.com/about" in u.lower() for u in info_links)
    assert any("sub.example.com/team" in u.lower() for u in info_links)
    assert not any("other.com" in u.lower() for u in info_links)

    # Enlaces internos irrelevantes como /login deben ser excluidos
    assert not any("example.com/login" in u.lower() for u in info_links)

    # Sociales válidos deben incluirse; genéricos o inválidos deben excluirse
    assert any("twitter.com/" in u for u in social_links)
    assert any("github.com/" in u for u in social_links)
    assert not any("linkedin.com/feed" in u for u in social_links)
    assert not any("facebook.com/pages/create" in u for u in social_links)
    assert not any(u.rstrip("/").endswith("instagram.com") for u in social_links)
    assert not any("x.com/intent" in u for u in social_links)
