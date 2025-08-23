from fastapi import APIRouter, HTTPException, Request
from api.v1.schemas import CreateBrochureRequest, DownloadBrochureRequest
from services.openai.openai_client import OpenAIClient
from services.scraper import Scraper
from services.redis.redis_client import redis_client

import time
import json

import hashlib
from fastapi.responses import Response
from html import escape as html_escape

router = APIRouter()

@router.post("/create_brochure")
async def create_brochure(request: Request, body: CreateBrochureRequest):

    try:
        
        url = str(body.url)
        company_name = str(body.company_name or "Company")

        brochure_type = str(body.brochure_type) or "professional"
        language = str(body.language) or "English"

        brochure = await OpenAIClient(Scraper).create_brochure(company_name, url, language, brochure_type)
        
        ## Cache the brochure in Redis
        user_ip = get_client_ip(request)
        cache_key = generate_cache_key(user_ip, body.model_dump(mode="json"))

        # Set data in Redis for 1 hour
        cache_data = {
            "brochure": brochure,
            "data": body.model_dump(mode="json"),
            "user_ip": user_ip,
            "created_at": time.time()
        }

        redis_client.set(
            cache_key,
            json.dumps(cache_data),
            ex=3600
        )

        return {
            "success": True,
            "brochure": brochure,
            "cache_key": cache_key,
            "expires_in": 3600
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def get_client_ip(request: Request) -> str:
    x_forwarded_for = request.headers.get("X-Forwarded-For")

    print(f"X-Forwarded-For: {x_forwarded_for}")
    print(f"Request client host: {request.client.host}")


    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]
    else:
        ip = request.client.host
    return ip

def generate_cache_key(user_ip: str, data_json: dict) -> str:
    """Generate a cache key for Redis based on the user's IP and the data to be cached."""
    content = f"{user_ip}:{json.dumps(data_json, sort_keys=True)}"
    return hashlib.sha256(content.encode()).hexdigest()


@router.post("/download_brochure")
async def download_brochure(body: DownloadBrochureRequest):
    cache_key = body.cache_key
    data = redis_client.get(cache_key)
    if data:
        data = json.loads(data)
        ttl = redis_client.ttl(cache_key)
        expires_in = ttl if ttl is not None and ttl >= 0 else None
        return {
            "success": True,
            "brochure": data["brochure"],
            "cache_key": cache_key,
            "expires_in": expires_in
        }
    else:
        raise HTTPException(status_code=404, detail="Cache key not found")


@router.post("/download_brochure_pdf")
async def download_brochure_pdf(request: Request, body: DownloadBrochureRequest):
    cache_key = body.cache_key
    data = redis_client.get(cache_key)
    if not data:
        raise HTTPException(status_code=404, detail="Cache key not found")

    payload = json.loads(data)
    brochure_html = payload.get("brochure")
    company_name = payload.get("data", {}).get("company_name") or "brochure"

    if not brochure_html or not str(brochure_html).strip():
        raise HTTPException(status_code=400, detail="No brochure content available for this key")

    # Asegurar HTML básico si viene texto plano
    html = brochure_html
    if "<html" not in html.lower():
        html = f"<!doctype html><html><head><meta charset='utf-8'><title>Brochure</title><style>body{{font-family:Arial,Helvetica,sans-serif;line-height:1.5;font-size:14px;padding:24px;}} h1,h2,h3{{margin:0.6em 0;}} p{{margin:0.4em 0;}} pre{{white-space:pre-wrap;}}</style></head><body><pre>{html_escape(str(brochure_html))}</pre></body></html>"

    # Diagnóstico: tamaños
    try:
        print(f"[PDF] HTML length: {len(html)}")
    except Exception:
        pass

    # Generar PDF con Playwright reutilizando el browser global
    browser = request.app.state.browser
    # Forzar esquema de color oscuro si la página usa prefers-color-scheme
    context = await browser.new_context(color_scheme="dark")
    page = await context.new_page()
    # Usar estilos de 'pantalla' para respetar fondos/temas y no los de impresión
    await page.emulate_media(media="screen")
    # Cargar y esperar a que terminen las solicitudes de recursos (CSS/imagenes)
    await page.set_content(html, wait_until="networkidle")
    # Asegurar que los colores de fondo no sean ajustados durante impresión
    try:
        await page.add_style_tag(content="*{-webkit-print-color-adjust:exact;print-color-adjust:exact;forced-color-adjust:none;} html,body{-webkit-print-color-adjust:exact;print-color-adjust:exact;forced-color-adjust:none;}")
    except Exception:
        pass
    # Sin márgenes y respetando @page CSS del HTML
    pdf_bytes = await page.pdf(print_background=True, prefer_css_page_size=True, margin={"top":"0","bottom":"0","left":"0","right":"0"})
    await context.close()

    try:
        print(f"[PDF] Bytes length: {len(pdf_bytes) if pdf_bytes else 0}")
    except Exception:
        pass

    headers = {
        "Content-Disposition": f"attachment; filename={company_name}_brochure.pdf",
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
