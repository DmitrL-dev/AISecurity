"""
SENTINEL Brain API v1 - Engines Endpoints

Engine management and status.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/engines", tags=["engines"])


class EngineInfo(BaseModel):
    """Information about a detection engine."""
    name: str
    version: str
    enabled: bool
    description: str
    category: str  # injection, pii, behavioral, etc.
    latency_avg_ms: Optional[float] = None


class EngineListResponse(BaseModel):
    """List of available engines."""
    engines: List[EngineInfo]
    count: int


class EngineStatsResponse(BaseModel):
    """Engine statistics."""
    name: str
    total_calls: int
    detections: int
    avg_latency_ms: float
    error_rate: float


@router.get("", response_model=EngineListResponse)
async def list_engines():
    """
    List all available detection engines.
    
    Returns information about each engine including status and description.
    """
    engines = [
        EngineInfo(
            name="injection",
            version="2.0.0",
            enabled=True,
            description="Multi-layer prompt injection detection",
            category="injection",
        ),
        EngineInfo(
            name="pii",
            version="1.5.0",
            enabled=True,
            description="Personally identifiable information detection",
            category="pii",
        ),
        EngineInfo(
            name="behavioral",
            version="1.2.0",
            enabled=True,
            description="Behavioral anomaly detection",
            category="behavioral",
        ),
        EngineInfo(
            name="yara",
            version="1.0.0",
            enabled=True,
            description="YARA rule-based pattern matching",
            category="patterns",
        ),
        EngineInfo(
            name="hallucination",
            version="1.0.0",
            enabled=True,
            description="Hallucination and factual accuracy detection",
            category="quality",
        ),
        EngineInfo(
            name="tda_enhanced",
            version="1.0.0",
            enabled=True,
            description="Topological Data Analysis for semantic attacks",
            category="advanced",
        ),
        EngineInfo(
            name="sheaf_coherence",
            version="1.0.0",
            enabled=True,
            description="Sheaf-theoretic coherence analysis",
            category="advanced",
        ),
    ]
    
    return EngineListResponse(engines=engines, count=len(engines))


@router.get("/{engine_name}")
async def get_engine(engine_name: str):
    """
    Get detailed information about a specific engine.
    """
    # Would look up engine details
    return {
        "name": engine_name,
        "version": "1.0.0",
        "enabled": True,
        "config": {},
    }


@router.get("/{engine_name}/stats", response_model=EngineStatsResponse)
async def get_engine_stats(engine_name: str):
    """
    Get statistics for a specific engine.
    """
    try:
        from src.brain.observability.metrics import get_metrics
        
        metrics = get_metrics()
        
        return EngineStatsResponse(
            name=engine_name,
            total_calls=0,  # Would get from metrics
            detections=0,
            avg_latency_ms=0.0,
            error_rate=0.0,
        )
        
    except Exception:
        return EngineStatsResponse(
            name=engine_name,
            total_calls=0,
            detections=0,
            avg_latency_ms=0.0,
            error_rate=0.0,
        )
