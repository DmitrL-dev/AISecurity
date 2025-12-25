"""
Semantic Tide — Threat Level Prediction System

Predicts attack "waves" based on:
- Time patterns (hour, day, timezone activity)
- Historical attack frequency
- External events (conferences, releases, CVE publications)
- Real-time attack rate

Usage:
    tide = SemanticTide()
    level = tide.get_current_level()  # 0-10
    forecast = tide.get_forecast(hours=6)  # Next 6 hours
    adjusted_threshold = tide.adjust_threshold(base=70.0)
"""

import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import deque
import math


@dataclass
class TideLevel:
    """Current threat tide level."""
    level: float  # 0-10
    trend: str    # "rising", "falling", "stable"
    confidence: float  # 0-1
    factors: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def severity(self) -> str:
        """Human-readable severity."""
        if self.level < 3:
            return "LOW"
        elif self.level < 6:
            return "MODERATE"
        elif self.level < 8:
            return "HIGH"
        else:
            return "CRITICAL"


@dataclass
class TideForecast:
    """Forecast for future threat levels."""
    predictions: List[Tuple[datetime, float]]  # [(time, level), ...]
    peak_time: Optional[datetime]
    peak_level: float
    next_low: Optional[datetime]


class SemanticTide:
    """
    Predicts attack waves based on temporal patterns and real-time data.

    Allows dynamic adjustment of security thresholds:
    - Low tide: Relax thresholds (reduce false positives)
    - High tide: Tighten thresholds (prevent attacks)
    """

    # Hourly base threat levels (0-23, UTC)
    # Based on typical attack patterns: peaks during US/EU business hours
    HOURLY_PATTERNS = {
        0: 0.3, 1: 0.2, 2: 0.2, 3: 0.2, 4: 0.3, 5: 0.4,
        6: 0.5, 7: 0.6, 8: 0.7, 9: 0.8, 10: 0.9, 11: 0.9,
        12: 0.8, 13: 0.9, 14: 1.0, 15: 1.0, 16: 0.9, 17: 0.8,
        18: 0.7, 19: 0.6, 20: 0.5, 21: 0.4, 22: 0.4, 23: 0.3,
    }

    # Day of week multipliers (0=Monday)
    WEEKDAY_MULTIPLIERS = {
        0: 1.0,   # Monday - normal
        1: 1.0,   # Tuesday - normal
        2: 1.0,   # Wednesday - normal
        3: 1.1,   # Thursday - slightly higher
        4: 1.2,   # Friday - experiments before weekend
        5: 0.7,   # Saturday - lower
        6: 0.6,   # Sunday - lowest
    }

    # Known high-risk periods (month, day) -> multiplier
    HIGH_RISK_DATES = {
        (8, 1): 2.0,    # DEF CON (first week August)
        (8, 2): 2.0,
        (8, 3): 2.0,
        (8, 4): 2.0,
        (8, 5): 2.0,
        (8, 6): 1.8,    # Black Hat (week before DEF CON)
        (8, 7): 1.8,
        (8, 8): 1.8,
        (12, 24): 0.5,  # Christmas Eve - low
        (12, 25): 0.4,  # Christmas - very low
        (12, 31): 0.5,  # New Year's Eve - low
        (1, 1): 0.4,    # New Year's Day - very low
    }

    def __init__(self, window_minutes: int = 60):
        """
        Initialize Semantic Tide.

        Args:
            window_minutes: Time window for real-time attack rate calculation
        """
        self.window_minutes = window_minutes
        self._attack_times: deque = deque(
            maxlen=10000)  # Recent attack timestamps
        self._last_level: Optional[TideLevel] = None
        self._baseline_attack_rate = 10.0  # Expected attacks per hour (normal)

    def record_attack(self, timestamp: Optional[datetime] = None):
        """Record an attack occurrence for real-time rate calculation."""
        if timestamp is None:
            timestamp = datetime.now()
        self._attack_times.append(timestamp)

    def _get_recent_attack_rate(self) -> float:
        """Calculate attacks per hour in recent window."""
        if not self._attack_times:
            return 0.0

        now = datetime.now()
        window_start = now - timedelta(minutes=self.window_minutes)

        recent_attacks = sum(
            1 for t in self._attack_times if t >= window_start)
        hours = self.window_minutes / 60.0

        return recent_attacks / hours if hours > 0 else 0.0

    def _get_temporal_factor(self, dt: Optional[datetime] = None) -> Tuple[float, Dict[str, float]]:
        """
        Calculate threat factor based on time patterns.

        Returns:
            (factor, breakdown): Overall factor and component breakdown
        """
        if dt is None:
            dt = datetime.now()

        # Hour of day factor
        hour_factor = self.HOURLY_PATTERNS.get(dt.hour, 0.5)

        # Day of week factor
        weekday_factor = self.WEEKDAY_MULTIPLIERS.get(dt.weekday(), 1.0)

        # Special date factor
        date_key = (dt.month, dt.day)
        date_factor = self.HIGH_RISK_DATES.get(date_key, 1.0)

        # Combine factors
        combined = hour_factor * weekday_factor * date_factor

        breakdown = {
            "hour": hour_factor,
            "weekday": weekday_factor,
            "date": date_factor,
        }

        return combined, breakdown

    def _get_realtime_factor(self) -> Tuple[float, Dict[str, float]]:
        """
        Calculate threat factor based on real-time attack rate.

        Returns:
            (factor, breakdown): Factor and component values
        """
        current_rate = self._get_recent_attack_rate()

        # Ratio to baseline
        if self._baseline_attack_rate > 0:
            ratio = current_rate / self._baseline_attack_rate
        else:
            ratio = 1.0

        # Convert ratio to factor (capped at 3x)
        factor = min(3.0, max(0.5, ratio))

        breakdown = {
            "attack_rate": current_rate,
            "baseline_rate": self._baseline_attack_rate,
            "ratio": ratio,
        }

        return factor, breakdown

    def get_current_level(self) -> TideLevel:
        """
        Get current threat tide level.

        Returns:
            TideLevel with 0-10 scale
        """
        now = datetime.now()

        # Get temporal factor (0-1 base, can exceed with multipliers)
        temporal_factor, temporal_breakdown = self._get_temporal_factor(now)

        # Get real-time factor
        realtime_factor, realtime_breakdown = self._get_realtime_factor()

        # Combine: 60% temporal, 40% real-time
        combined_factor = (temporal_factor * 0.6) + (realtime_factor * 0.4)

        # Scale to 0-10
        level = min(10.0, max(0.0, combined_factor * 5.0))

        # Determine trend
        if self._last_level:
            diff = level - self._last_level.level
            if diff > 0.5:
                trend = "rising"
            elif diff < -0.5:
                trend = "falling"
            else:
                trend = "stable"
        else:
            trend = "stable"

        # Confidence based on data availability
        confidence = min(1.0, len(self._attack_times) /
                         100.0) if self._attack_times else 0.5

        result = TideLevel(
            level=round(level, 2),
            trend=trend,
            confidence=round(confidence, 2),
            factors={
                "temporal": round(temporal_factor, 3),
                "realtime": round(realtime_factor, 3),
                **temporal_breakdown,
            },
            timestamp=now,
        )

        self._last_level = result
        return result

    def get_forecast(self, hours: int = 6) -> TideForecast:
        """
        Forecast threat levels for next N hours.

        Args:
            hours: Number of hours to forecast

        Returns:
            TideForecast with predictions
        """
        now = datetime.now()
        predictions = []
        peak_level = 0.0
        peak_time = None
        lowest_level = 10.0
        next_low = None

        for h in range(hours + 1):
            future_time = now + timedelta(hours=h)
            temporal_factor, _ = self._get_temporal_factor(future_time)

            # For forecast, assume current real-time factor persists (conservative)
            realtime_factor, _ = self._get_realtime_factor()
            combined = (temporal_factor * 0.6) + (realtime_factor * 0.4)
            level = min(10.0, max(0.0, combined * 5.0))

            predictions.append((future_time, round(level, 2)))

            if level > peak_level:
                peak_level = level
                peak_time = future_time

            if level < lowest_level:
                lowest_level = level
                next_low = future_time

        return TideForecast(
            predictions=predictions,
            peak_time=peak_time,
            peak_level=round(peak_level, 2),
            next_low=next_low,
        )

    def adjust_threshold(self, base_threshold: float, sensitivity: float = 0.2) -> float:
        """
        Adjust security threshold based on tide level.

        Args:
            base_threshold: Base threshold (e.g., 70.0)
            sensitivity: How much to adjust (0.1 = ±10%, 0.2 = ±20%)

        Returns:
            Adjusted threshold
        """
        level = self.get_current_level()

        # Level 0-3: Relax (increase threshold)
        # Level 4-6: Normal
        # Level 7-10: Tighten (decrease threshold)

        if level.level < 3:
            # Low tide: relax by up to sensitivity%
            adjustment = 1.0 + (sensitivity * (3 - level.level) / 3)
        elif level.level > 6:
            # High tide: tighten by up to sensitivity%
            adjustment = 1.0 - (sensitivity * (level.level - 6) / 4)
        else:
            adjustment = 1.0

        adjusted = base_threshold * adjustment

        # Ensure reasonable bounds (never go below 50 or above 90 for risk_score)
        if base_threshold == 70.0:  # Risk score
            adjusted = max(50.0, min(90.0, adjusted))

        return round(adjusted, 2)

    def get_status_summary(self) -> dict:
        """Get summary for dashboard/logging."""
        level = self.get_current_level()
        forecast = self.get_forecast(hours=6)

        return {
            "current_level": level.level,
            "severity": level.severity,
            "trend": level.trend,
            "confidence": level.confidence,
            "peak_next_6h": forecast.peak_level,
            "peak_time": forecast.peak_time.strftime("%H:%M") if forecast.peak_time else None,
            "factors": level.factors,
        }


# Singleton instance
_tide: Optional[SemanticTide] = None


def get_semantic_tide() -> SemanticTide:
    """Get or create singleton SemanticTide instance."""
    global _tide
    if _tide is None:
        _tide = SemanticTide()
    return _tide


# Convenience functions
def get_threat_level() -> TideLevel:
    """Get current threat tide level."""
    return get_semantic_tide().get_current_level()


def get_adjusted_threshold(base: float = 70.0) -> float:
    """Get threshold adjusted for current tide."""
    return get_semantic_tide().adjust_threshold(base)
