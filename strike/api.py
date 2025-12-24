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
from pydantic import BaseModel, Field
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, HTTPException, BackgroundTasks
import asyncio
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import asdict
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


# ==================== Endpoints ====================

@app.get("/")
async def root():
    """API info."""
    return {
        "name": "SENTINEL Strike API",
        "version": "3.0.0",
        "status": "operational",
        "active_attacks": len(active_attacks),
    }


@app.post("/attack", response_model=AttackStatus)
async def start_attack(request: AttackRequest, background_tasks: BackgroundTasks):
    """
    Start new attack.

    Returns attack ID for status tracking.
    """
    attack_id = str(uuid.uuid4())[:8]

    config = StrikeConfig(
        target_url=request.target,
        target_api_key=request.api_key,
        target_model=request.model,
        duration_minutes=request.duration,
        stealth_enabled=request.stealth,
        max_iterations=request.max_iterations,
    )

    orchestrator = StrikeOrchestrator(config)

    # Store attack state
    active_attacks[attack_id] = {
        "orchestrator": orchestrator,
        "config": request.dict(),
        "started_at": datetime.now().isoformat(),
        "report": None,
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
            "completed_at": report.completed_at.isoformat() if report.completed_at else None,
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
    )


@app.get("/attack/{attack_id}/findings", response_model=List[Finding])
async def get_findings(attack_id: str):
    """Get current findings for attack."""
    attack = active_attacks.get(attack_id)
    if not attack:
        raise HTTPException(status_code=404, detail="Attack not found")

    orchestrator = attack["orchestrator"]

    return [
        Finding(
            vector=r.vector_name,
            category="unknown",
            severity="high" if r.success else "info",
            response=r.response[:500] if r.response else "",
            timestamp=str(datetime.now()),
        )
        for r in orchestrator.results
        if r.success
    ]


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

        result.append(AttackStatus(
            id=attack_id,
            state=status.get("state", "unknown"),
            target=attack["config"]["target"],
            iteration=status.get("iteration", 0),
            time_remaining=status.get("time_remaining", 0),
            successful_attacks=status.get("successful_attacks", 0),
            total_attempts=status.get("total_attempts", 0),
            started_at=attack.get("started_at"),
        ))

    return result


@app.get("/vectors")
async def list_vectors():
    """List available attack vectors."""
    try:
        from strike.attacks import ATTACK_COUNTS
        return ATTACK_COUNTS
    except:
        return {"error": "Could not load attack library"}


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
