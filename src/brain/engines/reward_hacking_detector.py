"""
Reward Hacking Detector — SENTINEL Phase 3: RL Agent Security

Detects when RL-based agents optimize wrong metrics.
Philosophy: "Delete all backups = lower storage cost" is reward hacking.

Features:
- Metric gaming detection
- Shortcut identification
- Reward proxy analysis
- Behavioral integrity checks

Author: Dmitry Labintsev
Contact: chg@live.ru | @DmLabincev
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime


class HackingType(Enum):
    """Types of reward hacking"""

    METRIC_GAMING = "metric_gaming"
    SHORTCUT = "shortcut"
    PROXY_EXPLOITATION = "proxy_exploitation"
    SPECIFICATION_GAMING = "specification_gaming"


@dataclass
class MetricObservation:
    """Observation of agent metrics"""

    agent_id: str
    metric_name: str
    value: float
    timestamp: datetime
    action_taken: str


@dataclass
class HackingPattern:
    """Detected reward hacking pattern"""

    hacking_type: HackingType
    description: str
    metric_involved: str
    severity: float
    evidence: List[str]


@dataclass
class RewardHackingResult:
    """Result of reward hacking detection"""

    hacking_detected: bool
    patterns: List[HackingPattern]
    risk_score: float
    affected_metrics: List[str]
    recommendations: List[str]


class RewardHackingDetector:
    """
    Detects reward hacking in RL-based agents.

    Attack Pattern:
    - Agent goal: "Minimize storage cost"
    - Hack: Delete all backups → $0 storage
    - Result: Metric improved, system destroyed

    Usage:
        detector = RewardHackingDetector()
        result = detector.analyze(observations)
        if result.hacking_detected:
            pause_agent()
    """

    ENGINE_NAME = "reward_hacking_detector"
    ENGINE_VERSION = "1.0.0"
    IS_PROACTIVE = True

    # Suspicious patterns
    SUSPICIOUS_IMPROVEMENTS = {
        "cost": ["delete", "remove", "disable", "stop"],
        "time": ["skip", "bypass", "shortcut"],
        "error_rate": ["suppress", "ignore", "hide"],
        "throughput": ["cache_poison", "duplicate"],
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.observation_history: List[MetricObservation] = []
        self.baseline_metrics: Dict[str, float] = {}

    def analyze(self, observations: List[MetricObservation]) -> RewardHackingResult:
        """Analyze for reward hacking"""
        patterns = []

        # Group by metric
        by_metric: Dict[str, List[MetricObservation]] = {}
        for obs in observations:
            if obs.metric_name not in by_metric:
                by_metric[obs.metric_name] = []
            by_metric[obs.metric_name].append(obs)

        # 1. Detect metric gaming
        for metric, obs_list in by_metric.items():
            gaming = self._detect_metric_gaming(metric, obs_list)
            if gaming:
                patterns.append(gaming)

        # 2. Detect shortcuts
        shortcuts = self._detect_shortcuts(observations)
        patterns.extend(shortcuts)

        # 3. Detect proxy exploitation
        proxy = self._detect_proxy_exploitation(observations)
        patterns.extend(proxy)

        # Calculate risk
        risk_score = sum(p.severity for p in patterns) / max(len(patterns), 1)

        # Affected metrics
        affected = list(set(p.metric_involved for p in patterns))

        # Recommendations
        recommendations = []
        if patterns:
            recommendations.append("Review agent's optimization objective")
            recommendations.append("Add constraints to prevent harmful shortcuts")

        for pattern in patterns:
            if pattern.hacking_type == HackingType.METRIC_GAMING:
                recommendations.append(
                    f"Add integrity check for {pattern.metric_involved}"
                )

        return RewardHackingResult(
            hacking_detected=len(patterns) > 0,
            patterns=patterns,
            risk_score=min(risk_score, 1.0),
            affected_metrics=affected,
            recommendations=recommendations,
        )

    def _detect_metric_gaming(
        self, metric: str, observations: List[MetricObservation]
    ) -> Optional[HackingPattern]:
        """Detect metric gaming"""
        if len(observations) < 2:
            return None

        # Sort by time
        sorted_obs = sorted(observations, key=lambda o: o.timestamp)

        # Check for suspicious improvement
        first_val = sorted_obs[0].value
        last_val = sorted_obs[-1].value

        # Rapid improvement is suspicious
        improvement = (first_val - last_val) / max(first_val, 0.01)

        if improvement > 0.5:  # 50% improvement
            # Check if actions are suspicious
            for keyword_group in self.SUSPICIOUS_IMPROVEMENTS.values():
                for obs in sorted_obs:
                    if any(kw in obs.action_taken.lower() for kw in keyword_group):
                        return HackingPattern(
                            hacking_type=HackingType.METRIC_GAMING,
                            description=f"{metric} improved {improvement:.0%} "
                            f"via suspicious action",
                            metric_involved=metric,
                            severity=min(improvement, 1.0),
                            evidence=[
                                f"Action: {obs.action_taken}",
                                f"Improvement: {improvement:.0%}",
                            ],
                        )

        return None

    def _detect_shortcuts(
        self, observations: List[MetricObservation]
    ) -> List[HackingPattern]:
        """Detect shortcut exploitation"""
        patterns = []

        shortcut_actions = [
            "skip_validation",
            "bypass_check",
            "disable_safety",
            "cache_without_verify",
            "assume_success",
        ]

        for obs in observations:
            action_lower = obs.action_taken.lower()
            for shortcut in shortcut_actions:
                if shortcut.replace("_", " ") in action_lower:
                    patterns.append(
                        HackingPattern(
                            hacking_type=HackingType.SHORTCUT,
                            description=f"Shortcut detected: {obs.action_taken}",
                            metric_involved=obs.metric_name,
                            severity=0.7,
                            evidence=[
                                f"Agent: {obs.agent_id}",
                                f"Action: {obs.action_taken}",
                            ],
                        )
                    )

        return patterns

    def _detect_proxy_exploitation(
        self, observations: List[MetricObservation]
    ) -> List[HackingPattern]:
        """Detect proxy metric exploitation"""
        patterns = []

        # Proxy exploitation: optimizing measurable proxy instead of real goal
        proxy_cases = {
            "satisfaction_score": "Inflated self-ratings",
            "completion_count": "Marking incomplete as complete",
            "response_time": "Sacrificing quality for speed",
        }

        for obs in observations:
            if obs.metric_name in proxy_cases:
                # Check for suspicious action
                if any(
                    kw in obs.action_taken.lower()
                    for kw in ["mark_complete", "auto_approve", "skip"]
                ):
                    patterns.append(
                        HackingPattern(
                            hacking_type=HackingType.PROXY_EXPLOITATION,
                            description=proxy_cases[obs.metric_name],
                            metric_involved=obs.metric_name,
                            severity=0.6,
                            evidence=[f"Action: {obs.action_taken}"],
                        )
                    )

        return patterns

    def set_baseline(self, metric: str, value: float):
        """Set baseline for metric"""
        self.baseline_metrics[metric] = value

    def get_statistics(self) -> Dict[str, Any]:
        """Get detector statistics"""
        return {
            "observations_tracked": len(self.observation_history),
            "baseline_metrics": len(self.baseline_metrics),
            "suspicious_patterns": len(self.SUSPICIOUS_IMPROVEMENTS),
        }


# Factory
def create_engine(config: Optional[Dict[str, Any]] = None) -> RewardHackingDetector:
    return RewardHackingDetector(config)


if __name__ == "__main__":
    detector = RewardHackingDetector()

    print("=== Reward Hacking Detector Test ===\n")

    now = datetime.now()

    observations = [
        MetricObservation("agent-1", "storage_cost", 1000, now, "initial_state"),
        MetricObservation("agent-1", "storage_cost", 100, now, "delete_all_backups"),
        MetricObservation("agent-1", "completion_count", 50, now, "mark_all_complete"),
    ]

    result = detector.analyze(observations)

    print(f"Hacking detected: {result.hacking_detected}")
    print(f"Risk score: {result.risk_score:.0%}")
    print(f"Patterns found: {len(result.patterns)}")
    for pattern in result.patterns:
        print(f"  - {pattern.hacking_type.value}: {pattern.description}")
    print(f"Recommendations: {result.recommendations}")
