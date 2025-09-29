from fastapi import APIRouter

from api.v1.brochures import router as brochures_router
from api.v1.users import router as users_router

# Aggregator router for v1
router = APIRouter()

# Mount sub-routers
router.include_router(users_router)
router.include_router(brochures_router)
