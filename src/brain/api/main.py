"""
SENTINEL Brain API

Main FastAPI application with all routers.

Generated: 2026-01-08
Updated: 2026-01-09 (added metrics, v1 router)
"""

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

# Import API routers
from .requirements_api import router as requirements_router
from .compliance_api import router as compliance_router
from .design_review_api import router as design_review_router

# Import v1 router
try:
    from .v1 import router as v1_router
    HAS_V1 = True
except ImportError:
    HAS_V1 = False

# Import observability
try:
    from ..observability.metrics import get_metrics
    from ..observability.health import get_health
    HAS_OBSERVABILITY = True
except ImportError:
    HAS_OBSERVABILITY = False

# Create FastAPI app
app = FastAPI(
    title="SENTINEL Brain API",
    description="AI Security Platform - Detection, Compliance, and Design Review",
    version="1.7.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """API root endpoint."""
    return {
        "name": "SENTINEL Brain API",
        "version": "1.7.0",
        "modules": [
            {
                "name": "Requirements",
                "description": "Custom security requirements management",
                "prefix": "/requirements"
            },
            {
                "name": "Compliance",
                "description": "Unified compliance reporting",
                "prefix": "/compliance"
            },
            {
                "name": "Design Review",
                "description": "AI architecture security review",
                "prefix": "/design-review"
            },
            {
                "name": "API v1",
                "description": "Versioned API endpoints",
                "prefix": "/v1"
            }
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if HAS_OBSERVABILITY:
        health = get_health()
        result = await health.check_all()
        return {
            "status": result.status.value,
            "version": "1.7.0",
            "components": [
                {"name": c.name, "status": c.status.value}
                for c in result.components
            ]
        }
    return {"status": "healthy", "version": "1.7.0"}


@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    if HAS_OBSERVABILITY:
        registry = get_metrics()
        return Response(
            content=registry.collect(),
            media_type="text/plain; charset=utf-8"
        )
    # Return minimal metrics if observability not available
    return Response(
        content="# SENTINEL Brain API metrics\nsentinel_up 1\n",
        media_type="text/plain; charset=utf-8"
    )


@app.get("/ready")
async def readiness():
    """Readiness probe for load balancers."""
    return {"ready": True}


# Include routers
app.include_router(requirements_router)
app.include_router(compliance_router)
app.include_router(design_review_router)

# Include v1 router if available
if HAS_V1:
    app.include_router(v1_router)


# Export for uvicorn
def create_app():
    return app
