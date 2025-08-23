from fastapi import FastAPI, BackgroundTasks
from api.v1.routes import router as api_router
from fastapi.middleware.cors import CORSMiddleware
from playwright.async_api import async_playwright

from services.redis.redis_client import test_redis_connection

if not test_redis_connection():
    raise Exception("Redis connection failed")
else:
    print("Redis connection successful.")

app = FastAPI(title="BrochuresAI API", version="1.0.0")
app.include_router(api_router, prefix="/api/v1")

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)

@app.on_event("startup")
async def startup_playwright():
    app.state.playwright = await async_playwright().start()
    # --no-sandbox es común en contenedores
    app.state.browser = await app.state.playwright.chromium.launch(args=["--no-sandbox"]) 

@app.on_event("shutdown")
async def shutdown_playwright():
    try:
        if getattr(app.state, "browser", None):
            await app.state.browser.close()
        if getattr(app.state, "playwright", None):
            await app.state.playwright.stop()
    except Exception as e:
        print(f"Error closing Playwright: {e}")

