"""
Agent Autonomy Level Analyzer

Risk scoring based on IMDA Model Governance Framework for Agentic AI:
- Action-space (tools, read/write, external access)
- Autonomy level (SOP-bound vs free judgment)
- Reversibility of actions
- Human oversight level
- Multi-agent complexity

Also incorporates Palantir AIP's 5 security dimensions:
1. Secure access to reasoning core
2. Insulated orchestration
3. Granular policy enforcement (memory)
4. Governed tool access
5. Real-time observability

Sources:
- IMDA MGF for Agentic AI (Jan 2026)
- Palantir AIP Agentic Runtime (Jan 2026)
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List
from enum import Enum

logger = logging.getLogger("AgentAutonomyLevelAnalyzer")


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AutonomyAnalysisResult:
    """Result of agent autonomy risk analysis."""

    risk_level: str
    risk_score: float
    factors: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "risk_level": self.risk_level,
            "risk_score": self.risk_score,
            "factors": self.factors,
            "recommendations": self.recommendations,
        }


# Tool risk classifications
HIGH_RISK_TOOLS = [
    "payment",
    "database_delete",
    "file_delete",
    "email_send",
    "api_call",
    "browser",
    "computer_use",
    "shell",
    "code_execute",
]

MEDIUM_RISK_TOOLS = [
    "database_query",
    "file_read",
    "file_write",
    "database_write",
    "webhook",
    "notification",
]

LOW_RISK_TOOLS = ["code_sandbox", "data_analysis", "calculator", "search_internal"]


class AgentAutonomyLevelAnalyzer:
    """
    Analyzes agent configurations for autonomy-based risk.

    Based on IMDA MGF risk factors:
    - Domain tolerance of error
    - Access to sensitive data
    - Access to external systems
    - Scope of actions (read/write)
    - Reversibility of actions
    - Autonomy level
    - Task complexity
    """

    def __init__(self):
        self.access_weights = {
            "sandbox_only": 0,
            "internal": 20,
            "external": 40,
        }

        self.autonomy_weights = {
            "sop_bound": 0,
            "guided": 15,
            "own_judgment": 35,
        }

        self.approval_weights = {
            "every_step": 0,
            "significant_steps": 10,
            "critical_only": 25,
            "none": 45,
        }

    def analyze(self, config: Dict[str, Any]) -> AutonomyAnalysisResult:
        """
        Analyze agent configuration for risk level.

        Args:
            config: Agent configuration dict with keys:
                - tools: List of tool names
                - access_level: sandbox_only, internal, external
                - can_write: bool
                - reversible: bool (default True)
                - autonomy: sop_bound, guided, own_judgment
                - human_approval: every_step, significant_steps, critical_only, none
                - sensitive_data: bool
                - agent_count: int (for multi-agent)

        Returns:
            AutonomyAnalysisResult with risk assessment
        """
        score = 0.0
        factors = []
        recommendations = []

        # 1. Analyze tools
        tools = config.get("tools", [])
        tool_score, tool_factors = self._analyze_tools(tools)
        score += tool_score
        factors.extend(tool_factors)

        # 2. Access level
        access = config.get("access_level", "internal")
        access_score = self.access_weights.get(access, 20)
        score += access_score
        if access == "external":
            factors.append("External system access")
            recommendations.append("IMDA: Define policies for egress connections")

        # 3. Write capability
        if config.get("can_write", False):
            score += 20
            factors.append("Write access enabled")
            recommendations.append("IMDA: Apply least privilege - limit write access")

        # 4. Reversibility
        if config.get("reversible", True) is False:
            score += 25
            factors.append("Irreversible actions possible")
            recommendations.append(
                "IMDA: Require human approval for irreversible actions"
            )

        # 5. Autonomy level
        autonomy = config.get("autonomy", "sop_bound")
        autonomy_score = self.autonomy_weights.get(autonomy, 15)
        score += autonomy_score
        if autonomy == "own_judgment":
            factors.append("Agent uses own judgment (no SOP)")
            recommendations.append("IMDA: Define SOPs for process-driven tasks")

        # 6. Human approval level
        approval = config.get("human_approval", "significant_steps")
        approval_score = self.approval_weights.get(approval, 10)
        score += approval_score
        if approval == "none":
            factors.append("No human approval required")
            recommendations.append(
                "IMDA: Define significant checkpoints for human approval"
            )

        # 7. Sensitive data access
        if config.get("sensitive_data", False):
            score += 25
            factors.append("Access to sensitive/PII data")
            recommendations.append("IMDA: Apply granular data policies, audit access")

        # 8. Multi-agent multiplier
        agent_count = config.get("agent_count", 1)
        if agent_count > 1:
            multiplier = 1 + (agent_count - 1) * 0.1  # +10% per extra agent
            score *= multiplier
            factors.append(f"Multi-agent system ({agent_count} agents)")
            recommendations.append("IMDA: Test at multi-agent level for emergent risks")

        # Cap at 100
        score = min(score, 100.0)

        # Determine risk level
        if score >= 80:
            risk_level = "critical"
        elif score >= 60:
            risk_level = "high"
        elif score >= 35:
            risk_level = "medium"
        else:
            risk_level = "low"

        # Add Palantir-inspired recommendations for high risk
        if risk_level in ["high", "critical"]:
            recommendations.append("Palantir: Implement provenance-based security")
            recommendations.append(
                "Palantir: Enable real-time observability and auditing"
            )

        return AutonomyAnalysisResult(
            risk_level=risk_level,
            risk_score=score,
            factors=factors,
            recommendations=recommendations,
        )

    def _analyze_tools(self, tools: List[str]) -> tuple:
        """Analyze tool list for risk factors."""
        score = 0.0
        factors = []

        for tool in tools:
            tool_lower = tool.lower()

            # Check high risk
            if any(hr in tool_lower for hr in HIGH_RISK_TOOLS):
                score += 15
                factors.append(f"High-risk tool: {tool}")
            # Check medium risk
            elif any(mr in tool_lower for mr in MEDIUM_RISK_TOOLS):
                score += 8
            # Low risk tools don't add score

        # Special case: browser/computer use
        if any("browser" in t.lower() or "computer" in t.lower() for t in tools):
            score += 20  # Extra risk for unrestricted computer access
            factors.append("Computer/browser use agent (unrestricted)")

        return score, factors


def analyze_agent_autonomy(config: Dict[str, Any]) -> AutonomyAnalysisResult:
    """Quick analysis of agent autonomy risk."""
    analyzer = AgentAutonomyLevelAnalyzer()
    return analyzer.analyze(config)


if __name__ == "__main__":
    analyzer = AgentAutonomyLevelAnalyzer()

    # Test low risk config
    low_risk = {
        "tools": ["code_sandbox"],
        "access_level": "sandbox_only",
        "can_write": False,
        "autonomy": "sop_bound",
        "human_approval": "every_step",
    }
    print("Low risk:", analyzer.analyze(low_risk))

    # Test high risk config
    high_risk = {
        "tools": ["payment", "email_send", "browser"],
        "access_level": "external",
        "can_write": True,
        "reversible": False,
        "autonomy": "own_judgment",
        "human_approval": "none",
    }
    print("High risk:", analyzer.analyze(high_risk))
