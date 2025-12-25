"""
Agent Anomaly Detector — SENTINEL MCP Deep Security

Detects anomalous behavior in AI agents by analyzing:
- Tool call patterns vs baseline
- Timing anomalies
- Resource access patterns
- Behavioral drift

TTPs.ai Coverage:
- AI Agent Behavior Drift
- Tool Abuse Detection
- Session Anomaly Detection

Author: Dmitry Labintsev
Contact: chg@live.ru | @DmLabincev
"""

import logging
import time
from typing import Dict, List, Optional, Set, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import statistics

logger = logging.getLogger("AgentAnomaly")


# ============================================================================
# Data Classes
# ============================================================================


class AnomalyType(Enum):
    """Types of agent anomalies."""

    TOOL_FREQUENCY = "tool_frequency"  # Tool called too often/rarely
    TOOL_SEQUENCE = "tool_sequence"  # Unusual tool sequence
    TIMING_ANOMALY = "timing_anomaly"  # Unusual timing patterns
    RESOURCE_ACCESS = "resource_access"  # Unusual resource access
    BEHAVIOR_DRIFT = "behavior_drift"  # Deviation from baseline
    NEW_CAPABILITY = "new_capability"  # Agent using new capabilities
    SESSION_ANOMALY = "session_anomaly"  # Session-level anomaly


class SeverityLevel(Enum):
    """Anomaly severity levels."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AgentBaseline:
    """Baseline behavioral profile for an agent."""

    agent_id: str
    tool_frequencies: Dict[str, float] = field(
        default_factory=dict)  # tool -> avg calls/session
    tool_sequences: List[Tuple[str, str]] = field(
        default_factory=list)  # Common transitions
    avg_session_duration_ms: float = 0.0
    avg_tools_per_session: float = 0.0
    known_capabilities: Set[str] = field(default_factory=set)
    resource_patterns: Dict[str, int] = field(default_factory=dict)
    sample_count: int = 0
    last_updated: float = 0.0


@dataclass
class AnomalyEvent:
    """A detected anomaly event."""

    anomaly_type: AnomalyType
    severity: SeverityLevel
    description: str
    confidence: float
    evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "type": self.anomaly_type.value,
            "severity": self.severity.value,
            "description": self.description,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }


@dataclass
class AnomalyResult:
    """Result of anomaly detection analysis."""

    is_anomalous: bool
    anomaly_score: float  # 0.0 - 1.0
    max_severity: SeverityLevel
    anomalies: List[AnomalyEvent] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_anomalous": self.is_anomalous,
            "anomaly_score": self.anomaly_score,
            "max_severity": self.max_severity.value,
            "anomaly_count": len(self.anomalies),
            "anomalies": [a.to_dict() for a in self.anomalies[:5]],
            "recommendations": self.recommendations[:3],
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Agent Session Tracker
# ============================================================================


@dataclass
class ToolCallEvent:
    """A tool call event in a session."""

    tool_name: str
    arguments: Dict[str, Any]
    timestamp: float
    duration_ms: float = 0.0


class AgentSession:
    """Tracks an agent's session for anomaly detection."""

    def __init__(self, agent_id: str, session_id: str):
        self.agent_id = agent_id
        self.session_id = session_id
        self.start_time = time.time()
        self.tool_calls: List[ToolCallEvent] = []
        self.resources_accessed: Set[str] = set()

    def add_tool_call(self, event: ToolCallEvent) -> None:
        """Record a tool call event."""
        self.tool_calls.append(event)

        # Track resources accessed
        args_str = str(event.arguments).lower()
        if "file" in event.tool_name.lower() or "file" in args_str:
            self.resources_accessed.add("file_system")
        if "http" in event.tool_name.lower() or "http" in args_str:
            self.resources_accessed.add("network")
        if "database" in event.tool_name.lower() or "query" in args_str:
            self.resources_accessed.add("database")

    def get_tool_frequencies(self) -> Dict[str, int]:
        """Get tool call frequencies."""
        freq: Dict[str, int] = defaultdict(int)
        for call in self.tool_calls:
            freq[call.tool_name] += 1
        return dict(freq)

    def get_tool_transitions(self) -> List[Tuple[str, str]]:
        """Get tool transition pairs."""
        transitions = []
        for i in range(len(self.tool_calls) - 1):
            transitions.append(
                (self.tool_calls[i].tool_name,
                 self.tool_calls[i + 1].tool_name)
            )
        return transitions

    @property
    def duration_ms(self) -> float:
        return (time.time() - self.start_time) * 1000


# ============================================================================
# Anomaly Detectors
# ============================================================================


class ToolFrequencyDetector:
    """Detects anomalies in tool call frequencies."""

    def __init__(self, threshold_sigma: float = 2.0):
        self.threshold_sigma = threshold_sigma

    def detect(
        self,
        current_freq: Dict[str, int],
        baseline: AgentBaseline,
    ) -> List[AnomalyEvent]:
        """Detect frequency anomalies."""
        anomalies = []

        if baseline.sample_count < 3:
            return []  # Not enough data

        for tool, count in current_freq.items():
            if tool in baseline.tool_frequencies:
                expected = baseline.tool_frequencies[tool]
                # Simple z-score style check
                if expected > 0:
                    ratio = count / expected
                    if ratio > 3.0:  # 3x more than expected
                        anomalies.append(
                            AnomalyEvent(
                                anomaly_type=AnomalyType.TOOL_FREQUENCY,
                                severity=SeverityLevel.MEDIUM if ratio < 5 else SeverityLevel.HIGH,
                                description=f"Tool '{tool}' called {count}x (expected ~{expected:.1f}x)",
                                confidence=min(0.9, 0.5 + (ratio - 3) * 0.1),
                                evidence={"tool": tool, "count": count,
                                          "expected": expected},
                            )
                        )
            else:
                # New tool not in baseline
                anomalies.append(
                    AnomalyEvent(
                        anomaly_type=AnomalyType.NEW_CAPABILITY,
                        severity=SeverityLevel.LOW,
                        description=f"Agent using new tool: '{tool}'",
                        confidence=0.7,
                        evidence={"tool": tool, "count": count},
                    )
                )

        return anomalies


class SequenceAnomalyDetector:
    """Detects anomalies in tool call sequences."""

    def detect(
        self,
        transitions: List[Tuple[str, str]],
        baseline: AgentBaseline,
    ) -> List[AnomalyEvent]:
        """Detect sequence anomalies."""
        anomalies = []

        if not baseline.tool_sequences:
            return []

        known_transitions = set(baseline.tool_sequences)
        novel_transitions = []

        for trans in transitions:
            if trans not in known_transitions:
                novel_transitions.append(trans)

        if len(novel_transitions) > len(transitions) * 0.5:
            # More than half transitions are novel
            anomalies.append(
                AnomalyEvent(
                    anomaly_type=AnomalyType.TOOL_SEQUENCE,
                    severity=SeverityLevel.MEDIUM,
                    description=f"Unusual tool sequence pattern ({len(novel_transitions)} novel transitions)",
                    confidence=0.6 + min(0.3, len(novel_transitions) * 0.05),
                    evidence={
                        "novel_transitions": [f"{a}->{b}" for a, b in novel_transitions[:5]],
                        "total_transitions": len(transitions),
                    },
                )
            )

        return anomalies


class TimingAnomalyDetector:
    """Detects timing anomalies in sessions."""

    def detect(
        self,
        session: AgentSession,
        baseline: AgentBaseline,
    ) -> List[AnomalyEvent]:
        """Detect timing anomalies."""
        anomalies = []

        if baseline.avg_session_duration_ms <= 0 or baseline.sample_count < 3:
            return []

        # Check session duration
        duration_ratio = session.duration_ms / baseline.avg_session_duration_ms
        if duration_ratio > 5.0:
            anomalies.append(
                AnomalyEvent(
                    anomaly_type=AnomalyType.TIMING_ANOMALY,
                    severity=SeverityLevel.LOW,
                    description=f"Session unusually long ({session.duration_ms:.0f}ms vs avg {baseline.avg_session_duration_ms:.0f}ms)",
                    confidence=0.5 + min(0.4, (duration_ratio - 5) * 0.05),
                    evidence={
                        "current_duration_ms": session.duration_ms,
                        "expected_duration_ms": baseline.avg_session_duration_ms,
                    },
                )
            )

        # Check tool call timing
        if len(session.tool_calls) >= 2:
            intervals = []
            for i in range(len(session.tool_calls) - 1):
                interval = session.tool_calls[i + 1].timestamp - \
                    session.tool_calls[i].timestamp
                intervals.append(interval)

            # Check for unusually fast calls (< 10ms between calls)
            rapid_calls = sum(1 for i in intervals if i < 0.01)
            if rapid_calls > len(intervals) * 0.3:
                anomalies.append(
                    AnomalyEvent(
                        anomaly_type=AnomalyType.TIMING_ANOMALY,
                        severity=SeverityLevel.MEDIUM,
                        description=f"Unusually rapid tool calls ({rapid_calls} rapid calls)",
                        confidence=0.7,
                        evidence={"rapid_calls": rapid_calls,
                                  "total_calls": len(session.tool_calls)},
                    )
                )

        return anomalies


class ResourceAccessDetector:
    """Detects anomalies in resource access patterns."""

    def detect(
        self,
        session: AgentSession,
        baseline: AgentBaseline,
    ) -> List[AnomalyEvent]:
        """Detect resource access anomalies."""
        anomalies = []

        # Check for new resource types
        baseline_resources = set(baseline.resource_patterns.keys())
        new_resources = session.resources_accessed - baseline_resources

        if new_resources:
            anomalies.append(
                AnomalyEvent(
                    anomaly_type=AnomalyType.RESOURCE_ACCESS,
                    severity=SeverityLevel.MEDIUM,
                    description=f"Agent accessing new resource types: {', '.join(new_resources)}",
                    confidence=0.7,
                    evidence={"new_resources": list(new_resources)},
                )
            )

        return anomalies


# ============================================================================
# Main Engine
# ============================================================================


class AgentAnomalyDetector:
    """
    Engine: Agent Anomaly Detector

    Detects anomalous behavior in AI agents by comparing
    current session behavior against learned baselines.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Baselines per agent
        self.baselines: Dict[str, AgentBaseline] = {}

        # Active sessions
        self.sessions: Dict[str, AgentSession] = {}

        # Detectors
        self.freq_detector = ToolFrequencyDetector(
            threshold_sigma=self.config.get("frequency_threshold_sigma", 2.0)
        )
        self.seq_detector = SequenceAnomalyDetector()
        self.timing_detector = TimingAnomalyDetector()
        self.resource_detector = ResourceAccessDetector()

        # Statistics
        self.stats = {
            "sessions_analyzed": 0,
            "anomalies_detected": 0,
            "baselines_updated": 0,
        }

        logger.info("AgentAnomalyDetector initialized")

    def start_session(self, agent_id: str, session_id: str) -> AgentSession:
        """Start tracking a new session."""
        session = AgentSession(agent_id, session_id)
        self.sessions[session_id] = session
        return session

    def record_tool_call(
        self,
        session_id: str,
        tool_name: str,
        arguments: Dict[str, Any],
        duration_ms: float = 0.0,
    ) -> None:
        """Record a tool call in a session."""
        if session_id not in self.sessions:
            logger.warning(f"Unknown session: {session_id}")
            return

        event = ToolCallEvent(
            tool_name=tool_name,
            arguments=arguments,
            timestamp=time.time(),
            duration_ms=duration_ms,
        )
        self.sessions[session_id].add_tool_call(event)

    def analyze_session(self, session_id: str) -> AnomalyResult:
        """Analyze a session for anomalies."""
        start = time.time()

        if session_id not in self.sessions:
            return AnomalyResult(
                is_anomalous=False,
                anomaly_score=0.0,
                max_severity=SeverityLevel.INFO,
                recommendations=["Session not found"],
            )

        session = self.sessions[session_id]
        agent_id = session.agent_id

        # Get or create baseline
        if agent_id not in self.baselines:
            self.baselines[agent_id] = AgentBaseline(agent_id=agent_id)

        baseline = self.baselines[agent_id]

        # Run detectors
        all_anomalies: List[AnomalyEvent] = []

        # 1. Frequency anomalies
        all_anomalies.extend(
            self.freq_detector.detect(session.get_tool_frequencies(), baseline)
        )

        # 2. Sequence anomalies
        all_anomalies.extend(
            self.seq_detector.detect(session.get_tool_transitions(), baseline)
        )

        # 3. Timing anomalies
        all_anomalies.extend(self.timing_detector.detect(session, baseline))

        # 4. Resource access anomalies
        all_anomalies.extend(self.resource_detector.detect(session, baseline))

        # Calculate overall score
        if not all_anomalies:
            anomaly_score = 0.0
            max_severity = SeverityLevel.INFO
        else:
            severity_weights = {
                SeverityLevel.INFO: 0.1,
                SeverityLevel.LOW: 0.3,
                SeverityLevel.MEDIUM: 0.6,
                SeverityLevel.HIGH: 0.85,
                SeverityLevel.CRITICAL: 1.0,
            }
            scores = [
                a.confidence * severity_weights.get(a.severity, 0.5)
                for a in all_anomalies
            ]
            anomaly_score = min(1.0, sum(scores) /
                                len(scores) + 0.1 * len(scores))
            max_severity = max(
                (a.severity for a in all_anomalies),
                key=lambda s: list(SeverityLevel).index(s),
            )

        # Generate recommendations
        recommendations = self._generate_recommendations(all_anomalies)

        self.stats["sessions_analyzed"] += 1
        self.stats["anomalies_detected"] += len(all_anomalies)

        return AnomalyResult(
            is_anomalous=len(all_anomalies) > 0,
            anomaly_score=anomaly_score,
            max_severity=max_severity,
            anomalies=all_anomalies,
            recommendations=recommendations,
            latency_ms=(time.time() - start) * 1000,
        )

    def update_baseline(self, session_id: str) -> None:
        """Update baseline from a (presumably normal) session."""
        if session_id not in self.sessions:
            return

        session = self.sessions[session_id]
        agent_id = session.agent_id

        if agent_id not in self.baselines:
            self.baselines[agent_id] = AgentBaseline(agent_id=agent_id)

        baseline = self.baselines[agent_id]

        # Update frequencies (rolling average)
        current_freq = session.get_tool_frequencies()
        n = baseline.sample_count + 1

        for tool, count in current_freq.items():
            if tool in baseline.tool_frequencies:
                # Running average
                old = baseline.tool_frequencies[tool]
                baseline.tool_frequencies[tool] = old + (count - old) / n
            else:
                baseline.tool_frequencies[tool] = count

        # Update sequences
        transitions = session.get_tool_transitions()
        baseline.tool_sequences.extend(transitions)
        # Keep only recent transitions
        baseline.tool_sequences = baseline.tool_sequences[-1000:]

        # Update durations
        old_duration = baseline.avg_session_duration_ms
        baseline.avg_session_duration_ms = old_duration + \
            (session.duration_ms - old_duration) / n

        old_tools = baseline.avg_tools_per_session
        baseline.avg_tools_per_session = old_tools + \
            (len(session.tool_calls) - old_tools) / n

        # Update resources
        for resource in session.resources_accessed:
            baseline.resource_patterns[resource] = baseline.resource_patterns.get(
                resource, 0) + 1

        baseline.sample_count = n
        baseline.last_updated = time.time()

        self.stats["baselines_updated"] += 1
        logger.debug(f"Updated baseline for agent {agent_id} (n={n})")

    def end_session(self, session_id: str, update_baseline: bool = True) -> Optional[AnomalyResult]:
        """End a session and optionally update baseline."""
        result = self.analyze_session(session_id)

        # Only update baseline if session was not anomalous
        if update_baseline and not result.is_anomalous:
            self.update_baseline(session_id)

        # Cleanup
        if session_id in self.sessions:
            del self.sessions[session_id]

        return result

    def _generate_recommendations(self, anomalies: List[AnomalyEvent]) -> List[str]:
        """Generate recommendations based on detected anomalies."""
        recommendations = []

        anomaly_types = {a.anomaly_type for a in anomalies}

        if AnomalyType.TOOL_FREQUENCY in anomaly_types:
            recommendations.append("Review agent's tool usage patterns")

        if AnomalyType.TOOL_SEQUENCE in anomaly_types:
            recommendations.append("Investigate unusual tool call ordering")

        if AnomalyType.TIMING_ANOMALY in anomaly_types:
            recommendations.append(
                "Check for automated or scripted agent behavior")

        if AnomalyType.RESOURCE_ACCESS in anomaly_types:
            recommendations.append(
                "Verify agent's authorization for accessed resources")

        if AnomalyType.NEW_CAPABILITY in anomaly_types:
            recommendations.append("Confirm new capabilities are expected")

        if not recommendations:
            recommendations.append("Continue monitoring")

        return recommendations

    def get_statistics(self) -> Dict[str, Any]:
        """Get detector statistics."""
        return {
            **self.stats,
            "active_sessions": len(self.sessions),
            "baseline_count": len(self.baselines),
        }


# ============================================================================
# Factory
# ============================================================================


def create_engine(config: Optional[Dict[str, Any]] = None) -> AgentAnomalyDetector:
    """Create an instance of the AgentAnomalyDetector engine."""
    return AgentAnomalyDetector(config)
