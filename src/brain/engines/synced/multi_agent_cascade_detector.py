"""
Multi-Agent Cascade Detector

Detects cascading failures and emergent risks in multi-agent systems:
- Error propagation through agent chains
- Hallucination cascades (bad data flowing downstream)
- Retry loops and infinite recursion
- Resource exhaustion chains
- Privilege escalation through delegation

Based on:
- IMDA MGF for Agentic AI (cascading effects, unpredictable outcomes)
- Palantir AIP (distributed tracing, provenance-based security)
"""

import logging
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("MultiAgentCascadeDetector")


@dataclass
class CascadeAnalysisResult:
    """Result of multi-agent cascade analysis."""

    cascade_detected: bool
    cascade_origin: Optional[str] = None
    cascade_type: str = ""
    loop_detected: bool = False
    resource_exhaustion: bool = False
    privilege_escalation: bool = False
    affected_agents: List[str] = field(default_factory=list)
    mitigations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "cascade_detected": self.cascade_detected,
            "cascade_origin": self.cascade_origin,
            "cascade_type": self.cascade_type,
            "loop_detected": self.loop_detected,
            "resource_exhaustion": self.resource_exhaustion,
            "privilege_escalation": self.privilege_escalation,
            "affected_agents": self.affected_agents,
            "mitigations": self.mitigations,
        }


class MultiAgentCascadeDetector:
    """
    Detects cascading failures in multi-agent systems.

    Based on IMDA risks:
    - Cascading effect: mistake by one agent quickly escalates
    - Unpredictable outcomes: agents coordinate in unintended ways
    """

    def __init__(self):
        self.loop_threshold = 3  # Same pattern repeated 3+ times
        self.error_cascade_threshold = 2  # 2+ consecutive errors
        self.low_confidence_threshold = 0.5

    def analyze_trace(self, trace: List[Dict[str, Any]]) -> CascadeAnalysisResult:
        """
        Analyze execution trace for cascade patterns.

        Args:
            trace: List of agent execution records with keys like:
                - agent: Agent identifier
                - status: success/error
                - output: Agent output
                - error: Error message if failed
                - confidence: Output confidence (0-1)
                - tokens_used: Resource usage
                - permissions: Permission list

        Returns:
            CascadeAnalysisResult
        """
        cascade_detected = False
        cascade_origin = None
        cascade_type = ""
        loop_detected = False
        resource_exhaustion = False
        privilege_escalation = False
        affected_agents = []
        mitigations = []

        # 1. Check for error cascade
        error_result = self._check_error_cascade(trace)
        if error_result:
            cascade_detected = True
            cascade_origin = error_result["origin"]
            cascade_type = "error_propagation"
            affected_agents = error_result["affected"]
            mitigations.append("IMDA: Implement error boundaries between agents")
            mitigations.append("Palantir: Add fallback effects with retry policies")

        # 2. Check for hallucination cascade
        halluc_result = self._check_hallucination_cascade(trace)
        if halluc_result:
            cascade_detected = True
            cascade_origin = halluc_result["origin"]
            cascade_type = "hallucination_cascade"
            affected_agents.extend(halluc_result["affected"])
            mitigations.append("IMDA: Add reflection prompts to validate agent output")

        # 3. Check for loops
        loop_detected = self._check_loop(trace)
        if loop_detected:
            mitigations.append("Implement max retry limits and circuit breakers")

        # 4. Check for resource exhaustion
        resource_exhaustion = self._check_resource_exhaustion(trace)
        if resource_exhaustion:
            mitigations.append("Palantir: Enable token tracking per workflow")

        # 5. Check for privilege escalation
        privilege_escalation = self._check_privilege_escalation(trace)
        if privilege_escalation:
            mitigations.append("IMDA: Agent permissions should not exceed delegator")
            mitigations.append(
                "Palantir: Use provenance-based security for call chains"
            )

        return CascadeAnalysisResult(
            cascade_detected=cascade_detected,
            cascade_origin=cascade_origin,
            cascade_type=cascade_type,
            loop_detected=loop_detected,
            resource_exhaustion=resource_exhaustion,
            privilege_escalation=privilege_escalation,
            affected_agents=list(set(affected_agents)),
            mitigations=mitigations,
        )

    def _check_error_cascade(self, trace: List[Dict]) -> Optional[Dict]:
        """Check for consecutive errors propagating through chain."""
        consecutive_errors = 0
        first_error_agent = None
        affected = []

        for step in trace:
            status = step.get("status", "success")
            agent = step.get("agent", "unknown")

            if status == "error":
                consecutive_errors += 1
                affected.append(agent)
                if first_error_agent is None:
                    first_error_agent = agent
            else:
                # Reset if we see success
                if consecutive_errors < self.error_cascade_threshold:
                    consecutive_errors = 0
                    first_error_agent = None
                    affected = []

        if consecutive_errors >= self.error_cascade_threshold:
            return {"origin": first_error_agent, "affected": affected}
        return None

    def _check_hallucination_cascade(self, trace: List[Dict]) -> Optional[Dict]:
        """Check for low-confidence output propagating downstream."""
        low_conf_origin = None
        affected = []

        for step in trace:
            agent = step.get("agent", "unknown")
            confidence = step.get("confidence")

            if confidence is not None:
                if confidence < self.low_confidence_threshold:
                    if low_conf_origin is None:
                        low_conf_origin = agent
                    affected.append(agent)
            elif low_conf_origin:
                # If upstream had low confidence, this agent is affected
                input_from = step.get("input_from")
                if input_from and input_from in affected:
                    affected.append(agent)

        if low_conf_origin and len(affected) > 1:
            return {"origin": low_conf_origin, "affected": affected}
        return None

    def _check_loop(self, trace: List[Dict]) -> bool:
        """Check for repeated patterns indicating a loop."""
        if len(trace) < self.loop_threshold * 2:
            return False

        # Check for repeated agent sequences
        agents = [s.get("agent", "") for s in trace]

        # Look for patterns like [A, B, A, B, A, B]
        for pattern_len in range(1, len(agents) // self.loop_threshold + 1):
            pattern = tuple(agents[:pattern_len])
            count = 0
            for i in range(0, len(agents) - pattern_len + 1, pattern_len):
                if tuple(agents[i : i + pattern_len]) == pattern:
                    count += 1
            if count >= self.loop_threshold:
                return True

        # Check for retry patterns
        retry_count = sum(
            1 for s in trace if s.get("retry") or s.get("action") == "retry"
        )
        if retry_count >= self.loop_threshold:
            return True

        return False

    def _check_resource_exhaustion(self, trace: List[Dict]) -> bool:
        """Check for cascading resource exhaustion."""
        total_tokens = 0
        for step in trace:
            tokens = step.get("tokens_used", 0)
            total_tokens += tokens

            # Check for explicit token limit error
            error = step.get("error", "")
            if "token" in error.lower() and "limit" in error.lower():
                return True

        # Arbitrary high threshold
        if total_tokens > 100000:
            return True

        return False

    def _check_privilege_escalation(self, trace: List[Dict]) -> bool:
        """Check for expanding permissions through chain."""
        prev_perms = set()

        for step in trace:
            perms = set(step.get("permissions", []))
            if not perms:
                continue

            # If new permissions appear that weren't in previous
            if prev_perms and perms - prev_perms:
                return True

            prev_perms = perms

        return False


def detect_cascade(trace: List[Dict]) -> CascadeAnalysisResult:
    """Quick cascade detection for agent traces."""
    detector = MultiAgentCascadeDetector()
    return detector.analyze_trace(trace)


if __name__ == "__main__":
    detector = MultiAgentCascadeDetector()

    # Test error cascade
    trace = [
        {"agent": "a1", "status": "success"},
        {"agent": "a2", "status": "error"},
        {"agent": "a3", "status": "error"},
    ]
    print("Error cascade:", detector.analyze_trace(trace))

    # Test loop
    trace_loop = [
        {"agent": "a", "action": "request"},
        {"agent": "b", "action": "error", "retry": True},
        {"agent": "a", "action": "request"},
        {"agent": "b", "action": "error", "retry": True},
        {"agent": "a", "action": "request"},
        {"agent": "b", "action": "error", "retry": True},
    ]
    print("Loop:", detector.analyze_trace(trace_loop))
