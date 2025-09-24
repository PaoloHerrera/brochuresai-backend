from config import settings
from services.pdf.html_utils import inline_print_css

async def render_pdf(app, html: str) -> bytes:
    """Renderiza HTML a PDF usando el navegador Playwright global de la app."""
    browser = app.state.browser
    async with app.state.pdf_sema:
        context = await browser.new_context(
            color_scheme="light",
            java_script_enabled=not settings.playwright_disable_js,
            offline=True,
            viewport={"width": 1200, "height": 1600},
        )

        timeout_ms = settings.playwright_pdf_timeout_ms
        try:
            context.set_default_timeout(timeout_ms)
        except Exception:
            pass

        page = await context.new_page()
        await page.emulate_media(media="print")

        # Inyectar CSS de impresión inline (sin depender de JS)
        html = inline_print_css(html)

        await page.set_content(html, wait_until="domcontentloaded", timeout=timeout_ms)

        try:
            import asyncio as _asyncio
            pdf_coro = page.pdf(
                format="A4",
                print_background=True,
                scale=1.0,
                margin={"top": "1cm", "bottom": "1cm", "left": "1cm", "right": "1cm"},
            )
            pdf_bytes = await _asyncio.wait_for(pdf_coro, timeout=(max(1, int(timeout_ms)) / 1000.0))
            return pdf_bytes
        finally:
            try:
                await context.close()
            except Exception:
                pass