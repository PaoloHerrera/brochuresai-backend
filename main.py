from fastapi import FastAPI, Request, Response
from api.v1.routes import router as api_router
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright

from services.redis.redis_client import redis_client
from config import settings
from api.v1.deps import get_client_ip
import time
import asyncio

app = FastAPI(title="BrochuresAI API", version="1.0.0")

# Subrouters are mounted inside api.v1.routes (aggregator)
app.include_router(api_router, prefix="/api/v1")

# Restringir orígenes permitidos (ajustar aquí según despliegue)
origins = [
    "http://localhost:5173",
    "http://localhost:4173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

# Endpoints protegidos por rate limiting (creación y descarga de PDF)
PROTECTED_PATHS = {"/api/v1/create_brochure", "/api/v1/download_brochure_pdf"}

# --- Rate limiting middleware (fixed window) con TTL atómico ---
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    # Permitir libremente OPTIONS
    if request.method == "OPTIONS":
        return await call_next(request)

    # Normalizar path y filtrar si no es protegido
    path = request.url.path.rstrip("/") or "/"
    if path not in PROTECTED_PATHS:
        return await call_next(request)

    ip = get_client_ip(request)

    window = settings.rate_limit_window_seconds
    max_req = settings.rate_limit_max_per_minute
    now = int(time.time())
    bucket = now - (now % window)
    key = f"ratelimit:{ip}:{bucket}"

    try:
        # Evitar race condition: establece la clave con TTL si no existe.
        # Si no existía, la inicializamos en 0 con expiración, luego incrementamos.
        redis_client.set(key, 0, ex=window, nx=True)
        current = redis_client.incr(key)
        if current > max_req:
            reset_in = (bucket + window) - now
            headers = {
                "Retry-After": str(reset_in),
                "X-RateLimit-Limit": str(max_req),
                "X-RateLimit-Remaining": str(max(0, max_req - current)),
                "X-RateLimit-Reset": str(bucket + window),
            }
            return Response(status_code=429, content="Too Many Requests", headers=headers)
    except Exception:
        # Si Redis falla, fail-open
        pass

    response = await call_next(request)

    try:
        current_val = int(redis_client.get(key) or 0)
        remaining = max(0, max_req - current_val)
        response.headers["X-RateLimit-Limit"] = str(max_req)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Window"] = str(window)
    except Exception:
        pass

    return response


# Informar estado de Redis al iniciar la app (ping único, no bloqueante)
@app.on_event("startup")
async def startup_redis_ping():
    try:
        # Ejecutar ping en un hilo para no bloquear el event loop
        ok = await asyncio.get_running_loop().run_in_executor(None, redis_client.ping)
        if ok:
            print("INFO: [Redis] Connected OK")
        else:
            print("INFO: [Redis] Ping returned False")
    except Exception as e:
        print(f"INFO: [Redis] Not available: {e}")

@app.on_event("startup")
async def startup_playwright():
    app.state.playwright = await async_playwright().start()
    app.state.browser = await app.state.playwright.chromium.launch(headless=True, args=["--no-sandbox"]) 
    # Semáforo global para limitar concurrencia de generación de PDFs
    try:
        max_conc = max(1, int(settings.playwright_max_concurrency))
    except Exception:
        max_conc = 2
    app.state.pdf_sema = asyncio.Semaphore(max_conc)


@app.on_event("shutdown")
async def shutdown_playwright():
    try:
        if getattr(app.state, "browser", None):
            await app.state.browser.close()
    except Exception as e:
        try:
            print(f"Error closing Playwright: {e}")
        except Exception:
            pass
    if getattr(app.state, "playwright", None):
        await app.state.playwright.stop()

