"""
Temporal Poisoning Detector — SENTINEL Phase 3 Tier 2

Detects slow poisoning attacks across sessions.
Philosophy: Incremental drift undetectable per-session, visible over time.

Features:
- Cross-session drift tracking
- Cumulative anomaly detection
- Temporal pattern analysis
- Session fingerprinting

Author: Dmitry Labintsev
Contact: chg@live.ru | @DmLabincev
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class SessionSnapshot:
    """Snapshot of a session state"""

    session_id: str
    timestamp: datetime
    behavior_vector: List[float]
    anomaly_score: float


@dataclass
class DriftAnalysis:
    """Analysis of temporal drift"""

    total_drift: float
    per_session_drift: List[float]
    drift_direction: List[float]
    is_progressive: bool


@dataclass
class TemporalPoisoningResult:
    """Result of temporal poisoning detection"""

    poisoning_detected: bool
    drift_analysis: DriftAnalysis
    cumulative_anomaly: float
    affected_sessions: List[str]
    recommendations: List[str]


class TemporalPoisoningDetector:
    """
    Detects slow poisoning attacks across sessions.

    Attack pattern:
    Session 1: 0.1% drift (undetectable)
    Session 2: +0.1% drift (still benign)
    ...
    Session 100: 10% total drift (poisoned)

    Usage:
        detector = TemporalPoisoningDetector()
        detector.record_session(session)
        result = detector.analyze()
    """

    ENGINE_NAME = "temporal_poisoning"
    ENGINE_VERSION = "1.0.0"
    IS_PROACTIVE = True

    DRIFT_THRESHOLD = 0.05  # 5% cumulative drift
    SESSION_THRESHOLD = 0.01  # 1% per-session

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.session_history: List[SessionSnapshot] = []
        self.baseline_vector: Optional[List[float]] = None

    def set_baseline(self, vector: List[float]):
        """Set baseline behavior vector"""
        self.baseline_vector = vector

    def record_session(self, snapshot: SessionSnapshot):
        """Record a session snapshot"""
        self.session_history.append(snapshot)

    def analyze(self) -> TemporalPoisoningResult:
        """Analyze for temporal poisoning"""
        if len(self.session_history) < 2:
            return self._empty_result()

        # Calculate drift from baseline
        drifts = []
        for snapshot in self.session_history:
            if self.baseline_vector:
                drift = self._calculate_drift(
                    self.baseline_vector, snapshot.behavior_vector
                )
            else:
                drift = 0.0
            drifts.append(drift)

        # Analyze drift pattern
        total_drift = drifts[-1] if drifts else 0.0
        is_progressive = self._is_progressive_drift(drifts)

        # Calculate drift direction
        direction = self._calculate_drift_direction()

        drift_analysis = DriftAnalysis(
            total_drift=total_drift,
            per_session_drift=drifts,
            drift_direction=direction,
            is_progressive=is_progressive,
        )

        # Cumulative anomaly
        cumulative = sum(s.anomaly_score for s in self.session_history)

        # Detect poisoning
        poisoning_detected = total_drift > self.DRIFT_THRESHOLD and is_progressive

        affected = [
            s.session_id
            for s in self.session_history
            if s.anomaly_score > self.SESSION_THRESHOLD
        ]

        recommendations = []
        if poisoning_detected:
            recommendations.append("Reset to baseline state")
            recommendations.append("Review session history for injection points")
            recommendations.append("Increase per-session monitoring sensitivity")

        return TemporalPoisoningResult(
            poisoning_detected=poisoning_detected,
            drift_analysis=drift_analysis,
            cumulative_anomaly=cumulative,
            affected_sessions=affected,
            recommendations=recommendations,
        )

    def _calculate_drift(self, baseline: List[float], current: List[float]) -> float:
        """Calculate drift from baseline"""
        if not baseline or not current:
            return 0.0

        import math

        dist = math.sqrt(sum((b - c) ** 2 for b, c in zip(baseline, current)))
        return dist / len(baseline)

    def _is_progressive_drift(self, drifts: List[float]) -> bool:
        """Check if drift is progressive (monotonic increase)"""
        if len(drifts) < 3:
            return False

        increases = sum(1 for i in range(1, len(drifts)) if drifts[i] > drifts[i - 1])
        return increases > len(drifts) * 0.6

    def _calculate_drift_direction(self) -> List[float]:
        """Calculate average drift direction"""
        if len(self.session_history) < 2 or not self.baseline_vector:
            return []

        last = self.session_history[-1].behavior_vector
        return [l - b for l, b in zip(last, self.baseline_vector)]

    def _empty_result(self) -> TemporalPoisoningResult:
        return TemporalPoisoningResult(
            poisoning_detected=False,
            drift_analysis=DriftAnalysis(0.0, [], [], False),
            cumulative_anomaly=0.0,
            affected_sessions=[],
            recommendations=[],
        )

    def get_statistics(self) -> Dict[str, Any]:
        return {
            "sessions_tracked": len(self.session_history),
            "baseline_set": self.baseline_vector is not None,
            "drift_threshold": self.DRIFT_THRESHOLD,
        }


def create_engine(config: Optional[Dict[str, Any]] = None) -> TemporalPoisoningDetector:
    return TemporalPoisoningDetector(config)
