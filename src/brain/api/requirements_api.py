"""
Custom Security Requirements - REST API

FastAPI endpoints for managing security requirements.

Generated: 2026-01-08
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from datetime import datetime

from ..requirements import (
    RequirementsManager,
    SecurityRequirement,
    RequirementSet,
    RequirementCategory,
    Severity,
    EnforcementAction,
)
from ..requirements.enforcer import RequirementsEnforcer

router = APIRouter(prefix="/requirements", tags=["requirements"])

# Pydantic models for API
class RequirementCreate(BaseModel):
    name: str
    description: str = ""
    category: str = "custom"
    severity: str = "medium"
    engine: Optional[str] = None
    engine_config: dict = Field(default_factory=dict)
    action: str = "warn"
    compliance_tags: List[str] = Field(default_factory=list)


class RequirementUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    severity: Optional[str] = None
    action: Optional[str] = None


class RequirementSetCreate(BaseModel):
    name: str
    description: str = ""


class CheckRequest(BaseModel):
    text: str


class CheckResponse(BaseModel):
    passed: bool
    blocked: bool
    compliance_score: float
    requirements_checked: int
    requirements_passed: int
    violations: List[dict]


# Dependency
def get_manager():
    # In production, this would be injected
    return RequirementsManager()


@router.get("/sets")
async def list_requirement_sets(manager: RequirementsManager = Depends(get_manager)):
    """List all requirement sets."""
    return manager.list_all()


@router.post("/sets")
async def create_requirement_set(
    data: RequirementSetCreate,
    manager: RequirementsManager = Depends(get_manager)
):
    """Create a new requirement set."""
    req_set = manager.create(data.name, data.description)
    return req_set.to_dict()


@router.get("/sets/{set_id}")
async def get_requirement_set(
    set_id: str,
    manager: RequirementsManager = Depends(get_manager)
):
    """Get a requirement set by ID."""
    req_set = manager.get(set_id)
    if not req_set:
        raise HTTPException(status_code=404, detail="Requirement set not found")
    return req_set.to_dict()


@router.delete("/sets/{set_id}")
async def delete_requirement_set(
    set_id: str,
    manager: RequirementsManager = Depends(get_manager)
):
    """Delete a requirement set."""
    manager.delete(set_id)
    return {"status": "deleted"}


@router.post("/sets/{set_id}/requirements")
async def add_requirement(
    set_id: str,
    data: RequirementCreate,
    manager: RequirementsManager = Depends(get_manager)
):
    """Add a requirement to a set."""
    try:
        req = manager.add_requirement(
            set_id=set_id,
            name=data.name,
            description=data.description,
            category=RequirementCategory(data.category),
            severity=Severity(data.severity),
            engine=data.engine,
            engine_config=data.engine_config,
            action=EnforcementAction(data.action),
            compliance_tags=data.compliance_tags,
        )
        return req.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.patch("/sets/{set_id}/requirements/{req_id}")
async def update_requirement(
    set_id: str,
    req_id: str,
    data: RequirementUpdate,
    manager: RequirementsManager = Depends(get_manager)
):
    """Update a requirement."""
    req_set = manager.get(set_id)
    if not req_set:
        raise HTTPException(status_code=404, detail="Requirement set not found")
    
    for req in req_set.requirements:
        if req.id == req_id:
            if data.name is not None:
                req.name = data.name
            if data.description is not None:
                req.description = data.description
            if data.enabled is not None:
                req.enabled = data.enabled
            if data.severity is not None:
                req.severity = Severity(data.severity)
            if data.action is not None:
                req.action = EnforcementAction(data.action)
            req.updated_at = datetime.now()
            manager.save(req_set)
            return req.to_dict()
    
    raise HTTPException(status_code=404, detail="Requirement not found")


@router.delete("/sets/{set_id}/requirements/{req_id}")
async def delete_requirement(
    set_id: str,
    req_id: str,
    manager: RequirementsManager = Depends(get_manager)
):
    """Delete a requirement from a set."""
    req_set = manager.get(set_id)
    if not req_set:
        raise HTTPException(status_code=404, detail="Requirement set not found")
    
    req_set.requirements = [r for r in req_set.requirements if r.id != req_id]
    req_set.updated_at = datetime.now()
    manager.save(req_set)
    return {"status": "deleted"}


@router.post("/sets/{set_id}/check", response_model=CheckResponse)
async def check_text(
    set_id: str,
    data: CheckRequest,
    manager: RequirementsManager = Depends(get_manager)
):
    """Check text against requirements."""
    req_set = manager.get(set_id)
    if not req_set:
        raise HTTPException(status_code=404, detail="Requirement set not found")
    
    enforcer = RequirementsEnforcer(req_set)
    result = enforcer.check_text(data.text)
    
    return CheckResponse(
        passed=result.passed,
        blocked=result.blocked,
        compliance_score=result.compliance_score,
        requirements_checked=result.requirements_checked,
        requirements_passed=result.requirements_passed,
        violations=[v.to_dict() for v in result.violations],
    )


@router.get("/sets/{set_id}/export")
async def export_yaml(
    set_id: str,
    manager: RequirementsManager = Depends(get_manager)
):
    """Export requirement set as YAML."""
    req_set = manager.get(set_id)
    if not req_set:
        raise HTTPException(status_code=404, detail="Requirement set not found")
    
    import yaml
    yaml_content = yaml.dump(req_set.to_dict(), default_flow_style=False)
    
    from fastapi.responses import PlainTextResponse
    return PlainTextResponse(
        content=yaml_content,
        media_type="application/x-yaml",
        headers={"Content-Disposition": f"attachment; filename={req_set.name}.yaml"}
    )


@router.post("/sets/import")
async def import_yaml(
    yaml_content: str,
    manager: RequirementsManager = Depends(get_manager)
):
    """Import requirement set from YAML."""
    import yaml
    try:
        data = yaml.safe_load(yaml_content)
        req_set = RequirementSet.from_dict(data)
        manager.save(req_set)
        return req_set.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid YAML: {e}")
