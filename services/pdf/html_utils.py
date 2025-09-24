import re
from html import escape as html_escape
from bs4 import BeautifulSoup

# CSS mínimo para impresión en PDF (A4 con margen) — sencillo y estable
PRINT_CSS = (
    """
    @page { size: A4; margin: 1cm; }

    @media print {
      html, body { height: auto !important; }
      body { margin: 0 !important; }

      /* Intentar mantener las secciones completas cuando sea posible */
      section, .section { break-inside: avoid !important; page-break-inside: avoid !important; display: block !important; }
      footer, .footer { break-inside: avoid !important; page-break-inside: avoid !important; }

      /* Evitar cortes feos en imágenes y figuras */
      img, figure { break-inside: avoid; page-break-inside: avoid; }

      /* Neutraliza page-breaks forzados del contenido */
      .page-break { break-before: auto !important; page-break-before: auto !important; break-after: auto !important; page-break-after: auto !important; }
    }
    """
)


def ensure_html_document(html: str) -> str:
    try:
        lower = (html or "").lower()
        if "<html" in lower:
            return html
        # Envolver contenido plano en documento mínimo
        return (
            "<!doctype html><html><head><meta charset='utf-8'><title>Brochure</title>"
            "<style>body{font-family:Arial,Helvetica,sans-serif;line-height:1.5;font-size:14px;padding:24px;}"
            "h1,h2,h3{margin:0.6em 0;} p{margin:0.4em 0;} pre{white-space:pre-wrap;}</style>"
            "</head><body><pre>" + html_escape(html) + "</pre></body></html>"
        )
    except Exception:
        return html


def inline_print_css(html: str) -> str:
    """Inyecta PRINT_CSS al final del <head> o crea uno simple si no existe."""
    try:
        html = ensure_html_document(html)
        _lower = html.lower()
        if "<head" in _lower:
            return re.sub(r"(?i)</head>", f"<style>{PRINT_CSS}</style></head>", html, count=1)
        elif "<html" in _lower:
            return re.sub(
                "(?i)<html([^>]*)>",
                r"<html\\1><head><meta charset='utf-8'><style>" + PRINT_CSS + "</style></head>",
                html,
                count=1,
            )
        # Fallback: documento mínimo
        return f"<!doctype html><html><head><meta charset='utf-8'><style>{PRINT_CSS}</style></head><body>{html}</body></html>"
    except Exception:
        return f"<!doctype html><html><head><meta charset='utf-8'><style>{PRINT_CSS}</style></head><body>{html}</body></html>"


def sanitize_html_for_pdf(html: str) -> str:
    """Elimina recursos externos y reglas problemáticas para impresión offline."""
    try:
        html = ensure_html_document(html)
        # Eliminar hojas de estilo externas y @import
        html = re.sub(r"<link[^>]+rel=[\"']?stylesheet[\"']?[^>]*>", "", html, flags=re.I)
        html = re.sub(r"@import\s+url\([^\)]+\)\s*;?", "", html, flags=re.I)
        # Eliminar bloques @font-face
        html = re.sub(r"@font-face\s*\{[^}]*\}", "", html, flags=re.I | re.S)
        # Neutralizar url(...) en CSS inline
        html = re.sub(r"url\([^)]+\)", "none", html, flags=re.I)
        return html
    except Exception:
        return html

__all__ = [
    "PRINT_CSS",
    "ensure_html_document",
    "inline_print_css",
    "sanitize_html_for_pdf",
]