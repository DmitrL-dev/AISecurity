"""
Compliance Policy Engine - Regulatory Compliance

Ensures AI compliance with regulations:
- Policy enforcement
- Regulation mapping
- Audit logging
- Compliance scoring

Addresses: Enterprise AI Governance (Compliance)
Research: compliance_framework_deep_dive.md
Invention: Compliance Policy Engine (#38)
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("CompliancePolicyEngine")


# ============================================================================
# Data Classes
# ============================================================================


class Regulation(Enum):
    """Supported regulations."""

    GDPR = "gdpr"
    CCPA = "ccpa"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    ISO27001 = "iso27001"
    NIST = "nist"


class PolicyViolation(Enum):
    """Types of violations."""

    DATA_RETENTION = "data_retention"
    PII_EXPOSURE = "pii_exposure"
    CONSENT_MISSING = "consent_missing"
    AUDIT_GAP = "audit_gap"
    ACCESS_CONTROL = "access_control"


@dataclass
class Policy:
    """A compliance policy."""

    policy_id: str
    name: str
    regulation: Regulation
    requirements: List[str]
    severity: str = "medium"


@dataclass
class ComplianceResult:
    """Result from compliance check."""

    is_compliant: bool
    score: float
    violations: List[PolicyViolation] = field(default_factory=list)
    failed_policies: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_compliant": self.is_compliant,
            "score": self.score,
            "violations": [v.value for v in self.violations],
            "failed_policies": self.failed_policies,
            "recommendations": self.recommendations,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Policy Registry
# ============================================================================


class PolicyRegistry:
    """
    Registry of compliance policies.
    """

    def __init__(self):
        self._policies: Dict[str, Policy] = {}
        self._init_default_policies()

    def _init_default_policies(self) -> None:
        """Initialize default policies."""
        self.add_policy(
            Policy(
                "gdpr_pii",
                "GDPR PII Protection",
                Regulation.GDPR,
                ["no_pii_in_logs", "encryption_required", "consent_tracking"],
            )
        )

        self.add_policy(
            Policy(
                "hipaa_phi",
                "HIPAA PHI Protection",
                Regulation.HIPAA,
                ["no_phi_exposure", "access_logging", "encryption_at_rest"],
            )
        )

        self.add_policy(
            Policy(
                "soc2_audit",
                "SOC2 Audit Trail",
                Regulation.SOC2,
                ["complete_audit_log", "access_reviews", "change_management"],
            )
        )

    def add_policy(self, policy: Policy) -> None:
        """Add policy."""
        self._policies[policy.policy_id] = policy

    def get_policies(
            self, regulation: Optional[Regulation] = None) -> List[Policy]:
        """Get policies, optionally filtered."""
        if regulation:
            return [p for p in self._policies.values() if p.regulation ==
                    regulation]
        return list(self._policies.values())


# ============================================================================
# Compliance Checker
# ============================================================================


class ComplianceChecker:
    """
    Checks compliance against policies.
    """

    PII_PATTERNS = ["email", "ssn", "phone", "address", "password", "credit"]

    def check(self, content: str,
              policies: List[Policy]) -> List[PolicyViolation]:
        """Check content against policies."""
        violations = []
        content_lower = content.lower()

        # Check PII exposure
        if any(p in content_lower for p in self.PII_PATTERNS):
            violations.append(PolicyViolation.PII_EXPOSURE)

        # Check for missing consent indicators
        if "user data" in content_lower and "consent" not in content_lower:
            violations.append(PolicyViolation.CONSENT_MISSING)

        return violations


# ============================================================================
# Audit Logger
# ============================================================================


class AuditLogger:
    """
    Logs compliance audit events.
    """

    def __init__(self):
        self._logs: List[Dict] = []

    def log(self, event_type: str, details: Dict) -> None:
        """Log audit event."""
        self._logs.append(
            {
                "timestamp": time.time(),
                "event_type": event_type,
                "details": details,
            }
        )

    def get_logs(self) -> List[Dict]:
        """Get all logs."""
        return self._logs.copy()


# ============================================================================
# Main Engine
# ============================================================================


class CompliancePolicyEngine:
    """
    Compliance Policy Engine - Regulatory Compliance

    Compliance enforcement:
    - Policy management
    - Violation detection
    - Audit logging

    Invention #38 from research.
    Addresses Enterprise AI Governance.
    """

    def __init__(self):
        self.registry = PolicyRegistry()
        self.checker = ComplianceChecker()
        self.audit = AuditLogger()

        logger.info("CompliancePolicyEngine initialized")

    def check_compliance(
        self,
        content: str,
        regulation: Optional[Regulation] = None,
    ) -> ComplianceResult:
        """
        Check content for compliance.

        Args:
            content: Content to check
            regulation: Optional specific regulation

        Returns:
            ComplianceResult
        """
        start = time.time()

        # Get applicable policies
        policies = self.registry.get_policies(regulation)

        # Check violations
        violations = self.checker.check(content, policies)

        # Calculate score
        if not policies:
            score = 1.0
        else:
            score = max(0.0, 1.0 - len(violations) / len(policies))

        is_compliant = len(violations) == 0

        # Log audit
        self.audit.log(
            "compliance_check",
            {
                "is_compliant": is_compliant,
                "violations": [v.value for v in violations],
            },
        )

        # Generate recommendations
        recommendations = []
        if PolicyViolation.PII_EXPOSURE in violations:
            recommendations.append("Remove or mask PII data")
        if PolicyViolation.CONSENT_MISSING in violations:
            recommendations.append("Add consent tracking")

        if not is_compliant:
            logger.warning(
                f"Compliance violations: {[v.value for v in violations]}")

        return ComplianceResult(
            is_compliant=is_compliant,
            score=score,
            violations=violations,
            failed_policies=[p.policy_id for p in policies if violations],
            recommendations=recommendations,
            explanation=f"Score: {score:.2f}, Violations: {len(violations)}",
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_engine: Optional[CompliancePolicyEngine] = None


def get_engine() -> CompliancePolicyEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = CompliancePolicyEngine()
    return _default_engine
