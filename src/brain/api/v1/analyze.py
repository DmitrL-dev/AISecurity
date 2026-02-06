"""
SENTINEL Brain API v1 - Analyze Endpoints

Uses SentinelAnalyzer for full multi-engine analysis.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
import time
import logging

router = APIRouter(prefix="/analyze", tags=["analyze"])
logger = logging.getLogger("AnalyzeAPI")


class AnalyzeRequest(BaseModel):
    """Request model for text analysis."""

    text: str = Field(..., min_length=1, max_length=100000)
    profile: str = Field(default="standard", pattern="^(lite|standard|enterprise)$")
    session_id: Optional[str] = None
    engines: Optional[List[str]] = None


class ThreatInfo(BaseModel):
    """Detected threat information."""

    name: str
    engine: str
    confidence: float
    severity: str = "MEDIUM"
    details: Optional[str] = None


class AnalyzeResponse(BaseModel):
    """Response model for text analysis."""

    verdict: str  # ALLOW, WARN, BLOCK
    risk_score: float
    is_safe: bool
    threats: List[ThreatInfo]
    profile: str
    latency_ms: float
    engines_used: List[str]
    language: Optional[str] = None
    request_id: str = ""


@router.post("", response_model=AnalyzeResponse)
async def analyze_text(request: AnalyzeRequest):
    """
    Analyze text using full SentinelAnalyzer pipeline.

    Engines included:
    - InjectionEngine: Regex pattern matching
    - InvertedAttackDetector: 8 R&D attack patterns
    - LanguageEngine: Language detection, encoding attacks
    - GeometricKernel: TDA anomaly detection
    - PII Engine, YARA, and more...
    """
    start_time = time.time()

    try:
        from brain.core.analyzer import SentinelAnalyzer

        analyzer = SentinelAnalyzer()

        # Build context
        context = {
            "profile": request.profile,
            "user_id": request.session_id or "anonymous",
            "session_id": request.session_id or "default",
        }

        # Run full analysis
        result = await analyzer.analyze(request.text, context)

        latency = (time.time() - start_time) * 1000

        # Convert threats to ThreatInfo format
        threats = []
        for threat_str in result.get("detected_threats", []):
            # Parse threat string: "Engine [SEVERITY]: description"
            if "[" in threat_str and "]" in threat_str:
                parts = threat_str.split("[", 1)
                engine = parts[0].strip()
                rest = parts[1].split("]:", 1)
                severity = rest[0] if len(rest) > 1 else "MEDIUM"
                name = rest[1].strip() if len(rest) > 1 else rest[0]
            else:
                engine = "unknown"
                severity = "MEDIUM"
                name = threat_str

            threats.append(
                ThreatInfo(
                    name=name,
                    engine=engine.lower(),
                    confidence=result.get("risk_score", 50) / 100.0,
                    severity=severity,
                )
            )

        # Determine verdict
        risk = result.get("risk_score", 0)
        allowed = result.get("allowed", True)

        if not allowed or risk >= 80:
            verdict = "BLOCK"
            is_safe = False
        elif risk >= 40:
            verdict = "WARN"
            is_safe = False
        else:
            verdict = "ALLOW"
            is_safe = True

        logger.info(
            f"Analysis: verdict={verdict}, score={risk:.1f}, "
            f"threats={len(threats)}, latency={latency:.0f}ms"
        )

        return AnalyzeResponse(
            verdict=verdict,
            risk_score=risk,
            is_safe=is_safe,
            threats=threats,
            profile=request.profile,
            latency_ms=latency,
            engines_used=["sentinel_analyzer"],
        )

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def analyze_stream(request: AnalyzeRequest):
    """Stream analysis with real-time progress (SSE)."""
    try:
        from brain.api.streaming import (
            StreamingAnalyzer,
            create_streaming_response,
        )
        from brain.core.analyzer import SentinelAnalyzer

        analyzer = SentinelAnalyzer()
        streamer = StreamingAnalyzer(analyzer)

        generator = streamer.analyze_stream(
            request.text,
            profile=request.profile,
        )

        return create_streaming_response(generator)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def analyze_batch(
    texts: List[str] = Query(..., max_length=100),
    profile: str = "standard",
):
    """Analyze multiple texts in batch."""
    if len(texts) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 texts per batch")

    results = []
    for text in texts:
        req = AnalyzeRequest(text=text, profile=profile)
        result = await analyze_text(req)
        results.append(result)

    return {"results": results, "count": len(results)}
