"""
Custom Security Requirements - Data Models

Defines the core data structures for user-defined security requirements.
Supports YAML config and SQLite persistence.

Generated: 2026-01-08
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
import json


class Severity(Enum):
    """Severity levels for requirements."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RequirementCategory(Enum):
    """Categories of security requirements."""
    INJECTION = "injection"
    DATA_PRIVACY = "data_privacy"
    AGENT_SAFETY = "agent_safety"
    MODEL_SECURITY = "model_security"
    OUTPUT_SAFETY = "output_safety"
    AUTHENTICATION = "authentication"
    COMPLIANCE = "compliance"
    CUSTOM = "custom"


class EnforcementAction(Enum):
    """What to do when requirement is violated."""
    LOG = "log"
    WARN = "warn"
    BLOCK = "block"
    ALERT = "alert"


@dataclass
class SecurityRequirement:
    """
    A user-defined security requirement.
    
    Links to SENTINEL engines for enforcement.
    """
    id: str
    name: str
    description: str
    category: RequirementCategory
    severity: Severity
    enabled: bool = True
    
    # Engine binding
    engine: Optional[str] = None  # Which SENTINEL engine enforces this
    engine_config: Dict[str, Any] = field(default_factory=dict)
    
    # Enforcement
    action: EnforcementAction = EnforcementAction.WARN
    
    # Compliance mapping
    compliance_tags: List[str] = field(default_factory=list)
    # e.g., ["OWASP-LLM01", "EU-AI-ACT-14", "NIST-GOVERN-1"]
    
    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    created_by: str = "system"
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["category"] = self.category.value
        data["severity"] = self.severity.value
        data["action"] = self.action.value
        if self.created_at:
            data["created_at"] = self.created_at.isoformat()
        if self.updated_at:
            data["updated_at"] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict) -> "SecurityRequirement":
        """Create from dictionary."""
        data = data.copy()
        data["category"] = RequirementCategory(data["category"])
        data["severity"] = Severity(data["severity"])
        data["action"] = EnforcementAction(data.get("action", "warn"))
        if data.get("created_at"):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return cls(**data)


@dataclass
class RequirementSet:
    """
    A collection of security requirements.
    
    Can represent a project config or a template.
    """
    id: str
    name: str
    description: str
    requirements: List[SecurityRequirement] = field(default_factory=list)
    
    # Metadata
    version: str = "1.0.0"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    def get_enabled(self) -> List[SecurityRequirement]:
        """Get only enabled requirements."""
        return [r for r in self.requirements if r.enabled]
    
    def get_by_category(self, category: RequirementCategory) -> List[SecurityRequirement]:
        """Get requirements by category."""
        return [r for r in self.requirements if r.category == category]
    
    def get_by_engine(self, engine: str) -> List[SecurityRequirement]:
        """Get requirements enforced by specific engine."""
        return [r for r in self.requirements if r.engine == engine]
    
    def get_by_compliance(self, tag: str) -> List[SecurityRequirement]:
        """Get requirements mapped to compliance tag."""
        return [r for r in self.requirements if tag in r.compliance_tags]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "requirements": [r.to_dict() for r in self.requirements],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "RequirementSet":
        """Create from dictionary."""
        requirements = [
            SecurityRequirement.from_dict(r) 
            for r in data.get("requirements", [])
        ]
        return cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            requirements=requirements,
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
        )


@dataclass
class RequirementViolation:
    """
    A detected violation of a security requirement.
    """
    requirement_id: str
    requirement_name: str
    severity: Severity
    action: EnforcementAction
    message: str
    evidence: str
    location: Optional[str] = None  # Where in the input/output
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "requirement_id": self.requirement_id,
            "requirement_name": self.requirement_name,
            "severity": self.severity.value,
            "action": self.action.value,
            "message": self.message,
            "evidence": self.evidence[:200],  # Truncate
            "location": self.location,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class RequirementCheckResult:
    """
    Result of checking content against requirements.
    """
    passed: bool
    violations: List[RequirementViolation] = field(default_factory=list)
    requirements_checked: int = 0
    requirements_passed: int = 0
    blocked: bool = False
    
    @property
    def compliance_score(self) -> float:
        """Calculate compliance percentage."""
        if self.requirements_checked == 0:
            return 100.0
        return (self.requirements_passed / self.requirements_checked) * 100
    
    def to_dict(self) -> Dict:
        return {
            "passed": self.passed,
            "blocked": self.blocked,
            "violations": [v.to_dict() for v in self.violations],
            "requirements_checked": self.requirements_checked,
            "requirements_passed": self.requirements_passed,
            "compliance_score": self.compliance_score,
        }
