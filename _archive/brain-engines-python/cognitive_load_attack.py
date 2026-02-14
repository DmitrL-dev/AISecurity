"""
Cognitive Load Attack Detector — SENTINEL Phase 3: HITL Protection

Detects attacks that overwhelm human reviewers.
Philosophy: Attackers hide 1 malicious action in 100 benign ones.

Features:
- Reviewer attention modeling
- Suspicious clustering detection
- Action distribution anomaly
- Alert fatigue detection

Author: Dmitry Labintsev
Contact: chg@live.ru | @DmLabincev
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime, timedelta
from collections import Counter


class ActionRisk(Enum):
    """Risk level of actions"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ReviewerAction:
    """An action pending review"""

    action_id: str
    action_type: str
    timestamp: datetime
    risk_level: ActionRisk
    description: str
    source_agent: str


@dataclass
class CognitiveLoadMetrics:
    """Metrics about cognitive load"""

    pending_reviews: int
    actions_per_minute: float
    high_risk_ratio: float
    avg_decision_time: float
    attention_score: float  # 0-1, lower = stressed


@dataclass
class ClusterAnalysis:
    """Analysis of action clustering"""

    cluster_id: str
    action_count: int
    dominant_type: str
    hidden_risk_count: int
    is_suspicious: bool


@dataclass
class CognitiveLoadResult:
    """Result of cognitive load analysis"""

    is_attack_likely: bool
    load_metrics: CognitiveLoadMetrics
    suspicious_clusters: List[ClusterAnalysis]
    hidden_actions: List[ReviewerAction]
    risk_score: float
    recommendations: List[str]


class CognitiveLoadAttackDetector:
    """
    Detects attacks that overwhelm HITL reviewers.

    Attack Pattern:
    1. Generate 99 benign actions
    2. Hide 1 malicious action in the middle
    3. Reviewer approves in bulk (fatigue)
    4. Malicious action slips through

    Usage:
        detector = CognitiveLoadAttackDetector()
        result = detector.analyze_queue(action_queue)
        if result.is_attack_likely:
            slow_down_approvals()
    """

    ENGINE_NAME = "cognitive_load_attack"
    ENGINE_VERSION = "1.0.0"
    IS_PROACTIVE = True

    # Thresholds
    MAX_ACTIONS_PER_MINUTE = 10
    MIN_ATTENTION_SCORE = 0.4
    SUSPICIOUS_CLUSTER_SIZE = 20
    HIDDEN_RISK_THRESHOLD = 0.1  # 10% high-risk in cluster = suspicious

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.action_history: List[ReviewerAction] = []
        self.decision_history: List[Dict[str, Any]] = []

    def analyze_queue(
        self,
        pending_actions: List[ReviewerAction],
        reviewer_metrics: Optional[Dict[str, Any]] = None,
    ) -> CognitiveLoadResult:
        """Analyze action queue for cognitive load attacks"""

        # 1. Calculate load metrics
        load_metrics = self._calculate_load_metrics(pending_actions, reviewer_metrics)

        # 2. Detect suspicious clusters
        clusters = self._detect_clusters(pending_actions)
        suspicious = [c for c in clusters if c.is_suspicious]

        # 3. Find hidden high-risk actions
        hidden = self._find_hidden_actions(pending_actions)

        # 4. Calculate risk score
        risk_score = self._calculate_risk(load_metrics, suspicious, hidden)

        # 5. Determine if attack likely
        is_attack = risk_score > 0.6 or len(suspicious) > 0 or len(hidden) >= 3

        # 6. Recommendations
        recommendations = self._generate_recommendations(
            load_metrics, suspicious, hidden
        )

        return CognitiveLoadResult(
            is_attack_likely=is_attack,
            load_metrics=load_metrics,
            suspicious_clusters=suspicious,
            hidden_actions=hidden,
            risk_score=risk_score,
            recommendations=recommendations,
        )

    def _calculate_load_metrics(
        self, actions: List[ReviewerAction], reviewer_metrics: Optional[Dict[str, Any]]
    ) -> CognitiveLoadMetrics:
        """Calculate cognitive load metrics"""
        pending = len(actions)

        # Actions per minute (from timestamps)
        if len(actions) >= 2:
            time_span = (
                actions[-1].timestamp - actions[0].timestamp
            ).total_seconds() / 60
            apm = len(actions) / max(time_span, 0.1)
        else:
            apm = 0

        # High risk ratio
        high_risk = sum(
            1 for a in actions if a.risk_level in [ActionRisk.HIGH, ActionRisk.CRITICAL]
        )
        risk_ratio = high_risk / max(len(actions), 1)

        # Decision time (from reviewer metrics or default)
        avg_time = (reviewer_metrics or {}).get("avg_decision_time", 5.0)

        # Attention score (inverse of load)
        attention = 1.0
        if pending > 50:
            attention -= 0.3
        if apm > self.MAX_ACTIONS_PER_MINUTE:
            attention -= 0.3
        if avg_time < 2.0:  # Rushing
            attention -= 0.3

        return CognitiveLoadMetrics(
            pending_reviews=pending,
            actions_per_minute=apm,
            high_risk_ratio=risk_ratio,
            avg_decision_time=avg_time,
            attention_score=max(attention, 0.0),
        )

    def _detect_clusters(self, actions: List[ReviewerAction]) -> List[ClusterAnalysis]:
        """Detect suspicious action clusters"""
        clusters = []

        # Group by source agent and time window
        windows: Dict[str, List[ReviewerAction]] = {}
        for action in actions:
            key = f"{action.source_agent}:{action.timestamp.hour}"
            if key not in windows:
                windows[key] = []
            windows[key].append(action)

        # Analyze each window
        for key, window_actions in windows.items():
            if len(window_actions) < 5:
                continue

            # Count action types
            types = Counter(a.action_type for a in window_actions)
            dominant = types.most_common(1)[0][0] if types else "unknown"

            # Count hidden high-risk
            hidden_risk = sum(
                1
                for a in window_actions
                if a.risk_level in [ActionRisk.HIGH, ActionRisk.CRITICAL]
            )

            is_suspicious = (
                len(window_actions) >= self.SUSPICIOUS_CLUSTER_SIZE
                and hidden_risk > 0
                and hidden_risk / len(window_actions) < self.HIDDEN_RISK_THRESHOLD * 2
            )

            clusters.append(
                ClusterAnalysis(
                    cluster_id=key,
                    action_count=len(window_actions),
                    dominant_type=dominant,
                    hidden_risk_count=hidden_risk,
                    is_suspicious=is_suspicious,
                )
            )

        return clusters

    def _find_hidden_actions(
        self, actions: List[ReviewerAction]
    ) -> List[ReviewerAction]:
        """Find high-risk actions hidden among benign ones"""
        hidden = []

        for i, action in enumerate(actions):
            if action.risk_level not in [ActionRisk.HIGH, ActionRisk.CRITICAL]:
                continue

            # Check surrounding context
            start = max(0, i - 5)
            end = min(len(actions), i + 5)
            neighbors = actions[start:end]

            # Count benign neighbors
            benign_count = sum(
                1
                for n in neighbors
                if n.risk_level in [ActionRisk.LOW, ActionRisk.MEDIUM]
            )

            # If mostly benign neighbors, action is "hidden"
            if benign_count >= len(neighbors) * 0.7:
                hidden.append(action)

        return hidden

    def _calculate_risk(
        self,
        metrics: CognitiveLoadMetrics,
        clusters: List[ClusterAnalysis],
        hidden: List[ReviewerAction],
    ) -> float:
        """Calculate overall risk score"""
        risk = 0.0

        # Low attention = high risk
        risk += (1.0 - metrics.attention_score) * 0.4

        # Suspicious clusters
        risk += len(clusters) * 0.15

        # Hidden actions
        risk += len(hidden) * 0.1

        # High action rate
        if metrics.actions_per_minute > self.MAX_ACTIONS_PER_MINUTE:
            risk += 0.2

        return min(risk, 1.0)

    def _generate_recommendations(
        self,
        metrics: CognitiveLoadMetrics,
        clusters: List[ClusterAnalysis],
        hidden: List[ReviewerAction],
    ) -> List[str]:
        """Generate recommendations"""
        recs = []

        if metrics.attention_score < self.MIN_ATTENTION_SCORE:
            recs.append("Reduce approval queue to prevent fatigue")

        if metrics.actions_per_minute > self.MAX_ACTIONS_PER_MINUTE:
            recs.append("Rate-limit incoming actions")

        if clusters:
            recs.append(f"Review {len(clusters)} suspicious clusters individually")

        if hidden:
            recs.append(f"Flag {len(hidden)} hidden high-risk actions for attention")

        if metrics.avg_decision_time < 2.0:
            recs.append("Slow down: decision time indicates rushing")

        return recs

    def record_decision(self, action_id: str, approved: bool, decision_time: float):
        """Record a review decision"""
        self.decision_history.append(
            {
                "action_id": action_id,
                "approved": approved,
                "decision_time": decision_time,
                "timestamp": datetime.now(),
            }
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get detector statistics"""
        return {
            "actions_tracked": len(self.action_history),
            "decisions_tracked": len(self.decision_history),
            "max_actions_per_minute": self.MAX_ACTIONS_PER_MINUTE,
            "suspicious_cluster_size": self.SUSPICIOUS_CLUSTER_SIZE,
        }


# Factory
def create_engine(
    config: Optional[Dict[str, Any]] = None,
) -> CognitiveLoadAttackDetector:
    return CognitiveLoadAttackDetector(config)


if __name__ == "__main__":
    detector = CognitiveLoadAttackDetector()

    print("=== Cognitive Load Attack Detector Test ===\n")

    # Simulate attack: 95 benign + 5 hidden high-risk
    now = datetime.now()
    actions = []

    for i in range(100):
        risk = ActionRisk.LOW if i % 20 != 10 else ActionRisk.HIGH
        actions.append(
            ReviewerAction(
                action_id=f"action-{i}",
                action_type="read_data",
                timestamp=now + timedelta(seconds=i * 2),
                risk_level=risk,
                description=f"Action {i}",
                source_agent="agent-1",
            )
        )

    result = detector.analyze_queue(actions)

    print(f"Attack likely: {result.is_attack_likely}")
    print(f"Risk score: {result.risk_score:.0%}")
    print(f"Attention score: {result.load_metrics.attention_score:.0%}")
    print(f"Hidden actions: {len(result.hidden_actions)}")
    print(f"Suspicious clusters: {len(result.suspicious_clusters)}")
    print(f"Recommendations: {result.recommendations}")
