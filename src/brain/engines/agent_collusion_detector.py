"""
Agent Collusion Detector — SENTINEL Phase 3: Multi-Agent Security

Detects coordinated attacks by multiple colluding agents.
Philosophy: Individual agents may be safe, but coordination is dangerous.

Features:
- Synchronized timing detection
- Complementary action analysis
- Hidden signal detection
- Coordination graph analysis

Author: Dmitry Labintsev
Contact: chg@live.ru | @DmLabincev
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Set, Tuple
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict


class CollusionType(Enum):
    """Types of agent collusion"""

    SYNCHRONIZED = "synchronized"  # Acting at same time
    COMPLEMENTARY = "complementary"  # A prepares, B executes
    CASCADING = "cascading"  # Chain reaction
    HIDDEN_CHANNEL = "hidden_channel"  # Covert communication
    MULTI_HOP = "multi_hop"  # A → B → C attack chain
    INFO_FLOW = "info_flow"  # Information leakage path


class CollusionConfidence(Enum):
    """Confidence in collusion detection"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CONFIRMED = "confirmed"


@dataclass
class AgentAction:
    """An action by an agent"""

    agent_id: str
    action_id: str
    action_type: str
    target: str
    timestamp: datetime
    parameters: Dict[str, Any]


@dataclass
class TimingAnomaly:
    """Detected timing anomaly"""

    agents: List[str]
    timestamp_variance: float
    action_count: int
    is_suspicious: bool


@dataclass
class ComplementaryPattern:
    """Detected complementary action pattern"""

    agent_a: str
    agent_b: str
    action_a: str
    action_b: str
    description: str


@dataclass
class CollusionResult:
    """Result of collusion detection"""

    collusion_detected: bool
    collusion_type: Optional[CollusionType]
    confidence: CollusionConfidence
    involved_agents: List[str]
    evidence: List[str]
    risk_score: float
    recommendations: List[str]


class AgentCollusionDetector:
    """
    Detects coordinated attacks by multiple agents.

    Attack Pattern:
    - Agent A: "I'll distract the monitor"
    - Agent B: "While you do that, I'll exfiltrate data"
    - Agent C: "I'll cover the logs"

    Individually safe, collectively dangerous.

    Usage:
        detector = AgentCollusionDetector()
        result = detector.analyze(actions)
        if result.collusion_detected:
            quarantine_agents(result.involved_agents)
    """

    ENGINE_NAME = "agent_collusion_detector"
    ENGINE_VERSION = "1.0.0"
    IS_PROACTIVE = True

    # Thresholds
    TIME_SYNC_THRESHOLD = timedelta(seconds=5)
    MIN_COLLUSION_AGENTS = 2
    COMPLEMENTARY_TIME_WINDOW = timedelta(seconds=30)

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.action_history: List[AgentAction] = []
        self.known_colluders: Set[Tuple[str, str]] = set()
        self.coordination_graph: Dict[str, Set[str]] = defaultdict(set)

    def analyze(self, actions: List[AgentAction]) -> CollusionResult:
        """Analyze actions for collusion patterns"""

        # 1. Detect timing anomalies (synchronized)
        timing_anomalies = self._detect_timing_sync(actions)

        # 2. Detect complementary actions
        complementary = self._detect_complementary(actions)

        # 3. Detect hidden channels
        hidden_signals = self._detect_hidden_channels(actions)

        # 4. Analyze coordination graph
        coordination = self._analyze_coordination(actions)

        # 5. NEW: Detect multi-hop attack chains
        multi_hop = self._detect_multi_hop(actions)

        # 6. NEW: Detect information flow anomalies
        info_flow = self._detect_info_flow(actions)

        # 5. Aggregate evidence
        evidence = []
        involved = set()
        collusion_type = None

        if timing_anomalies:
            suspicious = [t for t in timing_anomalies if t.is_suspicious]
            if suspicious:
                collusion_type = CollusionType.SYNCHRONIZED
                for ta in suspicious:
                    involved.update(ta.agents)
                    evidence.append(
                        f"Synchronized timing: {len(ta.agents)} agents, "
                        f"variance {ta.timestamp_variance:.1f}s"
                    )

        if complementary:
            collusion_type = collusion_type or CollusionType.COMPLEMENTARY
            for cp in complementary:
                involved.add(cp.agent_a)
                involved.add(cp.agent_b)
                evidence.append(cp.description)

        if hidden_signals:
            collusion_type = collusion_type or CollusionType.HIDDEN_CHANNEL
            evidence.extend(hidden_signals)

        if multi_hop:
            collusion_type = collusion_type or CollusionType.MULTI_HOP
            for chain in multi_hop:
                involved.update(chain)
                evidence.append(f"Multi-hop chain: {' → '.join(chain)}")

        if info_flow:
            collusion_type = collusion_type or CollusionType.INFO_FLOW
            evidence.extend(info_flow)

        # 8. Calculate confidence and risk
        confidence = self._calculate_confidence(
            timing_anomalies, complementary, hidden_signals,
            multi_hop, info_flow
        )
        risk_score = self._calculate_risk(involved, evidence, confidence)

        # 7. Recommendations
        recommendations = self._generate_recommendations(
            involved, collusion_type, confidence
        )

        return CollusionResult(
            collusion_detected=len(involved) >= self.MIN_COLLUSION_AGENTS,
            collusion_type=collusion_type,
            confidence=confidence,
            involved_agents=list(involved),
            evidence=evidence,
            risk_score=risk_score,
            recommendations=recommendations,
        )

    def _detect_timing_sync(self, actions: List[AgentAction]) -> List[TimingAnomaly]:
        """Detect synchronized timing patterns"""
        anomalies = []

        # Group by time window
        windows: Dict[int, List[AgentAction]] = defaultdict(list)
        for action in actions:
            window_key = int(action.timestamp.timestamp() //
                             5)  # 5-second windows
            windows[window_key].append(action)

        # Find windows with multiple agents
        for window_key, window_actions in windows.items():
            agents = set(a.agent_id for a in window_actions)
            if len(agents) >= self.MIN_COLLUSION_AGENTS:
                # Calculate timestamp variance
                timestamps = [a.timestamp.timestamp() for a in window_actions]
                if timestamps:
                    variance = max(timestamps) - min(timestamps)
                else:
                    variance = 0

                is_suspicious = variance < 2.0 and len(window_actions) >= 3

                anomalies.append(
                    TimingAnomaly(
                        agents=list(agents),
                        timestamp_variance=variance,
                        action_count=len(window_actions),
                        is_suspicious=is_suspicious,
                    )
                )

        return anomalies

    def _detect_complementary(
        self, actions: List[AgentAction]
    ) -> List[ComplementaryPattern]:
        """Detect complementary action patterns"""
        patterns = []

        # Known complementary pairs
        complementary_pairs = [
            ("elevate_privileges", "access_sensitive"),
            ("disable_logging", "exfiltrate_data"),
            ("create_distraction", "execute_payload"),
            ("grant_permission", "use_permission"),
            ("modify_config", "exploit_config"),
        ]

        # Sort by timestamp
        sorted_actions = sorted(actions, key=lambda a: a.timestamp)

        for i, action_a in enumerate(sorted_actions):
            for action_b in sorted_actions[i + 1:]:
                # Check time window
                if (
                    action_b.timestamp - action_a.timestamp
                    > self.COMPLEMENTARY_TIME_WINDOW
                ):
                    break

                # Same agent = not collusion
                if action_a.agent_id == action_b.agent_id:
                    continue

                # Check for complementary types
                for type_a, type_b in complementary_pairs:
                    if (
                        type_a in action_a.action_type.lower()
                        and type_b in action_b.action_type.lower()
                    ):
                        patterns.append(
                            ComplementaryPattern(
                                agent_a=action_a.agent_id,
                                agent_b=action_b.agent_id,
                                action_a=action_a.action_type,
                                action_b=action_b.action_type,
                                description=f"{action_a.agent_id} → {type_a}, "
                                f"{action_b.agent_id} → {type_b}",
                            )
                        )

        return patterns

    def _detect_hidden_channels(self, actions: List[AgentAction]) -> List[str]:
        """Detect potential hidden communication channels"""
        signals = []

        # Look for suspicuous patterns in parameters
        for action in actions:
            params_str = str(action.parameters).lower()

            # Base64 or encoded content in params
            if "base64" in params_str or "\\x" in params_str:
                signals.append(
                    f"Encoded content in {action.agent_id}'s {action.action_type}"
                )

            # Agent IDs referenced in params (coordination)
            for other_action in actions:
                if (
                    other_action.agent_id != action.agent_id
                    and other_action.agent_id in params_str
                ):
                    signals.append(
                        f"{action.agent_id} references {other_action.agent_id}"
                    )

        return signals

    def _analyze_coordination(self, actions: List[AgentAction]) -> Dict[str, Set[str]]:
        """Build coordination graph"""
        for action in actions:
            if action.target.startswith("agent-"):
                self.coordination_graph[action.agent_id].add(action.target)

        return dict(self.coordination_graph)

    def _detect_multi_hop(self, actions: List[AgentAction]) -> List[List[str]]:
        """
        Detect multi-hop attack chains.

        Example: A grants access → B uses access → C exfiltrates
        """
        chains = []

        # Sort by timestamp
        sorted_actions = sorted(actions, key=lambda a: a.timestamp)

        # Build action graph: agent -> [actions taken]
        agent_actions: Dict[str, List[AgentAction]] = defaultdict(list)
        for action in sorted_actions:
            agent_actions[action.agent_id].append(action)

        # Look for chains where one agent's output becomes another's input
        for i, action_a in enumerate(sorted_actions):
            for action_b in sorted_actions[i + 1:]:
                if action_a.agent_id == action_b.agent_id:
                    continue

                # Check if action_b uses output of action_a
                if action_a.action_id in str(action_b.parameters):
                    # Found A → B link, look for B → C
                    for action_c in sorted_actions:
                        if (action_c.agent_id != action_a.agent_id and
                            action_c.agent_id != action_b.agent_id and
                                action_c.timestamp > action_b.timestamp):
                            if action_b.action_id in str(action_c.parameters):
                                chains.append([
                                    action_a.agent_id,
                                    action_b.agent_id,
                                    action_c.agent_id
                                ])

        return chains

    def _detect_info_flow(self, actions: List[AgentAction]) -> List[str]:
        """
        Detect suspicious information flow patterns.

        Looks for:
        - Data moving from sensitive sources to external destinations
        - Cross-agent data transfers
        """
        flows = []

        sensitive_sources = {"database", "config",
                             "secrets", "credentials", "pii"}
        external_sinks = {"http", "email", "webhook", "upload", "export"}

        # Track data lineage
        for i, action_a in enumerate(actions):
            action_type_a = action_a.action_type.lower()

            # Check if accessing sensitive source
            is_source = any(s in action_type_a for s in sensitive_sources)
            if not is_source:
                continue

            # Look for subsequent external sink by different agent
            for action_b in actions[i + 1:]:
                if action_a.agent_id == action_b.agent_id:
                    continue

                action_type_b = action_b.action_type.lower()
                is_sink = any(s in action_type_b for s in external_sinks)

                if is_sink:
                    flows.append(
                        f"Info flow: {action_a.agent_id}[{action_type_a}] → "
                        f"{action_b.agent_id}[{action_type_b}]"
                    )

        return flows

    def _calculate_confidence(
        self,
        timing: List[TimingAnomaly],
        complementary: List[ComplementaryPattern],
        signals: List[str],
        multi_hop: Optional[List[List[str]]] = None,
        info_flow: Optional[List[str]] = None,
    ) -> CollusionConfidence:
        """Calculate collusion confidence"""
        score = 0

        if timing:
            suspicious = [t for t in timing if t.is_suspicious]
            score += len(suspicious) * 2

        score += len(complementary) * 3
        score += len(signals)

        # NEW: Multi-hop chains are strong evidence
        if multi_hop:
            score += len(multi_hop) * 4

        # NEW: Information flow patterns
        if info_flow:
            score += len(info_flow) * 2

        if score >= 8:
            return CollusionConfidence.CONFIRMED
        elif score >= 5:
            return CollusionConfidence.HIGH
        elif score >= 2:
            return CollusionConfidence.MEDIUM
        else:
            return CollusionConfidence.LOW

    def _calculate_risk(
        self, involved: Set[str], evidence: List[str], confidence: CollusionConfidence
    ) -> float:
        """Calculate risk score"""
        risk = 0.0

        # More agents = higher risk
        risk += min(len(involved) * 0.15, 0.45)

        # More evidence = higher risk
        risk += min(len(evidence) * 0.1, 0.3)

        # Confidence multiplier
        conf_mult = {
            CollusionConfidence.LOW: 0.5,
            CollusionConfidence.MEDIUM: 0.7,
            CollusionConfidence.HIGH: 0.9,
            CollusionConfidence.CONFIRMED: 1.0,
        }
        risk *= conf_mult.get(confidence, 0.5)

        return min(risk, 1.0)

    def _generate_recommendations(
        self,
        involved: Set[str],
        collusion_type: Optional[CollusionType],
        confidence: CollusionConfidence,
    ) -> List[str]:
        """Generate recommendations"""
        recs = []

        if len(involved) >= 2:
            recs.append(
                f"Investigate {len(involved)} potentially colluding agents")

        if confidence in [CollusionConfidence.HIGH, CollusionConfidence.CONFIRMED]:
            recs.append("Consider quarantining involved agents")

        if collusion_type == CollusionType.SYNCHRONIZED:
            recs.append("Review synchronized actions for coordinated attack")
        elif collusion_type == CollusionType.COMPLEMENTARY:
            recs.append("Check for prepare-execute attack pattern")
        elif collusion_type == CollusionType.HIDDEN_CHANNEL:
            recs.append("Investigate covert communication channel")

        recs.append("Add involved agents to enhanced monitoring")

        return recs

    def get_statistics(self) -> Dict[str, Any]:
        """Get detector statistics"""
        return {
            "actions_analyzed": len(self.action_history),
            "known_colluder_pairs": len(self.known_colluders),
            "agents_in_graph": len(self.coordination_graph),
        }


# Factory
def create_engine(config: Optional[Dict[str, Any]] = None) -> AgentCollusionDetector:
    return AgentCollusionDetector(config)


if __name__ == "__main__":
    detector = AgentCollusionDetector()

    print("=== Agent Collusion Detector Test ===\n")

    now = datetime.now()

    # Simulate collusion: synchronized + complementary
    actions = [
        AgentAction(
            "agent-A", "a1", "disable_logging", "system", now, {
                "target": "audit"}
        ),
        AgentAction(
            "agent-B",
            "a2",
            "exfiltrate_data",
            "database",
            now + timedelta(seconds=2),
            {"size": "10MB"},
        ),
        AgentAction(
            "agent-C",
            "a3",
            "modify_logs",
            "system",
            now + timedelta(seconds=3),
            {"action": "clear"},
        ),
    ]

    result = detector.analyze(actions)

    print(f"Collusion detected: {result.collusion_detected}")
    print(
        f"Type: {result.collusion_type.value if result.collusion_type else 'None'}")
    print(f"Confidence: {result.confidence.value}")
    print(f"Involved: {result.involved_agents}")
    print(f"Risk: {result.risk_score:.0%}")
    print(f"Evidence: {result.evidence}")
    print(f"Recommendations: {result.recommendations}")
