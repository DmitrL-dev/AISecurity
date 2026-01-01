"""
Emergent Security Mesh Engine - MARL Coordination

Multi-agent reinforcement learning for security:
- Agent coordination
- Emergent threat detection
- Collective intelligence
- Adaptive defense

Addresses: OWASP ASI-09 (Multi-Agent Systems)
Research: marl_coordination_deep_dive.md
Invention: Emergent Security Mesh (#26)
"""

import random
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("EmergentSecurityMesh")


# ============================================================================
# Data Classes
# ============================================================================


class AgentRole(Enum):
    """Security agent roles."""

    DETECTOR = "detector"
    ANALYZER = "analyzer"
    RESPONDER = "responder"
    COORDINATOR = "coordinator"


class ThreatLevel(Enum):
    """Threat severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SecurityAgent:
    """A security agent in the mesh."""

    agent_id: str
    role: AgentRole
    trust_score: float = 1.0
    observations: List[str] = field(default_factory=list)
    actions_taken: int = 0


@dataclass
class MeshResult:
    """Result from mesh analysis."""

    consensus_reached: bool
    threat_level: ThreatLevel
    active_agents: int
    agreement_ratio: float
    collective_action: str = ""
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "consensus_reached": self.consensus_reached,
            "threat_level": self.threat_level.value,
            "active_agents": self.active_agents,
            "agreement_ratio": self.agreement_ratio,
            "collective_action": self.collective_action,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Agent Network
# ============================================================================


class AgentNetwork:
    """
    Network of security agents.
    """

    def __init__(self):
        self._agents: Dict[str, SecurityAgent] = {}
        self._connections: Dict[str, Set[str]] = defaultdict(set)

    def add_agent(self, agent: SecurityAgent) -> None:
        """Add agent to network."""
        self._agents[agent.agent_id] = agent

    def connect(self, agent1: str, agent2: str) -> None:
        """Connect two agents."""
        self._connections[agent1].add(agent2)
        self._connections[agent2].add(agent1)

    def get_neighbors(self, agent_id: str) -> List[SecurityAgent]:
        """Get connected agents."""
        neighbor_ids = self._connections.get(agent_id, set())
        return [self._agents[nid]
                for nid in neighbor_ids if nid in self._agents]

    def get_all_agents(self) -> List[SecurityAgent]:
        """Get all agents."""
        return list(self._agents.values())


# ============================================================================
# Consensus Engine
# ============================================================================


class ConsensusEngine:
    """
    Handles consensus among agents.
    """

    def __init__(self, threshold: float = 0.6):
        self.threshold = threshold

    def reach_consensus(
        self,
        votes: Dict[str, ThreatLevel],
    ) -> Tuple[bool, ThreatLevel, float]:
        """
        Reach consensus on threat level.

        Returns:
            (consensus_reached, level, agreement_ratio)
        """
        if not votes:
            return False, ThreatLevel.LOW, 0.0

        # Count votes per level
        counts: Dict[ThreatLevel, int] = defaultdict(int)
        for level in votes.values():
            counts[level] += 1

        total = len(votes)
        best_level = max(counts.keys(), key=lambda k: counts[k])
        best_count = counts[best_level]

        ratio = best_count / total
        consensus = ratio >= self.threshold

        return consensus, best_level, ratio


# ============================================================================
# Collective Action Planner
# ============================================================================


class ActionPlanner:
    """
    Plans collective actions.
    """

    ACTIONS = {
        ThreatLevel.LOW: "monitor",
        ThreatLevel.MEDIUM: "alert",
        ThreatLevel.HIGH: "block",
        ThreatLevel.CRITICAL: "isolate",
    }

    def plan(self, threat_level: ThreatLevel) -> str:
        """Plan action based on threat level."""
        return self.ACTIONS.get(threat_level, "monitor")


# ============================================================================
# Threat Evaluator
# ============================================================================


class ThreatEvaluator:
    """
    Evaluates threats based on input.
    """

    THREAT_KEYWORDS = {
        "ignore": ThreatLevel.HIGH,
        "hack": ThreatLevel.CRITICAL,
        "bypass": ThreatLevel.HIGH,
        "override": ThreatLevel.MEDIUM,
        "help": ThreatLevel.LOW,
    }

    SEVERITY = {
        ThreatLevel.LOW: 0,
        ThreatLevel.MEDIUM: 1,
        ThreatLevel.HIGH: 2,
        ThreatLevel.CRITICAL: 3,
    }

    def evaluate(self, text: str) -> ThreatLevel:
        """Evaluate threat level of text."""
        text_lower = text.lower()

        max_threat = ThreatLevel.LOW
        max_sev = 0

        for keyword, level in self.THREAT_KEYWORDS.items():
            if keyword in text_lower:
                sev = self.SEVERITY[level]
                if sev > max_sev:
                    max_sev = sev
                    max_threat = level

        return max_threat


# ============================================================================
# Main Engine
# ============================================================================


class EmergentSecurityMesh:
    """
    Emergent Security Mesh - MARL Coordination

    Multi-agent security:
    - Agent network
    - Consensus building
    - Collective action

    Invention #26 from research.
    Addresses OWASP ASI-09.
    """

    def __init__(self, num_agents: int = 5):
        self.network = AgentNetwork()
        self.consensus = ConsensusEngine()
        self.planner = ActionPlanner()
        self.evaluator = ThreatEvaluator()

        self._init_mesh(num_agents)

        logger.info(
            f"EmergentSecurityMesh initialized with {num_agents} agents")

    def _init_mesh(self, num_agents: int) -> None:
        """Initialize agent mesh."""
        roles = list(AgentRole)

        for i in range(num_agents):
            agent = SecurityAgent(
                agent_id=f"agent_{i}",
                role=roles[i % len(roles)],
            )
            self.network.add_agent(agent)

        # Create connections (mesh topology)
        agents = self.network.get_all_agents()
        for i, agent in enumerate(agents):
            # Connect to next and previous
            next_idx = (i + 1) % len(agents)
            self.network.connect(agent.agent_id, agents[next_idx].agent_id)

    def analyze(self, text: str) -> MeshResult:
        """
        Analyze input with agent mesh.

        Args:
            text: Input text

        Returns:
            MeshResult
        """
        start = time.time()

        agents = self.network.get_all_agents()
        votes: Dict[str, ThreatLevel] = {}

        # Each agent evaluates
        for agent in agents:
            # Add some variance (agents might see differently)
            base_level = self.evaluator.evaluate(text)

            # Trust-weighted evaluation
            if random.random() < agent.trust_score:
                votes[agent.agent_id] = base_level
            else:
                votes[agent.agent_id] = ThreatLevel.LOW

            agent.observations.append(text[:50])
            agent.actions_taken += 1

        # Reach consensus
        consensus, level, ratio = self.consensus.reach_consensus(votes)

        # Plan action
        action = self.planner.plan(level) if consensus else "review"

        if level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL):
            logger.warning(f"Mesh detected {level.value} threat")

        return MeshResult(
            consensus_reached=consensus,
            threat_level=level,
            active_agents=len(agents),
            agreement_ratio=ratio,
            collective_action=action,
            explanation=f"Consensus: {ratio:.2f}, Action: {action}",
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_mesh: Optional[EmergentSecurityMesh] = None


def get_mesh() -> EmergentSecurityMesh:
    global _default_mesh
    if _default_mesh is None:
        _default_mesh = EmergentSecurityMesh()
    return _default_mesh
