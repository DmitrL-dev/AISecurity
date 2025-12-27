"""
Temporal Pattern Analyzer Engine - Time-Based Attack Detection

Analyzes temporal patterns for attacks:
- Time series analysis
- Sequence detection
- Anomaly timing
- Attack cadence

Addresses: OWASP ASI-01 (Timing Attacks)
Research: temporal_analysis_deep_dive.md
Invention: Temporal Pattern Analyzer (#44)
"""

import time
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from base_engine import Severity, Action  # Base classes

logger = logging.getLogger("TemporalPatternAnalyzer")


# ============================================================================
# Data Classes
# ============================================================================


class TemporalThreat(Enum):
    """Types of temporal threats."""

    RAPID_FIRE = "rapid_fire"
    SLOW_DRIP = "slow_drip"
    COORDINATED = "coordinated"
    TIMING_ATTACK = "timing_attack"


@dataclass
class Event:
    """A timed event."""

    event_id: str
    timestamp: float
    event_type: str
    source: str = ""


@dataclass
class TemporalResult:
    """Result from temporal analysis."""

    is_anomaly: bool
    threats: List[TemporalThreat] = field(default_factory=list)
    pattern_score: float = 0.0
    interval_stats: Dict = field(default_factory=dict)
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_anomaly": self.is_anomaly,
            "threats": [t.value for t in self.threats],
            "pattern_score": self.pattern_score,
            "interval_stats": self.interval_stats,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Interval Analyzer
# ============================================================================


class IntervalAnalyzer:
    """
    Analyzes time intervals.
    """

    def analyze(self, events: List[Event]) -> Dict:
        """Analyze intervals between events."""
        if len(events) < 2:
            return {"count": len(events), "avg_interval": 0, "min_interval": 0}

        sorted_events = sorted(events, key=lambda e: e.timestamp)
        intervals = []

        for i in range(1, len(sorted_events)):
            interval = sorted_events[i].timestamp - \
                sorted_events[i - 1].timestamp
            intervals.append(interval)

        return {
            "count": len(events),
            "avg_interval": sum(intervals) / len(intervals),
            "min_interval": min(intervals),
            "max_interval": max(intervals),
        }


# ============================================================================
# Rapid Fire Detector
# ============================================================================


class RapidFireDetector:
    """
    Detects rapid-fire attack patterns.
    """

    def __init__(self, threshold: float = 0.1):
        self.threshold = threshold  # Min interval threshold

    def detect(self, stats: Dict) -> bool:
        """Detect rapid fire pattern."""
        min_interval = stats.get("min_interval", float("inf"))
        return min_interval < self.threshold


# ============================================================================
# Slow Drip Detector
# ============================================================================


class SlowDripDetector:
    """
    Detects slow drip attack patterns.
    """

    def __init__(self, consistency: float = 0.1):
        self.consistency = consistency

    def detect(self, stats: Dict) -> bool:
        """Detect suspiciously consistent intervals."""
        if stats.get("count", 0) < 5:
            return False

        avg = stats.get("avg_interval", 0)
        min_int = stats.get("min_interval", 0)
        max_int = stats.get("max_interval", float("inf"))

        if avg == 0:
            return False

        # Check if intervals are suspiciously consistent
        variance = (max_int - min_int) / avg if avg > 0 else 0
        return variance < self.consistency


# ============================================================================
# Sequence Detector
# ============================================================================


class SequenceDetector:
    """
    Detects attack sequences.
    """

    ATTACK_SEQUENCES = [
        ["probe", "exploit", "escalate"],
        ["recon", "inject", "exfil"],
    ]

    def detect(self, events: List[Event]) -> bool:
        """Detect known attack sequences."""
        types = [
            e.event_type for e in sorted(
                events,
                key=lambda e: e.timestamp)]

        for seq in self.ATTACK_SEQUENCES:
            if self._is_subsequence(seq, types):
                return True

        return False

    def _is_subsequence(self, seq: List[str], types: List[str]) -> bool:
        """Check if seq is subsequence of types."""
        seq_idx = 0
        for t in types:
            if seq_idx < len(seq) and t == seq[seq_idx]:
                seq_idx += 1
        return seq_idx == len(seq)


# ============================================================================
# Main Engine
# ============================================================================


class TemporalPatternAnalyzer:
    """
    Temporal Pattern Analyzer - Time-Based Attack Detection

    Temporal analysis:
    - Interval analysis
    - Pattern detection
    - Sequence detection

    Invention #44 from research.
    Addresses OWASP ASI-01.
    """

    def __init__(self):
        self.interval_analyzer = IntervalAnalyzer()
        self.rapid_fire = RapidFireDetector()
        self.slow_drip = SlowDripDetector()
        self.sequence = SequenceDetector()

        logger.info("TemporalPatternAnalyzer initialized")

    def analyze(self, events: List[Event]) -> TemporalResult:
        """
        Analyze temporal patterns.

        Args:
            events: List of events

        Returns:
            TemporalResult
        """
        start = time.time()

        threats = []

        # Analyze intervals
        stats = self.interval_analyzer.analyze(events)

        # Check patterns
        if self.rapid_fire.detect(stats):
            threats.append(TemporalThreat.RAPID_FIRE)

        if self.slow_drip.detect(stats):
            threats.append(TemporalThreat.SLOW_DRIP)

        if self.sequence.detect(events):
            threats.append(TemporalThreat.COORDINATED)

        is_anomaly = len(threats) > 0
        pattern_score = len(threats) / 3.0

        if is_anomaly:
            logger.warning(f"Temporal threats: {[t.value for t in threats]}")

        return TemporalResult(
            is_anomaly=is_anomaly,
            threats=threats,
            pattern_score=pattern_score,
            interval_stats=stats,
            explanation=f"Events: {stats.get('count', 0)}, Threats: {len(threats)}",
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_analyzer: Optional[TemporalPatternAnalyzer] = None


def get_analyzer() -> TemporalPatternAnalyzer:
    global _default_analyzer
    if _default_analyzer is None:
        _default_analyzer = TemporalPatternAnalyzer()
    return _default_analyzer
