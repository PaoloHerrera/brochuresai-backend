from services.pdf.html_utils import ensure_html_document, sanitize_html_for_pdf


def test_ensure_wraps_plain_text_document():
    raw = "Hello <b>World</b>"
    out = ensure_html_document(raw)
    assert out.lower().startswith("<!doctype html><html")
    assert "Hello &lt;b&gt;World&lt;/b&gt;" in out


def test_keep_existing_html_document():
    html = "<html><body><p>ok</p></body></html>"
    out = ensure_html_document(html)
    # Si ya es documento HTML, se devuelve tal cual
    assert "<p>ok</p>" in out


def test_sanitize_removes_dangerous_tags_and_attrs():
    html = (
        "<html><body>"
        "<script>alert(1)</script>"
        "<iframe src='http://evil'></iframe>"
        "<object data='x'></object>"
        "<embed src='y'></embed>"
        "<form action='/'><input /></form>"
        "<a href='javascript:alert(1)' onclick='do()'>Link</a>"
        "<img src='data:image/png;base64,AAAA' onload='x()'/>"
        "</body></html>"
    )
    out = sanitize_html_for_pdf(html)
    lower = out.lower()
    # Tags peligrosos eliminados
    for tag in ("script", "iframe", "object", "embed", "form"):
        assert f"<{tag}" not in lower
    # Atributos on* eliminados
    assert "onclick=" not in lower and "onload=" not in lower
    # href/src con esquemas inseguros eliminados
    assert 'href="javascript:' not in lower
    assert 'src="data:' not in lower


def test_sanitize_removes_external_styles_imports_and_fontface_and_neutralizes_url_css():
    html = (
        "<html><head>"
        "<link rel='stylesheet' href='https://cdn.example/styles.css'>"
        "<style>\n"
        "@import url(https://cdn.example/file.css);\n"
        "@font-face { font-family: X; src: url(font.woff2); }\n"
        ".x { background: url(https://example.com/img.png); }\n"
        "</style>"
        "</head><body><p>ok</p></body></html>"
    )
    out = sanitize_html_for_pdf(html)
    lower = out.lower()
    # link rel=stylesheet eliminado
    assert "<link" not in lower or 'rel="stylesheet"' not in lower
    # @import y @font-face eliminados
    assert "@import" not in lower
    assert "@font-face" not in lower
    # url(...) neutralizado a 'none'
    assert "url(" not in lower
    assert "background:none" in lower or "none" in lower


def test_sanitize_wraps_document_if_missing_html_tag():
    body_only = "<body><style>.x{background:url(a.png)}</style><script>1</script></body>"
    out = sanitize_html_for_pdf(body_only)
    lower = out.lower()
    # Debe asegurar documento HTML y sanitizar
    assert "<html" in lower
    assert "<script" not in lower
    assert "url(" not in lower
