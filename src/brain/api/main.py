"""
SENTINEL Brain API

Main FastAPI application with all routers.

Generated: 2026-01-08
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import API routers
from .requirements_api import router as requirements_router
from .compliance_api import router as compliance_router
from .design_review_api import router as design_review_router

# Create FastAPI app
app = FastAPI(
    title="SENTINEL Brain API",
    description="AI Security Platform - Detection, Compliance, and Design Review",
    version="1.6.0",
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
        "version": "1.6.0",
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
            }
        ]
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.6.0"}


# Include routers
app.include_router(requirements_router)
app.include_router(compliance_router)
app.include_router(design_review_router)


# Export for uvicorn
def create_app():
    return app
