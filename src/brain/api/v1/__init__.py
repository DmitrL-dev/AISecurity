"""
SENTINEL Brain API v1

Versioned API router with all v1 endpoints.
"""

from fastapi import APIRouter

from .analyze import router as analyze_router
from .health import router as health_router
from .engines import router as engines_router
from .engine_toggle import router as toggle_router
from .audit import router as audit_router

# Create v1 router
router = APIRouter(prefix="/v1", tags=["v1"])

# Include sub-routers
# NOTE: toggle_router must come BEFORE engines_router to avoid route conflicts
# (both have prefix /engines, toggle has /audit-log which could match as engine name)
router.include_router(analyze_router)
router.include_router(health_router)
router.include_router(audit_router)  # System audit
router.include_router(toggle_router)  # Must be before engines_router
router.include_router(engines_router)

__all__ = ["router"]
