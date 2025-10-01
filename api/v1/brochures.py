import re

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from api.v1.schemas import CreateBrochureRequest, DownloadBrochureRequest
from services.brochures.cache import (
    generate_cache_key as gen_cache_key_service,
)
from services.brochures.cache import (
    get_brochure_payload,
    store_brochure,
)
from services.openai.openai_client import OpenAIClient
from services.pdf.html_utils import sanitize_html_for_pdf
from services.pdf.renderer import render_pdf
from services.scraper import Scraper

from .deps import (
    MAX_BROCHURES_PER_USER,
    ensure_user,
    get_client_ip,
    get_conn,
    increment_brochures,
    reset_brochures_if_new_day,
    set_full_language,
    store_brochure_analytics,
)

router = APIRouter()


def _sanitize_filename_component(
    name: str, default: str = "brochure", max_length: int = 100
) -> str:
    if not name:
        return default
    # Eliminar CRLF e invisibles de control
    s = str(name).replace("\r", "").replace("\n", "").strip()
    # Quitar caracteres problemáticos para nombres de archivo y cabeceras
    s = re.sub(r'[<>:"/\\|?*\x00-\x1F]', "", s)
    # Colapsar espacios a guiones bajos
    s = re.sub(r"\s+", "_", s)
    # Evitar puntos/espacios al inicio/fin
    s = s.strip(". ")
    # Evitar nombres reservados de Windows
    reserved = (
        {"CON", "PRN", "AUX", "NUL"}
        | {f"COM{i}" for i in range(1, 10)}
        | {f"LPT{i}" for i in range(1, 10)}
    )
    if s.upper() in reserved:
        s = f"file_{s}"
    # Limitar longitud
    if len(s) == 0:
        s = default
    if len(s) > max_length:
        s = s[:max_length]
    return s


@router.post("/create_brochure")
async def create_brochure(request: Request, body: CreateBrochureRequest):
    import time

    start_time = time.time()

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
            # Analytics para quota excedida
            processing_time = int((time.time() - start_time) * 1000)
            store_brochure_analytics(
                anon_id=user["anon_id"],
                url=url,
                company_name=company_name,
                brochure_type=brochure_type,
                language=language,
                success=False,
                processing_time_ms=processing_time,
                error_type="quota_exceeded",
            )
            raise HTTPException(status_code=429, detail="Brochure quota exceeded for this user")

        brochure = await OpenAIClient(Scraper).create_brochure(
            company_name, url, language, brochure_type
        )

        processing_time = int((time.time() - start_time) * 1000)

        if isinstance(brochure, str) and brochure.startswith("Error:"):
            msg_lower = brochure.lower()
            error_type = (
                "openai_api_key_missing"
                if "missing openai api key" in msg_lower
                else "upstream_error"
            )

            # Analytics para errores
            store_brochure_analytics(
                anon_id=user["anon_id"],
                url=url,
                company_name=company_name,
                brochure_type=brochure_type,
                language=language,
                success=False,
                processing_time_ms=processing_time,
                error_type=error_type,
            )

            if "missing openai api key" in msg_lower:
                # Falta de configuración: 503 Service Unavailable
                raise HTTPException(status_code=503, detail="Service unavailable")
            else:
                # Error del proveedor o de procesamiento: 502 Bad Gateway
                raise HTTPException(status_code=502, detail="Upstream provider error")

        # Si no hay error, continuar flujo normal

        # Analytics para éxito
        store_brochure_analytics(
            anon_id=user["anon_id"],
            url=url,
            company_name=company_name,
            brochure_type=brochure_type,
            language=language,
            success=True,
            processing_time_ms=processing_time,
        )

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
        # Analytics para errores internos
        try:
            processing_time = int((time.time() - start_time) * 1000)
            # Intentar obtener datos básicos para analytics
            url = getattr(body, "url", "unknown") if "body" in locals() else "unknown"
            company_name = getattr(body, "company_name", None) if "body" in locals() else None
            brochure_type = (
                getattr(body, "brochure_type", "professional")
                if "body" in locals()
                else "professional"
            )
            language = getattr(body, "language", "en") if "body" in locals() else "en"
            anon_id = user.get("anon_id") if "user" in locals() and user else "unknown"

            store_brochure_analytics(
                anon_id=anon_id,
                url=str(url),
                company_name=str(company_name) if company_name else None,
                brochure_type=str(brochure_type),
                language=str(language),
                success=False,
                processing_time_ms=processing_time,
                error_type="internal_error",
            )
        except Exception:
            # Si analytics falla, no hacer nada más
            pass

        # No exponer detalles internos en 500
        print(f"[create_brochure] Error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


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
        raise HTTPException(status_code=500, detail="Internal server error") from None

    try:
        print(f"[PDF] Bytes length: {len(pdf_bytes) if pdf_bytes else 0}")
    except Exception:
        pass

    headers = {
        # Quoted-string y nombre seguro
        "Content-Disposition": f'attachment; filename="{_sanitize_filename_component(company_name)}_brochure.pdf"',
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
