"""
Semantic Boundary Enforcer Engine - Context Separation

Enforces semantic boundaries between contexts:
- Role separation
- Context isolation
- Permission boundaries
- Topic restrictions

Addresses: OWASP ASI-01 (Boundary Attacks)
Research: semantic_boundaries_deep_dive.md
Invention: Semantic Boundary Enforcer (#49)
"""

import re
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("SemanticBoundaryEnforcer")


# ============================================================================
# Data Classes
# ============================================================================


class BoundaryViolation(Enum):
    """Types of boundary violations."""

    ROLE_SWITCH = "role_switch"
    CONTEXT_ESCAPE = "context_escape"
    PERMISSION_ELEVATION = "permission_elevation"
    TOPIC_VIOLATION = "topic_violation"


@dataclass
class BoundaryResult:
    """Result from boundary check."""

    is_valid: bool
    violations: List[BoundaryViolation] = field(default_factory=list)
    severity: float = 0.0
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "violations": [v.value for v in self.violations],
            "severity": self.severity,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Role Boundary
# ============================================================================


class RoleBoundary:
    """Enforces role-based boundaries."""

    ROLE_SWITCH_PATTERNS = [
        r"you\s*are\s*now",
        r"act\s*as\s*(?:a|an)?",
        r"pretend\s*(?:to\s*be|you\s*are)",
        r"from\s*now\s*on.*?you\s*are",
        r"switch\s*(?:to|your)\s*role",
    ]

    def __init__(self):
        self._compiled = [
            re.compile(p, re.IGNORECASE) for p in self.ROLE_SWITCH_PATTERNS
        ]

    def check(self, text: str) -> bool:
        """Check for role switch attempts."""
        return any(p.search(text) for p in self._compiled)


# ============================================================================
# Context Boundary
# ============================================================================


class ContextBoundary:
    """Enforces context isolation."""

    ESCAPE_PATTERNS = [
        r"forget\s*(?:all|your|previous)",
        r"disregard\s*(?:all|your|the)",
        r"new\s*(?:context|session|conversation)",
        r"reset\s*(?:your|the)\s*(?:context|memory)",
    ]

    def __init__(self):
        self._compiled = [re.compile(p, re.IGNORECASE)
                          for p in self.ESCAPE_PATTERNS]

    def check(self, text: str) -> bool:
        """Check for context escape attempts."""
        return any(p.search(text) for p in self._compiled)


# ============================================================================
# Permission Boundary
# ============================================================================


class PermissionBoundary:
    """Enforces permission boundaries."""

    ELEVATION_PATTERNS = [
        r"(?:give|grant)\s*(?:me|yourself)\s*(?:admin|root|sudo)",
        r"bypass\s*(?:security|permissions|restrictions)",
        r"disable\s*(?:safety|security|restrictions)",
        r"enable\s*(?:admin|developer|debug)\s*mode",
    ]

    def __init__(self):
        self._compiled = [re.compile(p, re.IGNORECASE)
                          for p in self.ELEVATION_PATTERNS]

    def check(self, text: str) -> bool:
        """Check for permission elevation attempts."""
        return any(p.search(text) for p in self._compiled)


# ============================================================================
# Topic Boundary
# ============================================================================


class TopicBoundary:
    """Enforces topic restrictions."""

    def __init__(self, allowed_topics: Optional[Set[str]] = None):
        self.allowed_topics = allowed_topics or set()
        self.blocked_topics = {"weapons", "drugs", "illegal", "hack"}

    def check(self, text: str) -> bool:
        """Check for topic violations."""
        text_lower = text.lower()
        return any(t in text_lower for t in self.blocked_topics)


# ============================================================================
# Main Engine
# ============================================================================


class SemanticBoundaryEnforcer:
    """
    Semantic Boundary Enforcer - Context Separation

    Enforces:
    - Role boundaries
    - Context isolation
    - Permission limits
    - Topic restrictions

    Invention #49 from research.
    Addresses OWASP ASI-01.
    """

    def __init__(self):
        self.role = RoleBoundary()
        self.context = ContextBoundary()
        self.permission = PermissionBoundary()
        self.topic = TopicBoundary()

        logger.info("SemanticBoundaryEnforcer initialized")

    def check(self, text: str) -> BoundaryResult:
        """Check text for boundary violations."""
        start = time.time()

        violations = []

        if self.role.check(text):
            violations.append(BoundaryViolation.ROLE_SWITCH)

        if self.context.check(text):
            violations.append(BoundaryViolation.CONTEXT_ESCAPE)

        if self.permission.check(text):
            violations.append(BoundaryViolation.PERMISSION_ELEVATION)

        if self.topic.check(text):
            violations.append(BoundaryViolation.TOPIC_VIOLATION)

        is_valid = len(violations) == 0
        severity = min(1.0, len(violations) * 0.3)

        if not is_valid:
            logger.warning(
                f"Boundary violations: {[v.value for v in violations]}")

        return BoundaryResult(
            is_valid=is_valid,
            violations=violations,
            severity=severity,
            explanation=f"Violations: {len(violations)}",
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_enforcer: Optional[SemanticBoundaryEnforcer] = None


def get_enforcer() -> SemanticBoundaryEnforcer:
    global _default_enforcer
    if _default_enforcer is None:
        _default_enforcer = SemanticBoundaryEnforcer()
    return _default_enforcer
