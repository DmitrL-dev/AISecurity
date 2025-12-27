"""
Unit tests for Behavioral API Verifier.
"""

import pytest
import time
from behavioral_api_verifier import (
    BehavioralAPIVerifier,
    TimingAnalyzer,
    VelocityChecker,
    PatternMatcher,
    BehaviorProfile,
    AnomalyType,
)


class TestTimingAnalyzer:
    """Tests for timing analysis."""

    def test_normal_timing_passes(self):
        """Normal timing passes."""
        analyzer = TimingAnalyzer()

        intervals = [1.0, 1.1, 0.9, 1.0, 1.2, 1.0]
        is_anomaly, z_score = analyzer.analyze(intervals, 1.0)

        assert is_anomaly is False

    def test_anomalous_timing_detected(self):
        """Anomalous timing is detected."""
        analyzer = TimingAnalyzer()

        intervals = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
        is_anomaly, z_score = analyzer.analyze(intervals, 100.0)

        assert is_anomaly is True


class TestVelocityChecker:
    """Tests for velocity checking."""

    def test_normal_velocity_passes(self):
        """Normal velocity passes."""
        checker = VelocityChecker(max_per_second=5)

        violation, reason = checker.check("user1", time.time())

        assert violation is False

    def test_high_velocity_detected(self):
        """High velocity is detected."""
        checker = VelocityChecker(max_per_second=2)

        current = time.time()
        # Make many requests quickly
        for i in range(5):
            checker.check("user1", current + i * 0.1)

        violation, reason = checker.check("user1", current + 0.5)

        assert violation is True


class TestPatternMatcher:
    """Tests for pattern matching."""

    def test_similar_pattern_high_score(self):
        """Similar pattern gets high score."""
        matcher = PatternMatcher()

        profile = BehaviorProfile(
            user_id="user1",
            avg_request_interval=1.0,
            avg_text_length=50,
            request_count=10,
        )

        similarity = matcher.calculate_similarity(profile, 50, 1.0)

        assert similarity > 0.9

    def test_different_pattern_low_score(self):
        """Different pattern gets low score."""
        matcher = PatternMatcher()

        profile = BehaviorProfile(
            user_id="user1",
            avg_request_interval=1.0,
            avg_text_length=50,
            request_count=10,
        )

        similarity = matcher.calculate_similarity(profile, 500, 100.0)

        assert similarity < 0.5


class TestBehavioralAPIVerifier:
    """Integration tests."""

    def test_first_request_passes(self):
        """First request passes."""
        verifier = BehavioralAPIVerifier()

        result = verifier.verify("user1", "Hello world")

        assert result.is_verified is True

    def test_consistent_behavior_passes(self):
        """Consistent behavior passes."""
        verifier = BehavioralAPIVerifier()

        for i in range(5):
            result = verifier.verify("user1", "Similar text here")

        assert result.is_verified is True

    def test_high_velocity_flagged(self):
        """High velocity is flagged."""
        verifier = BehavioralAPIVerifier()
        verifier.velocity_checker.max_per_second = 3

        # Many rapid requests
        for i in range(10):
            result = verifier.verify("user1", "Quick request")

        assert AnomalyType.VELOCITY_SPIKE in result.anomalies

    def test_profile_builds(self):
        """Profile builds over time."""
        verifier = BehavioralAPIVerifier()

        verifier.verify("user1", "Request 1")
        verifier.verify("user1", "Request 2")
        verifier.verify("user1", "Request 3")

        profile = verifier._profiles["user1"]

        assert profile.request_count == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
