"""
Agentic Governance Compliance Checker

Validates agent configurations against IMDA MGF for Agentic AI.

4 Dimensions of IMDA Framework:
1. Assess and bound risks upfront
2. Make humans meaningfully accountable
3. Implement technical controls and processes
4. Enable end-user responsibility

Source: IMDA Model AI Governance Framework for Agentic AI (Jan 2026)
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List

logger = logging.getLogger("AgenticGovernanceCompliance")


@dataclass
class ComplianceResult:
    """Result of governance compliance check."""

    compliant: bool
    score: float = 100.0
    violations: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    dimension_scores: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "compliant": self.compliant,
            "score": self.score,
            "violations": self.violations,
            "recommendations": self.recommendations,
            "dimension_scores": self.dimension_scores,
        }


class AgenticGovernanceCompliance:
    """
    Checks agent configurations against IMDA best practices.

    Covers all 4 dimensions:
    1. Risk assessment and bounding
    2. Human accountability
    3. Technical controls
    4. End-user responsibility
    """

    def __init__(self):
        self.high_risk_tools = [
            "payment",
            "database_write",
            "database_delete",
            "file_delete",
            "email_send",
            "api_call",
        ]

    def check(self, config: Dict[str, Any]) -> ComplianceResult:
        """
        Check agent configuration for IMDA compliance.

        Args:
            config: Agent configuration with keys like:
                - agent_id, owner: Identity
                - tools: List of tools
                - human_approval: Approval level
                - logging_enabled, observability: Monitoring
                - tested, evals_run: Pre-deployment testing
                - user_facing, disclosed_as_ai: User disclosure
                - fallback_enabled, error_handling: Error handling

        Returns:
            ComplianceResult
        """
        violations = []
        recommendations = []
        dimension_scores = {
            "risk_assessment": 100.0,
            "human_accountability": 100.0,
            "technical_controls": 100.0,
            "end_user_responsibility": 100.0,
        }

        # Dimension 1: Risk Assessment (2.1)
        d1_violations = self._check_risk_assessment(config)
        violations.extend(d1_violations)
        if d1_violations:
            dimension_scores["risk_assessment"] -= len(d1_violations) * 25

        # Dimension 2: Human Accountability (2.2)
        d2_violations, d2_recs = self._check_human_accountability(config)
        violations.extend(d2_violations)
        recommendations.extend(d2_recs)
        if d2_violations:
            dimension_scores["human_accountability"] -= len(d2_violations) * 25

        # Dimension 3: Technical Controls (2.3)
        d3_violations, d3_recs = self._check_technical_controls(config)
        violations.extend(d3_violations)
        recommendations.extend(d3_recs)
        if d3_violations:
            dimension_scores["technical_controls"] -= len(d3_violations) * 20

        # Dimension 4: End-User Responsibility (2.4)
        d4_violations, d4_recs = self._check_end_user_responsibility(config)
        violations.extend(d4_violations)
        recommendations.extend(d4_recs)
        if d4_violations:
            dimension_scores["end_user_responsibility"] -= len(d4_violations) * 25

        # Calculate overall score
        overall_score = sum(dimension_scores.values()) / 4
        compliant = len(violations) == 0

        return ComplianceResult(
            compliant=compliant,
            score=max(0, overall_score),
            violations=violations,
            recommendations=recommendations,
            dimension_scores=dimension_scores,
        )

    def _check_risk_assessment(self, config: Dict) -> List[str]:
        """Check IMDA 2.1: Assess and bound risks upfront."""
        violations = []

        # Check agent identity
        if not config.get("agent_id") and not config.get("owner"):
            violations.append("[2.1] Missing agent identity/ownership assignment")

        return violations

    def _check_human_accountability(self, config: Dict) -> tuple:
        """Check IMDA 2.2: Human accountability."""
        violations = []
        recommendations = []

        # Check human approval for high-risk
        tools = config.get("tools", [])
        is_high_risk = config.get("risk_level") == "high" or any(
            t in self.high_risk_tools for t in tools
        )

        approval = config.get("human_approval", "significant_steps")

        if is_high_risk and approval == "none":
            violations.append("[2.2] No human oversight for high-risk agent")
            recommendations.append(
                "IMDA 2.2.2: Define significant checkpoints for human approval"
            )

        return violations, recommendations

    def _check_technical_controls(self, config: Dict) -> tuple:
        """Check IMDA 2.3: Technical controls and processes."""
        violations = []
        recommendations = []

        # Check logging/observability
        if not config.get("logging_enabled") and not config.get("observability"):
            violations.append("[2.3] Missing logging/observability")
            recommendations.append(
                "IMDA 2.3.3: Implement continuous monitoring and logging"
            )

        # Check pre-deployment testing
        if config.get("tested") is False or config.get("evals_run") is False:
            violations.append("[2.3] Agent deployed without testing/evaluation")
            recommendations.append(
                "IMDA 2.3.2: Test agents for safety and security before deployment"
            )

        # Check fallback/error handling
        if (
            config.get("fallback_enabled") is False
            or config.get("error_handling") is None
        ):
            violations.append("[2.3] Missing fallback/error handling mechanism")

        return violations, recommendations

    def _check_end_user_responsibility(self, config: Dict) -> tuple:
        """Check IMDA 2.4: End-user responsibility."""
        violations = []
        recommendations = []

        # Check disclosure for user-facing agents
        if config.get("user_facing") and not config.get("disclosed_as_ai"):
            violations.append("[2.4] User-facing agent not disclosed as AI")
            recommendations.append(
                "IMDA 2.4.2: Declare upfront that users are interacting with agents"
            )

        return violations, recommendations


def check_governance_compliance(config: Dict[str, Any]) -> ComplianceResult:
    """Quick compliance check for agent configuration."""
    checker = AgenticGovernanceCompliance()
    return checker.check(config)


if __name__ == "__main__":
    checker = AgenticGovernanceCompliance()

    # Non-compliant config
    bad_config = {
        "tools": ["payment"],
        "human_approval": "none",
        "logging_enabled": False,
    }
    print("Bad config:", checker.check(bad_config))

    # Compliant config
    good_config = {
        "agent_id": "agent_001",
        "owner": "team",
        "tools": ["search"],
        "human_approval": "significant_steps",
        "logging_enabled": True,
        "observability": True,
        "tested": True,
        "evals_run": True,
        "user_facing": True,
        "disclosed_as_ai": True,
        "fallback_enabled": True,
        "error_handling": "retry",
    }
    print("Good config:", checker.check(good_config))
