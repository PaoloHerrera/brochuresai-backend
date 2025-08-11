from fastapi import FastAPI, BackgroundTasks
from api.v1.routes import router as api_router

app = FastAPI(title="BrochuresAI API", version="1.0.0")
app.include_router(api_router, prefix="/api/v1")

