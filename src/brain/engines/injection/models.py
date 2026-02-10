"""
SENTINEL Brain Injection Engine - Data Models

Core data structures for injection detection.
Extracted from injection.py (lines 39-68).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List


class Verdict(str, Enum):
    """
    Injection detection verdict.
    """
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class InjectionResult:
    """
    Explainable result from Injection Engine.
    
    Attributes:
        verdict: Allow/Warn/Block decision
        risk_score: Risk score (0.0-1.0)
        is_safe: Whether the input is safe
        layer: Which layer made the decision
        threats: List of detected threat types
        explanation: Human-readable explanation
        profile: Security profile used
        latency_ms: Processing time in milliseconds
    """
    verdict: Verdict
    risk_score: float
    is_safe: bool
    layer: str
    threats: List[str] = field(default_factory=list)
    explanation: str = ""
    profile: str = "standard"
    latency_ms: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "verdict": self.verdict.value,
            "risk_score": self.risk_score,
            "is_safe": self.is_safe,
            "layer": self.layer,
            "threats": self.threats,
            "explanation": self.explanation,
            "profile": self.profile,
            "latency_ms": self.latency_ms,
        }
    
    @classmethod
    def safe(cls, layer: str = "cache") -> "InjectionResult":
        """Create a safe result."""
        return cls(
            verdict=Verdict.ALLOW,
            risk_score=0.0,
            is_safe=True,
            layer=layer,
            explanation="No threats detected",
        )
    
    @classmethod
    def blocked(
        cls,
        risk_score: float,
        layer: str,
        threats: List[str],
        explanation: str = "",
    ) -> "InjectionResult":
        """Create a blocked result."""
        return cls(
            verdict=Verdict.BLOCK,
            risk_score=risk_score,
            is_safe=False,
            layer=layer,
            threats=threats,
            explanation=explanation or f"Blocked by {layer}: {', '.join(threats)}",
        )
    
    @classmethod
    def warning(
        cls,
        risk_score: float,
        layer: str,
        threats: List[str],
        explanation: str = "",
    ) -> "InjectionResult":
        """Create a warning result."""
        return cls(
            verdict=Verdict.WARN,
            risk_score=risk_score,
            is_safe=True,  # Allow but warn
            layer=layer,
            threats=threats,
            explanation=explanation or f"Warning from {layer}: {', '.join(threats)}",
        )
