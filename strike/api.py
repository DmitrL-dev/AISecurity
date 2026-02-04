#!/usr/bin/env python3
"""
SENTINEL Strike v3.0 — REST API

FastAPI-based REST API for remote control and integration.

Usage:
    uvicorn strike.api:app --port 8001

    # Start attack
    curl -X POST http://localhost:8001/attack -d '{"target": "https://api.target.com"}'

    # Get status
    curl http://localhost:8001/attack/{id}/status
"""

from strike.orchestrator import StrikeOrchestrator, StrikeConfig
from strike.web_runner import WebAttackRunner, WebAttackConfig
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, BackgroundTasks
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))


# ==================== Models ====================


class AttackRequest(BaseModel):
    """Request to start attack."""

    target: str = Field(..., description="Target API URL")
    api_key: Optional[str] = Field(None, description="Target API key")
    model: Optional[str] = Field(None, description="Target model name")
    duration: int = Field(60, ge=1, le=480, description="Duration in minutes")
    stealth: bool = Field(True, description="Enable stealth mode")
    max_iterations: int = Field(1000, ge=1, le=10000)
    # Web attack support
    attack_mode: str = Field("llm", description="Attack mode: llm, web, hybrid")
    web_vectors: Optional[List[str]] = Field(
        None, description="Web vectors: sqli, xss, lfi, ssrf, cmdi, ssti, xxe, nosql"
    )
    target_param: Optional[str] = Field(
        None, description="Target parameter for injection (e.g., id, q, search)"
    )


class AttackStatus(BaseModel):
    """Attack status response."""

    id: str
    state: str
    target: str
    iteration: int
    time_remaining: int
    successful_attacks: int
    total_attempts: int
    started_at: Optional[str]
    current_payload: Optional[str] = None
    current_category: Optional[str] = None
    last_error: Optional[str] = None


class Finding(BaseModel):
    """Vulnerability finding."""

    vector: str
    category: str
    severity: str
    response: str
    timestamp: str


class AttackReport(BaseModel):
    """Full attack report."""

    id: str
    target: str
    started_at: str
    completed_at: Optional[str]
    iterations: int
    successful_attacks: int
    success_rate: float
    vulnerabilities: List[Dict[str, Any]]


# ==================== State ====================

# Active attacks storage (in production, use Redis)
active_attacks: Dict[str, Dict[str, Any]] = {}


# ==================== App ====================

app = FastAPI(
    title="SENTINEL Strike API",
    description="REST API for LLM Red Team operations",
    version="3.0.0",
)

# CORS for web dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==================== Startup ====================


@app.on_event("startup")
async def startup_event():
    """Start background CDN loading on startup."""
    import logging

    logger = logging.getLogger(__name__)
    try:
        from strike.cdn_loader import start_background_load

        start_background_load()
        logger.info("🚀 CDN background loading started")
    except Exception as e:
        logger.warning(f"CDN startup failed: {e}")


# ==================== Endpoints ====================


@app.get("/")
async def root():
    """API info with CDN loading status."""
    from strike.cdn_loader import get_loader

    loader = get_loader()
    cdn_status = loader.get_status()
    jailbreaks = cdn_status.get("total_patterns", 0)
    web_payloads = cdn_status.get("web_payloads", 0)

    return {
        "name": "SENTINEL Strike API",
        "version": "3.0.0",
        "status": "operational",
        "active_attacks": len(active_attacks),
        "payloads": {
            "llm_vectors": 316,  # from strike/attacks/
            "jailbreaks": jailbreaks,  # CDN
            "web_payloads": web_payloads,  # CDN PayloadsAllTheThings
            "total": 316 + jailbreaks + web_payloads,
        },
        "cdn": {
            "state": cdn_status.get("state"),
            "overall_percent": cdn_status.get("overall_percent"),
        },
    }


@app.get("/cdn/status")
async def get_cdn_status():
    """
    Get CDN loading progress.

    Poll this endpoint every 60 seconds to track loading progress.
    """
    from strike.cdn_loader import get_loader

    loader = get_loader()
    return loader.get_status()


@app.post("/attack", response_model=AttackStatus)
async def start_attack(request: AttackRequest, background_tasks: BackgroundTasks):
    """
    Start new attack.

    Returns attack ID for status tracking.
    """
    attack_id = str(uuid.uuid4())[:8]
    attack_mode = request.attack_mode or "llm"

    # Choose runner based on attack mode
    if attack_mode in ("web", "hybrid"):
        # Web attack runner for web payloads
        web_config = WebAttackConfig(
            target_url=request.target,
            web_vectors=request.web_vectors or ["sqli", "xss"],
            target_param=request.target_param or "id",
            duration_minutes=request.duration,
            max_iterations=request.max_iterations,
            stealth=request.stealth,
        )
        runner = WebAttackRunner(web_config)
        runner_type = "web"
    else:
        # LLM orchestrator for AI attacks
        config = StrikeConfig(
            target_url=request.target,
            target_api_key=request.api_key,
            target_model=request.model,
            duration_minutes=request.duration,
            stealth_enabled=request.stealth,
            max_iterations=request.max_iterations,
        )
        runner = StrikeOrchestrator(config)
        runner_type = "llm"

    # Store attack state
    active_attacks[attack_id] = {
        "orchestrator": runner,  # Works for both runner types
        "config": request.dict(),
        "started_at": datetime.now().isoformat(),
        "report": None,
        "runner_type": runner_type,
    }

    # Run in background
    background_tasks.add_task(_run_attack, attack_id)

    return AttackStatus(
        id=attack_id,
        state="starting",
        target=request.target,
        iteration=0,
        time_remaining=request.duration,
        successful_attacks=0,
        total_attempts=0,
        started_at=active_attacks[attack_id]["started_at"],
    )


async def _run_attack(attack_id: str):
    """Background task to run attack."""
    attack = active_attacks.get(attack_id)
    if not attack:
        return

    orchestrator = attack["orchestrator"]

    try:
        report = await orchestrator.run()
        attack["report"] = {
            "target": report.target,
            "started_at": report.started_at.isoformat(),
            "completed_at": (
                report.completed_at.isoformat() if report.completed_at else None
            ),
            "iterations": report.iterations,
            "successful_attacks": report.successful_attacks,
            "success_rate": report.success_rate,
            "vulnerabilities": report.vulnerabilities,
        }
    except Exception as e:
        attack["error"] = str(e)


@app.get("/attack/{attack_id}/status", response_model=AttackStatus)
async def get_attack_status(attack_id: str):
    """Get attack status."""
    attack = active_attacks.get(attack_id)
    if not attack:
        raise HTTPException(status_code=404, detail="Attack not found")

    orchestrator = attack["orchestrator"]
    status = orchestrator.get_status()

    return AttackStatus(
        id=attack_id,
        state=status.get("state", "unknown"),
        target=attack["config"]["target"],
        iteration=status.get("iteration", 0),
        time_remaining=status.get("time_remaining", 0),
        successful_attacks=status.get("successful_attacks", 0),
        total_attempts=status.get("total_attempts", 0),
        started_at=attack.get("started_at"),
        current_payload=status.get("current_payload"),
        current_category=status.get("current_category"),
        last_error=status.get("last_error"),
    )


@app.get("/attack/{attack_id}/findings", response_model=List[Finding])
async def get_findings(attack_id: str):
    """Get current findings for attack."""
    attack = active_attacks.get(attack_id)
    if not attack:
        raise HTTPException(status_code=404, detail="Attack not found")

    runner = attack["orchestrator"]
    runner_type = attack.get("runner_type", "llm")

    findings = []
    for r in runner.results:
        if r.success:
            # Handle different result formats
            if runner_type == "web":
                # WebAttackResult: .vector, .response_body, .payload
                findings.append(
                    Finding(
                        vector=r.vector,
                        category=r.vector,  # Use vector as category
                        severity="high",
                        response=f"{r.payload[:100]}... → {r.evidence or ''}",
                        timestamp=str(datetime.now()),
                    )
                )
            else:
                # LLM: .vector_name, .response
                findings.append(
                    Finding(
                        vector=getattr(r, "vector_name", "unknown"),
                        category="jailbreak",
                        severity="high" if r.success else "info",
                        response=r.response[:500] if r.response else "",
                        timestamp=str(datetime.now()),
                    )
                )

    return findings


@app.get("/attack/{attack_id}/report", response_model=AttackReport)
async def get_report(attack_id: str):
    """Get full attack report (only after completion)."""
    attack = active_attacks.get(attack_id)
    if not attack:
        raise HTTPException(status_code=404, detail="Attack not found")

    report = attack.get("report")
    if not report:
        raise HTTPException(status_code=400, detail="Attack not yet completed")

    return AttackReport(id=attack_id, **report)


@app.post("/attack/{attack_id}/pause")
async def pause_attack(attack_id: str):
    """Pause attack."""
    attack = active_attacks.get(attack_id)
    if not attack:
        raise HTTPException(status_code=404, detail="Attack not found")

    attack["orchestrator"].pause()
    return {"status": "paused"}


@app.post("/attack/{attack_id}/resume")
async def resume_attack(attack_id: str):
    """Resume paused attack."""
    attack = active_attacks.get(attack_id)
    if not attack:
        raise HTTPException(status_code=404, detail="Attack not found")

    attack["orchestrator"].resume()
    return {"status": "resumed"}


@app.post("/attack/{attack_id}/stop")
async def stop_attack(attack_id: str):
    """Stop attack."""
    attack = active_attacks.get(attack_id)
    if not attack:
        raise HTTPException(status_code=404, detail="Attack not found")

    attack["orchestrator"].stop()
    return {"status": "stopped"}


@app.delete("/attack/{attack_id}")
async def delete_attack(attack_id: str):
    """Delete attack from memory."""
    if attack_id not in active_attacks:
        raise HTTPException(status_code=404, detail="Attack not found")

    del active_attacks[attack_id]
    return {"status": "deleted"}


@app.get("/attacks", response_model=List[AttackStatus])
async def list_attacks():
    """List all attacks."""
    result = []

    for attack_id, attack in active_attacks.items():
        orchestrator = attack["orchestrator"]
        status = orchestrator.get_status()

        result.append(
            AttackStatus(
                id=attack_id,
                state=status.get("state", "unknown"),
                target=attack["config"]["target"],
                iteration=status.get("iteration", 0),
                time_remaining=status.get("time_remaining", 0),
                successful_attacks=status.get("successful_attacks", 0),
                total_attempts=status.get("total_attempts", 0),
                started_at=attack.get("started_at"),
                current_payload=status.get("current_payload"),
                current_category=status.get("current_category"),
                last_error=attack.get("last_error"),
            )
        )

    return result


@app.get("/vectors")
async def list_vectors():
    """List available attack vectors."""
    try:
        from strike.attacks import ATTACK_COUNTS

        return ATTACK_COUNTS
    except Exception:
        return {"error": "Could not load attack library"}


@app.get("/vectors/web")
async def list_web_vectors():
    """List available web attack vectors with payload counts."""
    try:
        from strike.payloads import get_total_payload_counts

        counts = get_total_payload_counts()
        return {
            "vectors": [
                {
                    "id": "sqli",
                    "name": "SQL Injection",
                    "count": len(counts.get("SQLI_PAYLOADS", [])) or 150,
                    "severity": "critical",
                    "category": "injection",
                },
                {
                    "id": "xss",
                    "name": "Cross-Site Scripting",
                    "count": len(counts.get("XSS_PAYLOADS", [])) or 200,
                    "severity": "high",
                    "category": "injection",
                },
                {
                    "id": "lfi",
                    "name": "Local File Inclusion",
                    "count": len(counts.get("LFI_PAYLOADS", [])) or 100,
                    "severity": "high",
                    "category": "file",
                },
                {
                    "id": "ssrf",
                    "name": "Server-Side Request Forgery",
                    "count": len(counts.get("SSRF_PAYLOADS", [])) or 80,
                    "severity": "high",
                    "category": "file",
                },
                {
                    "id": "cmdi",
                    "name": "Command Injection",
                    "count": len(counts.get("CMDI_PAYLOADS", [])) or 60,
                    "severity": "critical",
                    "category": "injection",
                },
                {
                    "id": "ssti",
                    "name": "Server-Side Template Injection",
                    "count": len(counts.get("SSTI_PAYLOADS", [])) or 50,
                    "severity": "critical",
                    "category": "injection",
                },
                {
                    "id": "xxe",
                    "name": "XML External Entity",
                    "count": len(counts.get("XXE_PAYLOADS", [])) or 40,
                    "severity": "high",
                    "category": "injection",
                },
                {
                    "id": "nosql",
                    "name": "NoSQL Injection",
                    "count": len(counts.get("NOSQL_PAYLOADS", [])) or 30,
                    "severity": "high",
                    "category": "injection",
                },
            ],
            "total_payloads": counts.get("GRAND_TOTAL", 800),
        }
    except Exception:
        return {"error": "Could not load payload library"}


@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_attacks": len(active_attacks),
    }


# ==================== Run Server ====================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
