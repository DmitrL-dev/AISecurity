"""
Strange Math v3 — Fractal Analysis Module

Fractal dimension analysis for prompt anomaly detection.

Features:
- Box-counting dimension
- Higuchi fractal dimension
- Multifractal spectrum
- Self-similarity detection

Author: SENTINEL Team
Date: 2025-12-16
"""

import logging
import math
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

logger = logging.getLogger("StrangeMath.Fractal")


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class FractalResult:
    """Result of fractal dimension analysis."""

    box_counting_dim: float
    higuchi_dim: float
    hurst_exponent: float
    is_anomaly: bool
    anomaly_score: float
    interpretation: str


@dataclass
class MultifractalResult:
    """Result of multifractal analysis."""

    alpha_min: float  # Minimum singularity
    alpha_max: float  # Maximum singularity
    spectrum_width: float  # Alpha range
    f_alpha_max: float  # Peak of f(alpha)
    is_multifractal: bool


# ============================================================================
# Fractal Engine
# ============================================================================


class FractalEngine:
    """
    Fractal dimension analysis for anomaly detection.

    Theory:
    - Text with high fractal dimension → complex, potentially obfuscated
    - Self-similar patterns → repetitive attack structures
    - Multifractal → layered complexity (sophisticated attacks)
    """

    # Thresholds
    NORMAL_DIM_RANGE = (1.0, 1.6)  # Expected for natural text
    HIGH_DIM_THRESHOLD = 1.8
    LOW_DIM_THRESHOLD = 0.8

    def __init__(self):
        logger.info("Initializing Fractal Analysis Engine v3...")

        self.anomaly_threshold = 0.6
        self._stats = {
            "analyses": 0,
            "anomalies_detected": 0,
        }

    def analyze(self, text: str) -> FractalResult:
        """
        Full fractal analysis of text.

        Args:
            text: Input text

        Returns:
            FractalResult with dimensions and anomaly score
        """
        if len(text) < 20:
            return FractalResult(
                box_counting_dim=1.0,
                higuchi_dim=1.0,
                hurst_exponent=0.5,
                is_anomaly=False,
                anomaly_score=0.0,
                interpretation="Text too short for analysis",
            )

        self._stats["analyses"] += 1

        # Convert text to time series
        series = self._text_to_series(text)

        # Calculate dimensions
        box_dim = self._box_counting_dimension(series)
        higuchi_dim = self._higuchi_dimension(series)
        hurst = self._hurst_exponent(series)

        # Calculate anomaly score
        anomaly_score = self._calculate_anomaly_score(
            box_dim, higuchi_dim, hurst)
        is_anomaly = anomaly_score >= self.anomaly_threshold

        if is_anomaly:
            self._stats["anomalies_detected"] += 1

        interpretation = self._interpret_results(box_dim, higuchi_dim, hurst)

        return FractalResult(
            box_counting_dim=round(box_dim, 3),
            higuchi_dim=round(higuchi_dim, 3),
            hurst_exponent=round(hurst, 3),
            is_anomaly=is_anomaly,
            anomaly_score=round(anomaly_score, 3),
            interpretation=interpretation,
        )

    def _text_to_series(self, text: str) -> np.ndarray:
        """Convert text to numeric time series."""
        # Use character codes normalized
        values = [ord(c) for c in text]
        series = np.array(values, dtype=float)

        # Normalize to [0, 1]
        if series.max() > series.min():
            series = (series - series.min()) / (series.max() - series.min())

        return series

    def _box_counting_dimension(
        self,
        series: np.ndarray,
        num_boxes: int = 10,
    ) -> float:
        """
        Calculate box-counting dimension.

        The dimension D is estimated from:
        N(r) ∝ r^(-D)

        where N(r) is the number of boxes of size r needed to cover the data.
        """
        n = len(series)
        if n < 4:
            return 1.0

        # Box sizes (epsilon values)
        sizes = np.linspace(1, n // 2, num_boxes, dtype=int)
        sizes = sizes[sizes > 0]

        if len(sizes) < 2:
            return 1.0

        box_counts = []
        for size in sizes:
            # Count boxes needed
            num_steps = n // size
            if num_steps < 1:
                continue

            count = 0
            for i in range(num_steps):
                start = i * size
                end = min(start + size, n)
                segment = series[start:end]
                if len(segment) > 0:
                    # Box height = max - min in segment
                    height = segment.max() - segment.min()
                    # Number of vertical boxes
                    count += max(1, int(height * size) + 1)

            box_counts.append((size, count))

        if len(box_counts) < 2:
            return 1.0

        # Linear regression in log-log space
        log_sizes = np.log([1.0 / s for s, _ in box_counts])
        log_counts = np.log([c for _, c in box_counts])

        # Slope = dimension
        coeffs = np.polyfit(log_sizes, log_counts, 1)
        dimension = coeffs[0]

        return max(0.0, min(2.0, dimension))

    def _higuchi_dimension(
        self,
        series: np.ndarray,
        k_max: int = 10,
    ) -> float:
        """
        Calculate Higuchi fractal dimension.

        More robust than box-counting for time series.
        """
        n = len(series)
        if n < 4:
            return 1.0

        k_max = min(k_max, n // 4)
        if k_max < 2:
            return 1.0

        lengths = []

        for k in range(1, k_max + 1):
            length_sum = 0.0

            for m in range(1, k + 1):
                # Create subsequence
                indices = range(m - 1, n, k)
                if len(list(indices)) < 2:
                    continue

                # Calculate length
                L = 0.0
                prev_idx = m - 1
                for idx in range(m - 1 + k, n, k):
                    L += abs(series[idx] - series[prev_idx])
                    prev_idx = idx

                # Normalize
                num_points = (n - m) // k
                if num_points > 0:
                    L = L * (n - 1) / (k * k * num_points)
                    length_sum += L

            if length_sum > 0:
                lengths.append((k, length_sum / k))

        if len(lengths) < 2:
            return 1.0

        # Linear regression in log-log space
        log_k = np.log([1.0 / k for k, _ in lengths])
        log_L = np.log([L for _, L in lengths])

        coeffs = np.polyfit(log_k, log_L, 1)
        dimension = coeffs[0]

        return max(1.0, min(2.0, dimension))

    def _hurst_exponent(self, series: np.ndarray) -> float:
        """
        Calculate Hurst exponent using R/S analysis.

        H > 0.5: Persistent (trending)
        H = 0.5: Random walk
        H < 0.5: Anti-persistent (mean-reverting)
        """
        n = len(series)
        if n < 20:
            return 0.5

        # Divide into subseries
        max_k = min(n // 2, 100)
        sizes = [k for k in range(10, max_k) if n % k == 0 or k < n // 2]

        if len(sizes) < 3:
            return 0.5

        rs_values = []

        for size in sizes[:10]:  # Limit for performance
            num_subseries = n // size

            rs_sum = 0.0
            for i in range(num_subseries):
                subseries = series[i * size:(i + 1) * size]

                # Mean and deviations
                mean = subseries.mean()
                deviations = subseries - mean
                cumsum = np.cumsum(deviations)

                # Range and std
                R = cumsum.max() - cumsum.min()
                S = subseries.std()

                if S > 0:
                    rs_sum += R / S

            if num_subseries > 0:
                rs_values.append((size, rs_sum / num_subseries))

        if len(rs_values) < 2:
            return 0.5

        # Linear regression in log-log space
        log_n = np.log([s for s, _ in rs_values])
        log_rs = np.log([rs for _, rs in rs_values])

        coeffs = np.polyfit(log_n, log_rs, 1)
        hurst = coeffs[0]

        return max(0.0, min(1.0, hurst))

    def _calculate_anomaly_score(
        self,
        box_dim: float,
        higuchi_dim: float,
        hurst: float,
    ) -> float:
        """Calculate combined anomaly score."""
        score = 0.0

        # Box dimension anomaly
        if box_dim > self.HIGH_DIM_THRESHOLD:
            score += 0.3 * (box_dim - self.HIGH_DIM_THRESHOLD)
        elif box_dim < self.LOW_DIM_THRESHOLD:
            score += 0.3 * (self.LOW_DIM_THRESHOLD - box_dim)

        # Higuchi dimension anomaly
        avg_dim = (box_dim + higuchi_dim) / 2
        if avg_dim > 1.7:
            score += 0.3

        # Hurst exponent anomaly (extreme values)
        if hurst > 0.85 or hurst < 0.15:
            score += 0.2

        # High persistence or anti-persistence
        if abs(hurst - 0.5) > 0.35:
            score += 0.2

        return min(1.0, score)

    def _interpret_results(
        self,
        box_dim: float,
        higuchi_dim: float,
        hurst: float,
    ) -> str:
        """Generate human-readable interpretation."""
        parts = []

        # Dimension interpretation
        if box_dim > 1.7:
            parts.append("High complexity (possible obfuscation)")
        elif box_dim < 0.9:
            parts.append("Low complexity (repetitive pattern)")
        else:
            parts.append("Normal complexity")

        # Hurst interpretation
        if hurst > 0.7:
            parts.append("Strong persistence (trending pattern)")
        elif hurst < 0.3:
            parts.append("Anti-persistent (unusual variation)")

        return "; ".join(parts)

    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return self._stats


# ============================================================================
# Factory
# ============================================================================


_fractal_engine: Optional[FractalEngine] = None


def get_fractal_engine() -> FractalEngine:
    """Get or create fractal engine."""
    global _fractal_engine
    if _fractal_engine is None:
        _fractal_engine = FractalEngine()
    return _fractal_engine
