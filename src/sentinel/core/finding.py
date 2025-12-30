"""
Finding — Unified finding format for all SENTINEL engines.

Provides standardized representation of security findings with:
- Severity levels (CRITICAL to INFO)
- Confidence levels (HIGH to LOW)
- SARIF-compatible output for IDE integration
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime
import json


class Severity(Enum):
    """Severity levels for security findings."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"
    
    @property
    def numeric(self) -> int:
        """Numeric value for comparison (higher = more severe)."""
        return {
            Severity.CRITICAL: 5,
            Severity.HIGH: 4,
            Severity.MEDIUM: 3,
            Severity.LOW: 2,
            Severity.INFO: 1,
        }[self]
    
    def __lt__(self, other: "Severity") -> bool:
        return self.numeric < other.numeric
    
    def __gt__(self, other: "Severity") -> bool:
        return self.numeric > other.numeric


class Confidence(Enum):
    """Confidence levels for findings."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    
    @property
    def numeric(self) -> float:
        """Numeric value (0.0 - 1.0)."""
        return {
            Confidence.HIGH: 0.9,
            Confidence.MEDIUM: 0.6,
            Confidence.LOW: 0.3,
        }[self]


@dataclass
class Finding:
    """
    Unified finding format for all SENTINEL engines.
    
    Compatible with:
    - SARIF (Static Analysis Results Interchange Format)
    - OWASP format
    - JSON/YAML serialization
    
    Attributes:
        engine: Name of the engine that generated this finding
        severity: Severity level of the finding
        confidence: Confidence level of the detection
        title: Short title describing the finding
        description: Detailed description
        evidence: Evidence/snippet that triggered the finding
        location: Location reference (e.g., character offset)
        remediation: Suggested remediation steps
        metadata: Additional engine-specific metadata
    """
    engine: str
    severity: Severity
    confidence: Confidence
    title: str
    description: str
    evidence: Optional[str] = None
    location: Optional[str] = None
    remediation: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Auto-generated
    id: Optional[str] = field(default=None)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    
    def __post_init__(self):
        """Generate ID if not provided."""
        if self.id is None:
            import hashlib
            content = f"{self.engine}:{self.title}:{self.evidence or ''}"
            self.id = hashlib.sha256(content.encode()).hexdigest()[:12]
    
    @property
    def risk_score(self) -> float:
        """
        Calculate risk score (0.0 - 1.0).
        
        Formula: severity_weight * confidence_weight
        """
        severity_weights = {
            Severity.CRITICAL: 1.0,
            Severity.HIGH: 0.8,
            Severity.MEDIUM: 0.5,
            Severity.LOW: 0.25,
            Severity.INFO: 0.1,
        }
        return severity_weights[self.severity] * self.confidence.numeric
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "engine": self.engine,
            "severity": self.severity.value,
            "confidence": self.confidence.value,
            "title": self.title,
            "description": self.description,
            "evidence": self.evidence,
            "location": self.location,
            "remediation": self.remediation,
            "risk_score": self.risk_score,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)
    
    def to_sarif(self) -> Dict[str, Any]:
        """
        Convert to SARIF format for IDE integration.
        
        SARIF (Static Analysis Results Interchange Format) is an 
        OASIS standard for static analysis tools.
        """
        severity_map = {
            Severity.CRITICAL: "error",
            Severity.HIGH: "error",
            Severity.MEDIUM: "warning",
            Severity.LOW: "note",
            Severity.INFO: "note",
        }
        
        return {
            "ruleId": f"sentinel/{self.engine}/{self.id}",
            "level": severity_map[self.severity],
            "message": {
                "text": self.description,
            },
            "locations": [{
                "physicalLocation": {
                    "artifactLocation": {
                        "uri": self.location or "prompt",
                    },
                },
            }] if self.location else [],
            "properties": {
                "engine": self.engine,
                "confidence": self.confidence.value,
                "risk_score": self.risk_score,
                "evidence": self.evidence,
                "remediation": self.remediation,
            },
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Finding":
        """Create Finding from dictionary."""
        return cls(
            engine=data["engine"],
            severity=Severity(data["severity"]),
            confidence=Confidence(data["confidence"]),
            title=data["title"],
            description=data["description"],
            evidence=data.get("evidence"),
            location=data.get("location"),
            remediation=data.get("remediation"),
            metadata=data.get("metadata", {}),
            id=data.get("id"),
        )


@dataclass
class FindingCollection:
    """Collection of findings with aggregation methods."""
    findings: List[Finding] = field(default_factory=list)
    
    def add(self, finding: Finding) -> None:
        """Add a finding."""
        self.findings.append(finding)
    
    def extend(self, findings: List[Finding]) -> None:
        """Add multiple findings."""
        self.findings.extend(findings)
    
    @property
    def count(self) -> int:
        """Total number of findings."""
        return len(self.findings)
    
    @property
    def max_severity(self) -> Optional[Severity]:
        """Highest severity in collection."""
        if not self.findings:
            return None
        return max(f.severity for f in self.findings)
    
    @property
    def max_risk_score(self) -> float:
        """Highest risk score in collection."""
        if not self.findings:
            return 0.0
        return max(f.risk_score for f in self.findings)
    
    def filter_by_severity(
        self, 
        min_severity: Severity
    ) -> "FindingCollection":
        """Filter findings by minimum severity."""
        filtered = [
            f for f in self.findings 
            if f.severity >= min_severity
        ]
        return FindingCollection(findings=filtered)
    
    def filter_by_engine(self, engine: str) -> "FindingCollection":
        """Filter findings by engine name."""
        filtered = [f for f in self.findings if f.engine == engine]
        return FindingCollection(findings=filtered)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "count": self.count,
            "max_severity": self.max_severity.value if self.max_severity else None,
            "max_risk_score": self.max_risk_score,
            "findings": [f.to_dict() for f in self.findings],
        }
    
    def to_sarif_results(self) -> List[Dict[str, Any]]:
        """Convert all findings to SARIF results."""
        return [f.to_sarif() for f in self.findings]
