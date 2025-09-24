from fastapi import APIRouter, HTTPException, Request
from api.v1.schemas import CreateBrochureRequest, DownloadBrochureRequest
from services.openai.openai_client import OpenAIClient
from services.scraper import Scraper
from fastapi.responses import Response

from services.pdf.renderer import render_pdf
from services.brochures.cache import (
    generate_cache_key as gen_cache_key_service,
    store_brochure,
    get_brochure_payload,
)

from .deps import (
    MAX_BROCHURES_PER_USER,
    ensure_user,
    increment_brochures,
    get_client_ip,
    get_conn,
    reset_brochures_if_new_day,
    set_full_language,
)
from services.pdf.html_utils import sanitize_html_for_pdf

router = APIRouter()

@router.post("/create_brochure")
async def create_brochure(request: Request, body: CreateBrochureRequest):
    try:
        url = str(body.url)
        company_name = str(body.company_name or "Company")
        brochure_type = str(body.brochure_type) or "professional"
        language = set_full_language(body.language)

        # Identify or create user in the same call using anon_id or IP
        user_ip = get_client_ip(request)
        user = ensure_user(user_ip, body.anon_id)

        # Reset diario por fecha para consistencia
        conn = get_conn()
        try:
            user = reset_brochures_if_new_day(conn, user)
        finally:
            conn.close()

        used = int(user.get("brochures_count", 0))
        if used >= MAX_BROCHURES_PER_USER:
            raise HTTPException(status_code=429, detail="Brochure quota exceeded for this user")

        brochure = await OpenAIClient(Scraper).create_brochure(company_name, url, language, brochure_type)
        if isinstance(brochure, str) and brochure.startswith("Error:"):
            msg_lower = brochure.lower()
            if "missing openai api key" in msg_lower:
                # Falta de configuración: 503 Service Unavailable
                raise HTTPException(status_code=503, detail="Service unavailable")
            else:
                # Error del proveedor o de procesamiento: 502 Bad Gateway
                raise HTTPException(status_code=502, detail="Upstream provider error")
        # Si no hay error, continuar flujo normal
        
        # Cache brochure original en Redis por 1 hora
        cache_key = gen_cache_key_service(user_ip, body.model_dump(mode="json"))
        store_brochure(cache_key, brochure, body.model_dump(mode="json"), user_ip, ttl_seconds=3600)

        # Update usage count after successful generation
        increment_brochures(user["anon_id"])
        remaining_after = max(0, MAX_BROCHURES_PER_USER - (used + 1))

        return {
            "success": True,
            "brochure": brochure,
            "cache_key": cache_key,
            "expires_in": 3600,
            "anon_id": user["anon_id"],
            "brochures_used": used + 1,
            "brochures_remaining": remaining_after,
        }

    except HTTPException:
        raise
    except Exception as e:
        # No exponer detalles internos en 500
        print(f"[create_brochure] Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/download_brochure_pdf")
async def download_brochure_pdf(request: Request, body: DownloadBrochureRequest):
    cache_key = body.cache_key
    payload = get_brochure_payload(cache_key)
    if not payload:
        raise HTTPException(status_code=404, detail="Cache key not found")

    brochure_html = payload.get("brochure")
    company_name = payload.get("data", {}).get("company_name") or "brochure"

    if not brochure_html or not str(brochure_html).strip():
        raise HTTPException(status_code=400, detail="No brochure content available for this key")

    # Sanitizar y asegurar documento HTML
    html = sanitize_html_for_pdf(brochure_html)

    try:
        print(f"[PDF] HTML length: {len(html)}")
    except Exception:
        pass

    # Generar PDF con Playwright vía helper (capturar errores inesperados)
    try:
        pdf_bytes = await render_pdf(request.app, html)
    except Exception:
        # No exponer detalles internos
        raise HTTPException(status_code=500, detail="Internal server error")

    try:
        print(f"[PDF] Bytes length: {len(pdf_bytes) if pdf_bytes else 0}")
    except Exception:
        pass

    headers = {
        "Content-Disposition": f"attachment; filename={company_name}_brochure.pdf",
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)