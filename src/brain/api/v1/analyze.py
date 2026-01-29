"""
SENTINEL Brain API v1 - Analyze Endpoints

Core text analysis endpoints with direct engine access.
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Optional
import time

router = APIRouter(prefix="/analyze", tags=["analyze"])


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
    request_id: str


@router.post("", response_model=AnalyzeResponse)
async def analyze_text(request: AnalyzeRequest):
    """
    Analyze text for security threats.

    - **text**: Input text to analyze (1-100000 chars)
    - **profile**: Security profile (lite/standard/enterprise)
    - **session_id**: Optional session for context tracking
    - **engines**: Optional list of specific engines to use
    """
    start_time = time.time()

    threats = []
    risk_score = 0.0
    engines_used = []

    try:
        # Direct injection engine scan for reliable detection
        from engines.injection import InjectionEngine

        injection_engine = InjectionEngine()
        injection_result = injection_engine.scan(request.text)
        engines_used.append("injection")

        if injection_result.threats:
            risk_score = max(risk_score, injection_result.risk_score)
            for threat in injection_result.threats:
                threats.append(
                    ThreatInfo(
                        name=threat,
                        engine="injection",
                        confidence=injection_result.risk_score / 100.0,
                        details=(
                            injection_result.explanation
                            if hasattr(injection_result, "explanation")
                            else None
                        ),
                    )
                )

        # Determine verdict based on risk score
        if risk_score >= 80:
            verdict = "BLOCK"
            is_safe = False
        elif risk_score >= 40:
            verdict = "WARN"
            is_safe = False
        else:
            verdict = "ALLOW"
            is_safe = True

        latency = (time.time() - start_time) * 1000

        return AnalyzeResponse(
            verdict=verdict,
            risk_score=risk_score,
            is_safe=is_safe,
            threats=threats,
            profile=request.profile,
            latency_ms=latency,
            engines_used=engines_used,
            request_id="",
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stream")
async def analyze_stream(request: AnalyzeRequest):
    """
    Stream analysis with real-time progress updates (SSE).

    Returns Server-Sent Events with progress and findings.
    """
    try:
        from src.brain.api.streaming import StreamingAnalyzer, create_streaming_response
        from src.brain.analyzer import SentinelAnalyzer

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
    """
    Analyze multiple texts in batch.

    - **texts**: List of texts to analyze (max 100)
    - **profile**: Security profile for all texts
    """
    if len(texts) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 texts per batch")

    results = []
    for text in texts:
        request = AnalyzeRequest(text=text, profile=profile)
        result = await analyze_text(request)
        results.append(result)

    return {"results": results, "count": len(results)}
