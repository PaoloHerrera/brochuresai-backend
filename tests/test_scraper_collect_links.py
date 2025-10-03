from bs4 import BeautifulSoup

from services.scraper import _collect_links


def test_collect_links_resolves_relative_and_filters_non_http_and_private():
    html = """
    <html><body>
        <a href="about">About</a>
        <a href="/careers/">Careers</a>
        <a href="http://example.com/contact#section">Contact</a>
        <a href="mailto:test@example.com">Email</a>
        <a href="javascript:void(0)">JS</a>
        <a href="http://127.0.0.1/admin">Local</a>
        <a href="https://twitter.com/companyx">Twitter</a>
    </body></html>
    """
    soup = BeautifulSoup(html, "html.parser")
    base_url = "http://example.com"
    base_host = "example.com"

    result = _collect_links(soup, base_url, base_host)

    # Relative links should be resolved to absolute
    assert "http://example.com/about" in result
    assert "http://example.com/careers/" in result

    # Non-http schemes should be filtered out
    assert not any(u.startswith("mailto:") for u in result)
    assert not any(u.startswith("javascript:") for u in result)

    # Private/loopback hosts should be filtered out
    assert not any("127.0.0.1" in u for u in result)

    # Social links may be present; filtering occurs later
    assert any("twitter.com" in u for u in result)


def test_collect_links_collects_all_without_limit():
    # Generate many relative links; all should be collected now
    links_html = "".join(f'<a href="page{i}">Page {i}</a>' for i in range(1, 50))
    soup = BeautifulSoup(f"<html><body>{links_html}</body></html>", "html.parser")

    base_url = "http://example.com"
    base_host = "example.com"
    result = _collect_links(soup, base_url, base_host)
    # We expect all 49 generated links to be present (no cap)
    assert len(result) == 49
