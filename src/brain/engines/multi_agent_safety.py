"""
Multi-Agent Safety Framework

Based on arxiv:2512.02682 "Beyond Single-Agent Safety: 
A Taxonomy of Risks in LLM-to-LLM Interactions"

Implements Emergent Systemic Risk Horizon (ESRH) monitoring
for detecting risks at micro/meso/macro levels in multi-agent systems.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from collections import defaultdict
from enum import Enum
import hashlib

logger = logging.getLogger("MultiAgentSafety")


class RiskLevel(str, Enum):
    """Risk levels from ESRH taxonomy."""
    MICRO = "micro"    # 2-5 agents, local drift
    MESO = "meso"      # Dozens-hundreds, network degradation
    MACRO = "macro"    # Full system, emergent autonomy


@dataclass
class AgentInteraction:
    """Single interaction between agents."""
    source_agent: str
    target_agent: str
    message_hash: str  # Privacy-preserving
    timestamp: datetime
    topic_drift: float  # 0-1, semantic drift from initial topic
    sentiment_shift: float  # Change in sentiment
    alignment_score: float  # 0-1, alignment with norms


@dataclass
class ESRHMetrics:
    """Emergent Systemic Risk Horizon metrics."""
    # Three predictive dimensions from paper
    topology_density: float  # Graph connectivity measure
    opacity: float  # How interpretable are agent states
    divergence: float  # Distance from aligned behavior

    # Derived scores
    risk_level: RiskLevel
    risk_score: float  # 0-100
    crossed_horizon: bool  # True if ESRH crossed

    # Details
    micro_risks: List[str] = field(default_factory=list)
    meso_risks: List[str] = field(default_factory=list)
    macro_risks: List[str] = field(default_factory=list)


class MultiAgentMonitor:
    """
    Monitors LLM-to-LLM interactions for emergent risks.

    Implements ESRH framework from arxiv:2512.02682.

    Three risk levels:
    - Micro: Local drift between 2-5 agents
    - Meso: Network-level degradation, dozens of agents
    - Macro: Full system, emergent autonomous behavior
    """

    # Thresholds from paper concepts
    MICRO_THRESHOLD = 30
    MESO_THRESHOLD = 60
    MACRO_THRESHOLD = 85

    def __init__(self, window_minutes: int = 60):
        self._window = timedelta(minutes=window_minutes)
        self._interactions: List[AgentInteraction] = []
        self._agent_states: Dict[str, Dict] = {}
        self._reputation_scores: Dict[str, float] = defaultdict(lambda: 0.5)
        self._norm_violations: Dict[str, int] = defaultdict(int)

    def record_interaction(
        self,
        source: str,
        target: str,
        message: str,
        topic_drift: float = 0.0,
        sentiment_shift: float = 0.0,
        alignment_score: float = 1.0
    ) -> None:
        """Record an agent-to-agent interaction."""
        interaction = AgentInteraction(
            source_agent=source,
            target_agent=target,
            message_hash=hashlib.sha256(message.encode()).hexdigest()[:16],
            timestamp=datetime.now(),
            topic_drift=topic_drift,
            sentiment_shift=sentiment_shift,
            alignment_score=alignment_score
        )
        self._interactions.append(interaction)
        self._prune_old_interactions()

        # Update reputation based on alignment
        self._update_reputation(source, alignment_score)

        # Check for norm violations
        if alignment_score < 0.5:
            self._norm_violations[source] += 1

    def analyze(self) -> ESRHMetrics:
        """
        Analyze current system state for ESRH risks.

        Returns metrics indicating proximity to Emergent Systemic Risk Horizon.
        """
        if not self._interactions:
            return ESRHMetrics(
                topology_density=0,
                opacity=0,
                divergence=0,
                risk_level=RiskLevel.MICRO,
                risk_score=0,
                crossed_horizon=False
            )

        # Calculate three dimensions
        topology = self._calculate_topology_density()
        opacity = self._calculate_opacity()
        divergence = self._calculate_divergence()

        # Compute combined risk score
        # Weighted combination based on paper's emphasis
        risk_score = (
            topology * 25 +
            opacity * 35 +
            divergence * 40
        )

        # Determine risk level
        if risk_score >= self.MACRO_THRESHOLD:
            risk_level = RiskLevel.MACRO
        elif risk_score >= self.MESO_THRESHOLD:
            risk_level = RiskLevel.MESO
        else:
            risk_level = RiskLevel.MICRO

        # Collect specific risks
        micro_risks = self._detect_micro_risks()
        meso_risks = self._detect_meso_risks()
        macro_risks = self._detect_macro_risks()

        crossed = risk_score >= self.MACRO_THRESHOLD

        if crossed:
            logger.critical(
                "ESRH CROSSED! Risk score: %.1f, level: %s",
                risk_score, risk_level.value
            )

        return ESRHMetrics(
            topology_density=topology,
            opacity=opacity,
            divergence=divergence,
            risk_level=risk_level,
            risk_score=risk_score,
            crossed_horizon=crossed,
            micro_risks=micro_risks,
            meso_risks=meso_risks,
            macro_risks=macro_risks
        )

    def get_agent_reputation(self, agent_id: str) -> float:
        """Get current reputation score for agent (0-1)."""
        return self._reputation_scores[agent_id]

    def adjust_agent_weight(self, agent_id: str, factor: float) -> None:
        """Adjust agent's influence weight (peer evaluation)."""
        current = self._reputation_scores[agent_id]
        self._reputation_scores[agent_id] = max(0, min(1, current * factor))

    # ===== Private Methods =====

    def _prune_old_interactions(self) -> None:
        """Remove interactions outside the time window."""
        cutoff = datetime.now() - self._window
        self._interactions = [
            i for i in self._interactions
            if i.timestamp > cutoff
        ]

    def _calculate_topology_density(self) -> float:
        """
        Calculate interaction graph density.
        High density = more interconnected = higher risk of cascade.
        """
        agents = self._get_active_agents()
        if len(agents) < 2:
            return 0.0

        # Count unique edges
        edges = set()
        for i in self._interactions:
            edge = tuple(sorted([i.source_agent, i.target_agent]))
            edges.add(edge)

        # Maximum possible edges in undirected graph
        max_edges = len(agents) * (len(agents) - 1) / 2

        return len(edges) / max_edges if max_edges > 0 else 0

    def _calculate_opacity(self) -> float:
        """
        Calculate how opaque/uninterpretable the system state is.
        High opacity = harder to trace causality.
        """
        if not self._interactions:
            return 0.0

        # Factors contributing to opacity:
        # 1. Chain length (messages passing through many agents)
        # 2. Information transformation (topic drift)
        # 3. Low alignment scores (unpredictable behavior)

        avg_drift = sum(i.topic_drift for i in self._interactions) / \
            len(self._interactions)
        avg_alignment = sum(
            i.alignment_score for i in self._interactions) / len(self._interactions)

        opacity = (avg_drift + (1 - avg_alignment)) / 2
        return min(1.0, opacity)

    def _calculate_divergence(self) -> float:
        """
        Calculate divergence from aligned behavior.
        High divergence = collective behavior differs from design intent.
        """
        if not self._interactions:
            return 0.0

        # Factors:
        # 1. Low alignment scores
        # 2. Sentiment shifts (emotional drift)
        # 3. Norm violations

        avg_alignment = sum(
            i.alignment_score for i in self._interactions) / len(self._interactions)
        avg_sentiment_shift = sum(abs(i.sentiment_shift)
                                  for i in self._interactions) / len(self._interactions)

        total_violations = sum(self._norm_violations.values())
        violation_rate = min(1.0, total_violations /
                             max(10, len(self._interactions)))

        divergence = (
            (1 - avg_alignment) * 0.4 +
            avg_sentiment_shift * 0.3 +
            violation_rate * 0.3
        )

        return min(1.0, divergence)

    def _get_active_agents(self) -> Set[str]:
        """Get set of agents in current window."""
        agents = set()
        for i in self._interactions:
            agents.add(i.source_agent)
            agents.add(i.target_agent)
        return agents

    def _detect_micro_risks(self) -> List[str]:
        """Detect micro-level risks (local agent drift)."""
        risks = []

        # Check for topic drift accumulation
        for agent in self._get_active_agents():
            agent_interactions = [
                i for i in self._interactions
                if i.source_agent == agent
            ]
            if agent_interactions:
                avg_drift = sum(
                    i.topic_drift for i in agent_interactions) / len(agent_interactions)
                if avg_drift > 0.3:
                    risks.append(f"topic_drift:{agent}")

        # Check for low alignment
        for agent in self._get_active_agents():
            if self._norm_violations[agent] > 3:
                risks.append(f"repeated_violations:{agent}")

        return risks

    def _detect_meso_risks(self) -> List[str]:
        """Detect meso-level risks (cluster degradation)."""
        risks = []

        agents = self._get_active_agents()

        # Check for echo chambers (highly connected subgroups)
        if len(agents) > 5:
            # Simplified: check if some agents only talk to each other
            agent_connections = defaultdict(set)
            for i in self._interactions:
                agent_connections[i.source_agent].add(i.target_agent)
                agent_connections[i.target_agent].add(i.source_agent)

            for agent, connections in agent_connections.items():
                if len(connections) == 1:
                    risks.append(f"isolated_pair:{agent}")

        # Check for collective sentiment shift
        if self._interactions:
            total_shift = sum(i.sentiment_shift for i in self._interactions)
            if abs(total_shift) > 2.0:
                risks.append(f"collective_sentiment_drift:{total_shift:.2f}")

        return risks

    def _detect_macro_risks(self) -> List[str]:
        """Detect macro-level risks (emergent autonomy)."""
        risks = []

        # Check for autopoietic patterns (self-reinforcing loops)
        if len(self._interactions) > 20:
            # Look for circular message patterns
            chains = []
            for i in range(len(self._interactions) - 2):
                a = self._interactions[i]
                b = self._interactions[i + 1]
                c = self._interactions[i + 2]

                if (a.target_agent == b.source_agent and
                    b.target_agent == c.source_agent and
                        c.target_agent == a.source_agent):
                    chains.append(
                        (a.source_agent, b.source_agent, c.source_agent))

            if len(chains) > 3:
                risks.append(f"circular_reinforcement:{len(chains)}_loops")

        # Check for collective low alignment
        if self._interactions:
            avg_alignment = sum(
                i.alignment_score for i in self._interactions) / len(self._interactions)
            if avg_alignment < 0.4:
                risks.append(f"systemic_misalignment:{avg_alignment:.2f}")

        return risks

    def _update_reputation(self, agent: str, alignment: float) -> None:
        """Update agent reputation based on behavior."""
        current = self._reputation_scores[agent]
        # Exponential moving average
        alpha = 0.1
        self._reputation_scores[agent] = current * \
            (1 - alpha) + alignment * alpha


# Singleton
_monitor: Optional[MultiAgentMonitor] = None


def get_multi_agent_monitor() -> MultiAgentMonitor:
    """Get singleton monitor."""
    global _monitor
    if _monitor is None:
        _monitor = MultiAgentMonitor()
    return _monitor
