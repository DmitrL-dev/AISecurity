"""
SENTINEL Brain API v1 - Health Endpoints

Health check and readiness probes.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List
from datetime import datetime

router = APIRouter(prefix="/health", tags=["health"])


class ComponentStatus(BaseModel):
    """Status of a single component."""
    name: str
    status: str  # healthy, degraded, unhealthy
    message: str = ""
    latency_ms: float = 0.0


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: str
    components: List[ComponentStatus]


class ReadyResponse(BaseModel):
    """Readiness check response."""
    ready: bool
    checks: Dict[str, bool]


@router.get("", response_model=HealthResponse)
async def health_check():
    """
    Comprehensive health check.
    
    Returns status of all system components.
    """
    try:
        from src.brain.observability.health import get_health
        
        health = get_health()
        result = await health.check_all()
        
        return HealthResponse(
            status=result.status.value,
            version=result.version,
            timestamp=result.timestamp,
            components=[
                ComponentStatus(
                    name=c.name,
                    status=c.status.value,
                    message=c.message,
                    latency_ms=c.latency_ms,
                )
                for c in result.components
            ],
        )
        
    except Exception as e:
        return HealthResponse(
            status="unhealthy",
            version="unknown",
            timestamp=datetime.now().isoformat(),
            components=[
                ComponentStatus(
                    name="error",
                    status="unhealthy",
                    message=str(e),
                )
            ],
        )


@router.get("/ready", response_model=ReadyResponse)
async def readiness_check():
    """
    Quick readiness check for load balancer.
    
    Returns true if service can accept requests.
    """
    try:
        from src.brain.observability.health import get_health
        
        health = get_health()
        is_ready = await health.check_ready()
        
        return ReadyResponse(
            ready=is_ready,
            checks={
                "brain": True,
                "engines": True,
            },
        )
        
    except Exception:
        return ReadyResponse(ready=False, checks={})


@router.get("/live")
async def liveness_check():
    """
    Simple liveness probe.
    
    Returns 200 if process is alive.
    """
    return {"alive": True}
