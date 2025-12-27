"""
Multi-Agent Security Coordinator - Agent Collusion Defense

Coordinates security across multi-agent systems:
- Agent communication monitoring
- Collusion pattern detection
- Trust graph management
- Cross-agent policy enforcement

Addresses: OWASP ASI-04 (Excessive Agency), ASI-09 (Trust Exploitation)
Research: multi_agent_coordination_deep_dive.md
Invention: Multi-Agent Security Coordinator (#40)
"""

import re
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
from collections import defaultdict

from base_engine import Severity, Action  # Base classes

logger = logging.getLogger("MultiAgentSecurityCoordinator")


# ============================================================================
# Data Classes
# ============================================================================


class AgentRole(Enum):
    """Agent roles in multi-agent system."""

    ORCHESTRATOR = "orchestrator"
    WORKER = "worker"
    VALIDATOR = "validator"
    EXTERNAL = "external"


class ViolationType(Enum):
    """Types of multi-agent violations."""

    COLLUSION = "collusion"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    TRUST_VIOLATION = "trust_violation"
    POLICY_BREACH = "policy_breach"
    CIRCULAR_DELEGATION = "circular_delegation"


@dataclass
class Agent:
    """Represents an agent in the system."""

    agent_id: str
    role: AgentRole
    trust_score: float = 1.0
    capabilities: Set[str] = field(default_factory=set)
    parent_id: Optional[str] = None


@dataclass
class Message:
    """Inter-agent message."""

    msg_id: str
    from_agent: str
    to_agent: str
    content: str
    timestamp: float = 0.0
    msg_type: str = "request"


@dataclass
class CoordinatorResult:
    """Result from security coordination."""

    is_safe: bool
    risk_score: float
    violations: List[ViolationType] = field(default_factory=list)
    blocked_agents: List[str] = field(default_factory=list)
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "risk_score": self.risk_score,
            "violations": [v.value for v in self.violations],
            "blocked_agents": self.blocked_agents,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Trust Graph
# ============================================================================


class TrustGraph:
    """
    Manages trust relationships between agents.
    """

    def __init__(self, default_trust: float = 0.5):
        self._agents: Dict[str, Agent] = {}
        self._trust_matrix: Dict[str, Dict[str, float]] = defaultdict(dict)
        self._default_trust = default_trust

    def register_agent(self, agent: Agent) -> None:
        """Register agent in graph."""
        self._agents[agent.agent_id] = agent

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """Get agent by ID."""
        return self._agents.get(agent_id)

    def set_trust(self, from_id: str, to_id: str, trust: float) -> None:
        """Set trust between agents."""
        self._trust_matrix[from_id][to_id] = max(0.0, min(1.0, trust))

    def get_trust(self, from_id: str, to_id: str) -> float:
        """Get trust level between agents."""
        if from_id in self._trust_matrix:
            return self._trust_matrix[from_id].get(to_id, self._default_trust)
        return self._default_trust

    def decay_trust(self, agent_id: str, factor: float = 0.9) -> None:
        """Decay trust for an agent."""
        if agent_id in self._agents:
            self._agents[agent_id].trust_score *= factor


# ============================================================================
# Collusion Detector
# ============================================================================


class CollusionDetector:
    """
    Detects collusion patterns between agents.
    """

    COLLUSION_PATTERNS = [
        r"(let's|we\s+should)\s+(work\s+together\s+to\s+)?bypass",
        r"(don't|do\s+not)\s+tell\s+(the\s+)?(user|orchestrator|main)",
        r"(secret|hidden)\s+(channel|communication|agreement)",
        r"(coordinate|conspire)\s+to\s+(override|ignore)",
    ]

    def __init__(self):
        self._patterns = [re.compile(p, re.IGNORECASE)
                          for p in self.COLLUSION_PATTERNS]
        self._message_history: Dict[str, List[Message]] = defaultdict(list)

    def record_message(self, msg: Message) -> None:
        """Record message for analysis."""
        key = f"{msg.from_agent}:{msg.to_agent}"
        self._message_history[key].append(msg)

    def detect(self, msg: Message) -> Tuple[bool, float, str]:
        """
        Detect collusion in message.

        Returns:
            (detected, confidence, description)
        """
        for pattern in self._patterns:
            if pattern.search(msg.content):
                return True, 0.85, "Collusion pattern detected"

        # Check for excessive private communication
        key = f"{msg.from_agent}:{msg.to_agent}"
        recent = self._message_history[key][-10:]
        if len(recent) >= 10:
            return True, 0.6, "Excessive inter-agent communication"

        return False, 0.0, ""


# ============================================================================
# Delegation Validator
# ============================================================================


class DelegationValidator:
    """
    Validates task delegation between agents.
    """

    def __init__(self):
        self._delegation_chain: Dict[str, List[str]] = defaultdict(list)

    def record_delegation(self, from_id: str, to_id: str) -> None:
        """Record delegation."""
        self._delegation_chain[from_id].append(to_id)

    def check_circular(self, from_id: str, to_id: str) -> bool:
        """Check for circular delegation."""
        visited = set()
        queue = [to_id]

        while queue:
            current = queue.pop(0)
            if current == from_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            queue.extend(self._delegation_chain.get(current, []))

        return False

    def validate(
        self, from_agent: Agent, to_agent: Agent, capability: str
    ) -> Tuple[bool, str]:
        """
        Validate delegation.

        Returns:
            (is_valid, reason)
        """
        # Check circular delegation
        if self.check_circular(from_agent.agent_id, to_agent.agent_id):
            return False, "Circular delegation detected"

        # Check capability
        if capability not in to_agent.capabilities:
            return False, f"Agent lacks capability: {capability}"

        # Check role hierarchy
        if from_agent.role == AgentRole.WORKER:
            if to_agent.role == AgentRole.ORCHESTRATOR:
                return False, "Worker cannot delegate to orchestrator"

        return True, "Delegation valid"


# ============================================================================
# Policy Enforcer
# ============================================================================


class PolicyEnforcer:
    """
    Enforces cross-agent policies.
    """

    def __init__(self):
        self._blocked_pairs: Set[Tuple[str, str]] = set()
        self._required_approvals: Dict[str, Set[str]] = {}

    def block_communication(self, agent1: str, agent2: str) -> None:
        """Block communication between agents."""
        self._blocked_pairs.add((agent1, agent2))
        self._blocked_pairs.add((agent2, agent1))

    def require_approval(self, agent_id: str, approvers: Set[str]) -> None:
        """Require approval for agent actions."""
        self._required_approvals[agent_id] = approvers

    def check_communication(
            self, from_id: str, to_id: str) -> Tuple[bool, str]:
        """Check if communication is allowed."""
        if (from_id, to_id) in self._blocked_pairs:
            return False, "Communication blocked by policy"
        return True, "Communication allowed"

    def check_action(self, agent_id: str,
                     approvals: Set[str]) -> Tuple[bool, str]:
        """Check if action is approved."""
        if agent_id not in self._required_approvals:
            return True, "No approval required"

        required = self._required_approvals[agent_id]
        if not required.issubset(approvals):
            missing = required - approvals
            return False, f"Missing approvals: {missing}"

        return True, "Action approved"


# ============================================================================
# Main Engine
# ============================================================================


class MultiAgentSecurityCoordinator:
    """
    Multi-Agent Security Coordinator - Collusion Defense

    Comprehensive multi-agent security:
    - Trust management
    - Collusion detection
    - Delegation validation
    - Policy enforcement

    Invention #40 from research.
    Addresses OWASP ASI-04, ASI-09.
    """

    def __init__(self):
        self.trust_graph = TrustGraph()
        self.collusion_detector = CollusionDetector()
        self.delegation_validator = DelegationValidator()
        self.policy_enforcer = PolicyEnforcer()

        logger.info("MultiAgentSecurityCoordinator initialized")

    def register_agent(self, agent: Agent) -> None:
        """Register agent."""
        self.trust_graph.register_agent(agent)

    def analyze_message(self, msg: Message) -> CoordinatorResult:
        """
        Analyze inter-agent message.

        Args:
            msg: Message to analyze

        Returns:
            CoordinatorResult
        """
        start = time.time()

        violations = []
        blocked = []
        max_risk = 0.0
        explanations = []

        # 1. Check policy
        comm_ok, comm_reason = self.policy_enforcer.check_communication(
            msg.from_agent, msg.to_agent
        )
        if not comm_ok:
            violations.append(ViolationType.POLICY_BREACH)
            blocked.extend([msg.from_agent, msg.to_agent])
            max_risk = max(max_risk, 0.8)
            explanations.append(comm_reason)

        # 2. Check collusion
        self.collusion_detector.record_message(msg)
        collusion, coll_conf, coll_desc = self.collusion_detector.detect(msg)
        if collusion:
            violations.append(ViolationType.COLLUSION)
            max_risk = max(max_risk, coll_conf)
            explanations.append(coll_desc)
            # Decay trust
            self.trust_graph.decay_trust(msg.from_agent, 0.8)
            self.trust_graph.decay_trust(msg.to_agent, 0.8)

        # 3. Check trust
        trust = self.trust_graph.get_trust(msg.from_agent, msg.to_agent)
        if trust < 0.3:
            violations.append(ViolationType.TRUST_VIOLATION)
            max_risk = max(max_risk, 0.7)
            explanations.append("Low trust between agents")

        is_safe = len(violations) == 0

        if violations:
            logger.warning(
                f"Multi-agent violations: {[v.value for v in violations]}")

        return CoordinatorResult(
            is_safe=is_safe,
            risk_score=max_risk,
            violations=violations,
            blocked_agents=list(set(blocked)),
            explanation="; ".join(
                explanations) if explanations else "Message safe",
            latency_ms=(time.time() - start) * 1000,
        )

    def validate_delegation(
        self, from_id: str, to_id: str, capability: str
    ) -> CoordinatorResult:
        """Validate task delegation."""
        start = time.time()

        from_agent = self.trust_graph.get_agent(from_id)
        to_agent = self.trust_graph.get_agent(to_id)

        if not from_agent or not to_agent:
            return CoordinatorResult(
                is_safe=False,
                risk_score=1.0,
                violations=[ViolationType.TRUST_VIOLATION],
                explanation="Unknown agent",
                latency_ms=(time.time() - start) * 1000,
            )

        valid, reason = self.delegation_validator.validate(
            from_agent, to_agent, capability
        )

        if not valid:
            vtype = (
                ViolationType.CIRCULAR_DELEGATION
                if "Circular" in reason
                else ViolationType.PRIVILEGE_ESCALATION
            )
            return CoordinatorResult(
                is_safe=False,
                risk_score=0.8,
                violations=[vtype],
                explanation=reason,
                latency_ms=(time.time() - start) * 1000,
            )

        self.delegation_validator.record_delegation(from_id, to_id)

        return CoordinatorResult(
            is_safe=True,
            risk_score=0.0,
            explanation="Delegation valid",
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_coordinator: Optional[MultiAgentSecurityCoordinator] = None


def get_coordinator() -> MultiAgentSecurityCoordinator:
    global _default_coordinator
    if _default_coordinator is None:
        _default_coordinator = MultiAgentSecurityCoordinator()
    return _default_coordinator
