"""
Unit tests for Temporal Pattern Analyzer.
"""

import time
import pytest
from engines.temporal_pattern_analyzer import (
    TemporalPatternAnalyzer,
    IntervalAnalyzer,
    RapidFireDetector,
    SlowDripDetector,
    SequenceDetector,
    Event,
    TemporalThreat,
)


class TestIntervalAnalyzer:
    """Tests for interval analyzer."""

    def test_analyze_single_event(self):
        """Single event has no intervals."""
        analyzer = IntervalAnalyzer()
        events = [Event("e1", 1.0, "test")]

        stats = analyzer.analyze(events)

        assert stats["count"] == 1
        assert stats["avg_interval"] == 0

    def test_analyze_multiple_events(self):
        """Multiple events have intervals."""
        analyzer = IntervalAnalyzer()
        events = [
            Event("e1", 1.0, "test"),
            Event("e2", 2.0, "test"),
            Event("e3", 3.0, "test"),
        ]

        stats = analyzer.analyze(events)

        assert stats["count"] == 3
        assert stats["avg_interval"] == 1.0


class TestRapidFireDetector:
    """Tests for rapid fire detector."""

    def test_normal_not_detected(self):
        """Normal intervals not detected."""
        detector = RapidFireDetector(threshold=0.1)

        result = detector.detect({"min_interval": 1.0})

        assert result is False

    def test_rapid_detected(self):
        """Rapid intervals detected."""
        detector = RapidFireDetector(threshold=0.5)

        result = detector.detect({"min_interval": 0.05})

        assert result is True


class TestSequenceDetector:
    """Tests for sequence detector."""

    def test_attack_sequence_detected(self):
        """Attack sequence detected."""
        detector = SequenceDetector()
        events = [
            Event("e1", 1.0, "probe"),
            Event("e2", 2.0, "exploit"),
            Event("e3", 3.0, "escalate"),
        ]

        result = detector.detect(events)

        assert result is True


class TestTemporalPatternAnalyzer:
    """Integration tests."""

    def test_normal_events(self):
        """Normal events pass."""
        analyzer = TemporalPatternAnalyzer()
        events = [
            Event("e1", 1.0, "request"),
            Event("e2", 5.0, "request"),
        ]

        result = analyzer.analyze(events)

        assert result.is_anomaly is False

    def test_rapid_fire_detected(self):
        """Rapid fire detected."""
        analyzer = TemporalPatternAnalyzer()
        now = time.time()
        events = [Event(f"e{i}", now + i * 0.01, "request") for i in range(5)]

        result = analyzer.analyze(events)

        assert TemporalThreat.RAPID_FIRE in result.threats

    def test_attack_sequence_detected(self):
        """Attack sequence detected."""
        analyzer = TemporalPatternAnalyzer()
        events = [
            Event("e1", 1.0, "probe"),
            Event("e2", 10.0, "exploit"),
            Event("e3", 20.0, "escalate"),
        ]

        result = analyzer.analyze(events)

        assert TemporalThreat.COORDINATED in result.threats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
