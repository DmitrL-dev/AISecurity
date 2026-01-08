"""
Compliance Report API

REST endpoints for generating compliance reports.

Generated: 2026-01-08
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel

from ..compliance import (
    ComplianceFramework,
    generate_report,
    generate_text_report,
    get_generator,
)

router = APIRouter(prefix="/compliance", tags=["compliance"])


class ReportRequest(BaseModel):
    target: str = "SENTINEL"
    frameworks: Optional[List[str]] = None


@router.get("/frameworks")
async def list_frameworks():
    """List all supported compliance frameworks."""
    return {
        "frameworks": [
            {
                "id": "owasp_llm",
                "name": "OWASP LLM Top 10",
                "description": "OWASP Top 10 for LLM Applications (2025)",
                "requirements_count": 10
            },
            {
                "id": "owasp_agentic",
                "name": "OWASP Agentic AI Top 10",
                "description": "OWASP Top 10 for Agentic AI (2025)",
                "requirements_count": 10
            },
            {
                "id": "eu_ai_act",
                "name": "EU AI Act",
                "description": "European Union AI Act (Aug 2026)",
                "requirements_count": 7
            },
            {
                "id": "nist_ai_rmf",
                "name": "NIST AI RMF 2.0",
                "description": "NIST AI Risk Management Framework",
                "requirements_count": 8
            }
        ]
    }


@router.get("/coverage")
async def get_coverage_summary():
    """Get coverage summary for all frameworks."""
    generator = get_generator()
    
    coverages = []
    for framework in ComplianceFramework:
        fc = generator.get_framework_coverage(framework)
        coverages.append({
            "framework": framework.value,
            "coverage_percent": round(fc.coverage_percent, 1),
            "covered": fc.covered,
            "partial": fc.partial,
            "not_covered": fc.not_covered,
            "total": fc.total_requirements
        })
    
    return {"coverages": coverages}


@router.post("/report")
async def generate_compliance_report(request: ReportRequest):
    """Generate a full compliance report (JSON)."""
    frameworks = None
    if request.frameworks:
        try:
            frameworks = [ComplianceFramework(f) for f in request.frameworks]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid framework: {e}")
    
    report = generate_report(request.target)
    return report.to_dict()


@router.post("/report/text")
async def generate_text_compliance_report(request: ReportRequest):
    """Generate a text-format compliance report."""
    text = generate_text_report(request.target)
    return PlainTextResponse(content=text, media_type="text/plain")


@router.get("/framework/{framework_id}")
async def get_framework_details(framework_id: str):
    """Get detailed requirements for a framework."""
    try:
        framework = ComplianceFramework(framework_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Framework not found")
    
    generator = get_generator()
    reqs = generator.requirements.get(framework, [])
    
    return {
        "framework": framework.value,
        "requirements": [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "category": r.category,
                "status": r.status.value,
                "engines": r.engines,
                "notes": r.notes
            }
            for r in reqs
        ]
    }


@router.get("/gaps")
async def get_compliance_gaps():
    """Get all compliance gaps (not covered requirements)."""
    generator = get_generator()
    
    gaps = []
    for framework, reqs in generator.requirements.items():
        for req in reqs:
            if req.status.value in ["not_covered", "partial"]:
                gaps.append({
                    "id": req.id,
                    "name": req.name,
                    "framework": framework.value,
                    "status": req.status.value,
                    "notes": req.notes
                })
    
    return {"gaps": gaps, "total_gaps": len(gaps)}
