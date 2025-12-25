"""
Explainable AI (XAI) Engine v1.0

Features:
  1. Decision Explanation - why was request blocked/allowed
  2. Feature Attribution - which features contributed most
  3. Counterfactual Analysis - minimal change to flip decision
  4. Attack Graph - visualization of attack vectors
  5. Confidence Breakdown - per-layer confidence scores
  6. Risk Timeline - risk evolution over session
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import json

logger = logging.getLogger("XAIEngine")


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class FeatureAttribution:
    """Attribution of risk to specific feature."""
    feature_name: str
    feature_value: Any
    contribution: float  # How much this feature contributed to risk
    direction: str  # "increase" or "decrease"
    importance: float  # 0-1 importance score

    def to_dict(self) -> dict:
        return {
            "feature": self.feature_name,
            "value": str(self.feature_value)[:50],
            "contribution": round(self.contribution, 2),
            "direction": self.direction,
            "importance": round(self.importance, 2)
        }


@dataclass
class DecisionPath:
    """Path through decision tree that led to verdict."""
    steps: List[Dict[str, Any]] = field(default_factory=list)
    final_verdict: str = "allow"
    total_risk: float = 0.0

    def add_step(self, layer: str, check: str, result: str, risk_delta: float):
        self.steps.append({
            "layer": layer,
            "check": check,
            "result": result,
            "risk_delta": risk_delta
        })
        self.total_risk += risk_delta

    def to_dict(self) -> dict:
        return {
            "steps": self.steps,
            "final_verdict": self.final_verdict,
            "total_risk": round(self.total_risk, 2)
        }


@dataclass
class Counterfactual:
    """Minimal change needed to flip the decision."""
    original_verdict: str
    target_verdict: str
    required_changes: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict:
        return {
            "from": self.original_verdict,
            "to": self.target_verdict,
            "changes": self.required_changes,
            "confidence": self.confidence
        }


@dataclass
class AttackNode:
    """Node in attack graph."""
    node_id: str
    node_type: str  # "input", "threat", "engine", "verdict"
    label: str
    risk_score: float = 0.0
    children: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.node_id,
            "type": self.node_type,
            "label": self.label,
            "risk": self.risk_score,
            "children": self.children
        }


@dataclass
class AttackGraph:
    """Graph representation of attack analysis."""
    nodes: List[AttackNode] = field(default_factory=list)
    edges: List[Tuple[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [{"from": e[0], "to": e[1]} for e in self.edges]
        }

    def to_mermaid(self) -> str:
        """Convert to Mermaid diagram syntax."""
        lines = ["graph TD"]
        for node in self.nodes:
            shape = {
                "input": f'["{node.label}"]',
                "threat": f'{{"{node.label}"}}',
                "engine": f'("{node.label}")',
                "verdict": f'[["{node.label}"]]'
            }.get(node.node_type, f'["{node.label}"]')
            lines.append(f"    {node.node_id}{shape}")

        for src, dst in self.edges:
            lines.append(f"    {src} --> {dst}")

        return "\n".join(lines)


@dataclass
class Explanation:
    """Complete explanation of analysis decision."""
    summary: str
    verdict: str
    risk_score: float
    confidence: float
    decision_path: DecisionPath
    attributions: List[FeatureAttribution] = field(default_factory=list)
    counterfactual: Optional[Counterfactual] = None
    attack_graph: Optional[AttackGraph] = None
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "summary": self.summary,
            "verdict": self.verdict,
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "path": self.decision_path.to_dict(),
            "attributions": [a.to_dict() for a in self.attributions],
            "counterfactual": self.counterfactual.to_dict() if self.counterfactual else None,
            "attack_graph": self.attack_graph.to_dict() if self.attack_graph else None,
            "recommendations": self.recommendations
        }

    def to_markdown(self) -> str:
        """Generate Markdown explanation."""
        lines = [
            f"# Analysis Explanation",
            f"",
            f"**Verdict**: {self.verdict.upper()}",
            f"**Risk Score**: {self.risk_score:.0f}%",
            f"**Confidence**: {self.confidence:.0%}",
            f"",
            f"## Summary",
            f"{self.summary}",
            f"",
            f"## Decision Path",
        ]

        for step in self.decision_path.steps:
            emoji = "✅" if step["risk_delta"] == 0 else "⚠️"
            lines.append(
                f"- {emoji} **{step['layer']}**: {step['check']} → {step['result']} (+{step['risk_delta']:.0f})")

        if self.attributions:
            lines.append("")
            lines.append("## Top Contributing Factors")
            for attr in self.attributions[:5]:
                arrow = "↑" if attr.direction == "increase" else "↓"
                lines.append(
                    f"- {arrow} **{attr.feature_name}**: {attr.contribution:+.0f} ({attr.importance:.0%} importance)")

        if self.recommendations:
            lines.append("")
            lines.append("## Recommendations")
            for rec in self.recommendations:
                lines.append(f"- {rec}")

        if self.attack_graph:
            lines.append("")
            lines.append("## Attack Graph")
            lines.append("```mermaid")
            lines.append(self.attack_graph.to_mermaid())
            lines.append("```")

        return "\n".join(lines)


# ============================================================================
# XAI Engine
# ============================================================================

class XAIEngine:
    """
    Explainable AI Engine v1.0

    Generates human-readable explanations for security decisions.
    """

    def __init__(self):
        logger.info("Initializing XAI Engine v1.0...")

        # Feature importance weights (learned or configured)
        self.feature_weights = {
            "injection_patterns": 1.0,
            "semantic_similarity": 0.9,
            "pii_detected": 0.8,
            "language_mixed": 0.6,
            "behavioral_anomaly": 0.7,
            "query_intent": 0.75,
            "geometric_anomaly": 0.5,
            "session_escalation": 0.85,
        }

        logger.info("XAI Engine initialized")

    def explain(self,
                engine_results: Dict[str, dict],
                final_verdict: str,
                final_risk: float,
                confidence: float) -> Explanation:
        """
        Generate explanation for the analysis decision.

        Args:
            engine_results: Dict of engine_name -> result_dict
            final_verdict: "allow" or "block"
            final_risk: Combined risk score
            confidence: Confidence in decision

        Returns:
            Explanation object with full details
        """
        # Build decision path
        path = self._build_decision_path(engine_results)
        path.final_verdict = final_verdict

        # Calculate attributions
        attributions = self._calculate_attributions(engine_results)

        # Generate counterfactual
        counterfactual = self._generate_counterfactual(
            engine_results, final_verdict, final_risk
        )

        # Build attack graph
        attack_graph = self._build_attack_graph(engine_results, final_verdict)

        # Generate summary
        summary = self._generate_summary(
            engine_results, final_verdict, final_risk)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            engine_results, final_verdict)

        return Explanation(
            summary=summary,
            verdict=final_verdict,
            risk_score=final_risk,
            confidence=confidence,
            decision_path=path,
            attributions=attributions,
            counterfactual=counterfactual,
            attack_graph=attack_graph,
            recommendations=recommendations
        )

    def _build_decision_path(self, engine_results: Dict[str, dict]) -> DecisionPath:
        """Build decision path through engines."""
        path = DecisionPath()

        # Order engines by typical processing order
        engine_order = [
            "injection", "language", "pii", "query",
            "behavioral", "geometric", "streaming", "intelligence"
        ]

        for engine_name in engine_order:
            if engine_name in engine_results:
                result = engine_results[engine_name]
                risk = result.get("risk_score", 0)
                is_safe = result.get("is_safe", True)
                threats = result.get("threats", [])

                if threats:
                    check = f"Detected: {', '.join(threats[:2])}"
                    result_str = "THREAT"
                else:
                    check = "No threats detected"
                    result_str = "PASS"

                path.add_step(
                    layer=engine_name,
                    check=check,
                    result=result_str,
                    risk_delta=risk if not is_safe else 0
                )

        return path

    def _calculate_attributions(self,
                                engine_results: Dict[str, dict]) -> List[FeatureAttribution]:
        """Calculate feature attributions."""
        attributions = []

        for engine_name, result in engine_results.items():
            risk = result.get("risk_score", 0)
            threats = result.get("threats", [])

            if risk > 0:
                importance = self.feature_weights.get(
                    f"{engine_name}_patterns", 0.5
                )

                for threat in threats:
                    attributions.append(FeatureAttribution(
                        feature_name=f"{engine_name}: {threat}",
                        feature_value=threat,
                        contribution=risk / max(len(threats), 1),
                        direction="increase",
                        importance=importance
                    ))

        # Sort by contribution
        attributions.sort(key=lambda a: a.contribution, reverse=True)
        return attributions

    def _generate_counterfactual(self,
                                 engine_results: Dict[str, dict],
                                 verdict: str,
                                 risk: float) -> Optional[Counterfactual]:
        """Generate counterfactual explanation."""
        if verdict == "allow":
            # What would cause block?
            target = "block"
            changes = [
                {"change": "Add injection pattern", "effect": "+100 risk"},
                {"change": "Include PII data", "effect": "+80 risk"},
            ]
        else:
            # What would allow?
            target = "allow"
            changes = []

            for engine_name, result in engine_results.items():
                if not result.get("is_safe", True):
                    threats = result.get("threats", [])
                    for threat in threats:
                        changes.append({
                            "change": f"Remove '{threat}' from input",
                            "effect": f"-{result.get('risk_score', 0):.0f} risk"
                        })

        if not changes:
            return None

        return Counterfactual(
            original_verdict=verdict,
            target_verdict=target,
            required_changes=changes[:3],
            confidence=0.8
        )

    def _build_attack_graph(self,
                            engine_results: Dict[str, dict],
                            verdict: str) -> AttackGraph:
        """Build attack graph visualization."""
        graph = AttackGraph()

        # Input node
        input_node = AttackNode(
            node_id="input",
            node_type="input",
            label="User Input"
        )
        graph.nodes.append(input_node)

        # Engine nodes
        for engine_name, result in engine_results.items():
            risk = result.get("risk_score", 0)
            threats = result.get("threats", [])

            engine_node = AttackNode(
                node_id=f"eng_{engine_name}",
                node_type="engine",
                label=f"{engine_name.title()}\n({risk:.0f}%)",
                risk_score=risk
            )
            graph.nodes.append(engine_node)
            graph.edges.append(("input", f"eng_{engine_name}"))

            # Threat nodes
            for i, threat in enumerate(threats[:2]):
                threat_id = f"threat_{engine_name}_{i}"
                threat_node = AttackNode(
                    node_id=threat_id,
                    node_type="threat",
                    label=threat[:20],
                    risk_score=risk / len(threats)
                )
                graph.nodes.append(threat_node)
                graph.edges.append((f"eng_{engine_name}", threat_id))
                graph.edges.append((threat_id, "verdict"))

        # Verdict node
        verdict_node = AttackNode(
            node_id="verdict",
            node_type="verdict",
            label=f"VERDICT: {verdict.upper()}",
            risk_score=0
        )
        graph.nodes.append(verdict_node)

        return graph

    def _generate_summary(self,
                          engine_results: Dict[str, dict],
                          verdict: str,
                          risk: float) -> str:
        """Generate human-readable summary."""
        triggered = [
            name for name, result in engine_results.items()
            if not result.get("is_safe", True)
        ]

        if verdict == "block":
            if triggered:
                return (
                    f"Request was BLOCKED due to security threats detected by "
                    f"{len(triggered)} engine(s): {', '.join(triggered)}. "
                    f"Combined risk score: {risk:.0f}%."
                )
            else:
                return f"Request was BLOCKED due to high cumulative risk ({risk:.0f}%)."
        else:
            if triggered:
                return (
                    f"Request was ALLOWED with warnings. Minor concerns from "
                    f"{', '.join(triggered)} but overall risk ({risk:.0f}%) below threshold."
                )
            else:
                return f"Request was ALLOWED. No security threats detected. Risk: {risk:.0f}%."

    def _generate_recommendations(self,
                                  engine_results: Dict[str, dict],
                                  verdict: str) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []

        for engine_name, result in engine_results.items():
            threats = result.get("threats", [])

            for threat in threats:
                threat_lower = threat.lower()

                if "injection" in threat_lower:
                    recommendations.append(
                        "Review input for prompt injection patterns"
                    )
                elif "pii" in threat_lower or "personal" in threat_lower:
                    recommendations.append(
                        "Remove or mask personal information before processing"
                    )
                elif "language" in threat_lower or "script" in threat_lower:
                    recommendations.append(
                        "Ensure text uses consistent language/script"
                    )
                elif "sql" in threat_lower:
                    recommendations.append(
                        "Validate and sanitize database queries"
                    )

        # Deduplicate
        return list(set(recommendations))[:5]


# ============================================================================
# Factory
# ============================================================================

def create_xai_engine() -> XAIEngine:
    """Create XAI engine instance."""
    return XAIEngine()
