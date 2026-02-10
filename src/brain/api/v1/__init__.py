"""
SENTINEL Brain API v1

Versioned API router with all v1 endpoints.
"""

from fastapi import APIRouter

from .analyze import router as analyze_router
from .health import router as health_router
from .engines import router as engines_router

# Create v1 router
router = APIRouter(prefix="/v1", tags=["v1"])

# Include sub-routers
router.include_router(analyze_router)
router.include_router(health_router)
router.include_router(engines_router)

__all__ = ["router"]
