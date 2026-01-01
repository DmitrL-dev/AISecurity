"""
Behavioral API Verifier Engine - User Verification

Verifies user identity through behavioral analysis:
- Typing patterns
- Request timing
- Session behavior
- Anomaly detection

Addresses: Enterprise AI Governance
Research: behavioral_biometrics_deep_dive.md
Invention: Behavioral API Verifier (#29)
"""

import time
import math
import logging
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("BehavioralAPIVerifier")


# ============================================================================
# Data Classes
# ============================================================================


class AnomalyType(Enum):
    """Types of behavioral anomalies."""

    TIMING_ANOMALY = "timing_anomaly"
    PATTERN_SHIFT = "pattern_shift"
    VELOCITY_SPIKE = "velocity_spike"
    SESSION_HIJACK = "session_hijack"


@dataclass
class BehaviorProfile:
    """User behavior profile."""

    user_id: str
    avg_request_interval: float = 0.0
    avg_text_length: float = 0.0
    request_count: int = 0
    last_request_time: float = 0.0
    intervals: List[float] = field(default_factory=list)
    lengths: List[int] = field(default_factory=list)


@dataclass
class VerificationResult:
    """Result from behavioral verification."""

    is_verified: bool
    confidence: float
    anomalies: List[AnomalyType] = field(default_factory=list)
    risk_score: float = 0.0
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_verified": self.is_verified,
            "confidence": self.confidence,
            "anomalies": [a.value for a in self.anomalies],
            "risk_score": self.risk_score,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Timing Analyzer
# ============================================================================


class TimingAnalyzer:
    """
    Analyzes request timing patterns.
    """

    def __init__(self, window_size: int = 20):
        self.window_size = window_size

    def analyze(
        self,
        intervals: List[float],
        current_interval: float,
    ) -> Tuple[bool, float]:
        """
        Analyze timing for anomaly.

        Returns:
            (is_anomaly, z_score)
        """
        if len(intervals) < 5:
            return False, 0.0

        recent = intervals[-self.window_size:]
        mean = sum(recent) / len(recent)
        variance = sum((x - mean) ** 2 for x in recent) / len(recent)
        std = math.sqrt(variance) if variance > 0 else 1.0

        z_score = abs(current_interval - mean) / std if std > 0 else 0.0

        # Anomaly if z-score > 3
        return z_score > 3.0, z_score


# ============================================================================
# Velocity Checker
# ============================================================================


class VelocityChecker:
    """
    Checks request velocity for abuse.
    """

    def __init__(
        self,
        max_per_second: float = 5.0,
        max_per_minute: float = 60.0,
    ):
        self.max_per_second = max_per_second
        self.max_per_minute = max_per_minute
        self._timestamps: Dict[str, deque] = {}

    def check(
        self,
        user_id: str,
        current_time: float,
    ) -> Tuple[bool, str]:
        """
        Check velocity limits.

        Returns:
            (is_violation, reason)
        """
        if user_id not in self._timestamps:
            self._timestamps[user_id] = deque(maxlen=100)

        timestamps = self._timestamps[user_id]
        timestamps.append(current_time)

        # Check per-second
        one_sec_ago = current_time - 1.0
        recent_1s = sum(1 for t in timestamps if t > one_sec_ago)
        if recent_1s > self.max_per_second:
            return True, f"Rate exceeded: {recent_1s}/sec"

        # Check per-minute
        one_min_ago = current_time - 60.0
        recent_1m = sum(1 for t in timestamps if t > one_min_ago)
        if recent_1m > self.max_per_minute:
            return True, f"Rate exceeded: {recent_1m}/min"

        return False, ""


# ============================================================================
# Pattern Matcher
# ============================================================================


class PatternMatcher:
    """
    Matches behavioral patterns.
    """

    def calculate_similarity(
        self,
        profile: BehaviorProfile,
        current_length: int,
        current_interval: float,
    ) -> float:
        """Calculate similarity to profile."""
        if profile.request_count < 5:
            return 1.0  # Not enough data

        # Length similarity
        len_diff = abs(current_length - profile.avg_text_length)
        len_score = max(0, 1 - len_diff / (profile.avg_text_length or 1))

        # Interval similarity
        int_diff = abs(current_interval - profile.avg_request_interval)
        int_score = max(0, 1 - int_diff / (profile.avg_request_interval or 1))

        return (len_score + int_score) / 2


# ============================================================================
# Main Engine
# ============================================================================


class BehavioralAPIVerifier:
    """
    Behavioral API Verifier - User Verification

    Comprehensive behavioral verification:
    - Timing analysis
    - Velocity checking
    - Pattern matching

    Invention #29 from research.
    Addresses Enterprise AI Governance.
    """

    def __init__(
        self,
        similarity_threshold: float = 0.5,
    ):
        self.timing_analyzer = TimingAnalyzer()
        self.velocity_checker = VelocityChecker()
        self.pattern_matcher = PatternMatcher()

        self._profiles: Dict[str, BehaviorProfile] = {}
        self.similarity_threshold = similarity_threshold

        logger.info("BehavioralAPIVerifier initialized")

    def verify(
        self,
        user_id: str,
        text: str,
        session_id: str = "",
    ) -> VerificationResult:
        """
        Verify user behavior.

        Args:
            user_id: User identifier
            text: Request text
            session_id: Session identifier

        Returns:
            VerificationResult
        """
        start = time.time()
        current_time = time.time()

        anomalies = []
        risk = 0.0
        explanations = []

        # Get or create profile
        if user_id not in self._profiles:
            self._profiles[user_id] = BehaviorProfile(user_id=user_id)

        profile = self._profiles[user_id]

        # Calculate interval
        interval = 0.0
        if profile.last_request_time > 0:
            interval = current_time - profile.last_request_time

        # Check velocity
        velocity_violation, velocity_reason = self.velocity_checker.check(
            user_id, current_time
        )
        if velocity_violation:
            anomalies.append(AnomalyType.VELOCITY_SPIKE)
            risk = max(risk, 0.8)
            explanations.append(velocity_reason)

        # Check timing
        if profile.intervals:
            timing_anomaly, z_score = self.timing_analyzer.analyze(
                profile.intervals, interval
            )
            if timing_anomaly:
                anomalies.append(AnomalyType.TIMING_ANOMALY)
                risk = max(risk, 0.6)
                explanations.append(f"Timing z-score: {z_score:.2f}")

        # Check pattern similarity
        similarity = self.pattern_matcher.calculate_similarity(
            profile, len(text), interval
        )
        if similarity < self.similarity_threshold and profile.request_count > 10:
            anomalies.append(AnomalyType.PATTERN_SHIFT)
            risk = max(risk, 0.7)
            explanations.append(f"Pattern similarity: {similarity:.2f}")

        # Update profile
        profile.request_count += 1
        profile.last_request_time = current_time

        if interval > 0:
            profile.intervals.append(interval)
            if len(profile.intervals) > 100:
                profile.intervals = profile.intervals[-100:]

        profile.lengths.append(len(text))
        if len(profile.lengths) > 100:
            profile.lengths = profile.lengths[-100:]

        # Update averages
        if profile.intervals:
            profile.avg_request_interval = sum(profile.intervals) / len(
                profile.intervals
            )
        if profile.lengths:
            profile.avg_text_length = sum(
                profile.lengths) / len(profile.lengths)

        is_verified = len(anomalies) == 0
        confidence = 1.0 - risk

        if anomalies:
            logger.warning(
                f"Behavioral anomalies: {[a.value for a in anomalies]}")

        return VerificationResult(
            is_verified=is_verified,
            confidence=confidence,
            anomalies=anomalies,
            risk_score=risk,
            explanation="; ".join(
                explanations) if explanations else "Behavior normal",
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_verifier: Optional[BehavioralAPIVerifier] = None


def get_verifier() -> BehavioralAPIVerifier:
    global _default_verifier
    if _default_verifier is None:
        _default_verifier = BehavioralAPIVerifier()
    return _default_verifier
