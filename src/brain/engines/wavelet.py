"""
Strange Math v3 — Wavelet Transform Module

Wavelet analysis for multi-scale anomaly detection.

Features:
- Discrete Wavelet Transform (DWT)
- Wavelet packet decomposition
- Multi-resolution analysis
- Transient detection

Author: SENTINEL Team
Date: 2025-12-16
"""

import logging
import math
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

logger = logging.getLogger("StrangeMath.Wavelet")


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class WaveletResult:
    """Result of wavelet analysis."""

    energy_distribution: Dict[str, float]  # Energy at each level
    dominant_scale: int
    anomaly_score: float
    is_anomaly: bool
    transients_detected: int
    interpretation: str


@dataclass
class TransientEvent:
    """Detected transient/spike in signal."""

    position: int
    scale: int
    magnitude: float
    significance: float


# ============================================================================
# Wavelet Bases
# ============================================================================


class WaveletBasis:
    """Simple wavelet basis functions."""

    @staticmethod
    def haar_low(x: np.ndarray) -> np.ndarray:
        """Haar low-pass filter (scaling function)."""
        n = len(x)
        if n % 2 != 0:
            x = np.append(x, x[-1])
            n += 1
        return (x[::2] + x[1::2]) / np.sqrt(2)

    @staticmethod
    def haar_high(x: np.ndarray) -> np.ndarray:
        """Haar high-pass filter (wavelet function)."""
        n = len(x)
        if n % 2 != 0:
            x = np.append(x, x[-1])
            n += 1
        return (x[::2] - x[1::2]) / np.sqrt(2)

    @staticmethod
    def db4_low(x: np.ndarray) -> np.ndarray:
        """Daubechies-4 approximation (simplified)."""
        # Simplified DB4 using moving average
        kernel = np.array([0.4829, 0.8365, 0.2241, -0.1294])
        padded = np.pad(x, (len(kernel) - 1, 0), mode='edge')
        result = np.convolve(padded, kernel, mode='valid')
        return result[::2]

    @staticmethod
    def db4_high(x: np.ndarray) -> np.ndarray:
        """Daubechies-4 detail (simplified)."""
        kernel = np.array([-0.1294, -0.2241, 0.8365, -0.4829])
        padded = np.pad(x, (len(kernel) - 1, 0), mode='edge')
        result = np.convolve(padded, kernel, mode='valid')
        return result[::2]


# ============================================================================
# Wavelet Engine
# ============================================================================


class WaveletEngine:
    """
    Wavelet transform analysis for multi-scale anomaly detection.

    Theory:
    - Low frequencies → global structure
    - High frequencies → local details/noise
    - Energy concentration → feature localization
    - Transients → sudden changes (injection attempts)
    """

    def __init__(self, wavelet: str = "haar"):
        logger.info(f"Initializing Wavelet Engine v3 ({wavelet})...")

        self.wavelet = wavelet
        self.max_levels = 8
        self.anomaly_threshold = 0.55

        self._stats = {
            "analyses": 0,
            "anomalies_detected": 0,
            "transients_found": 0,
        }

    def analyze(self, text: str) -> WaveletResult:
        """
        Full wavelet analysis of text.

        Args:
            text: Input text

        Returns:
            WaveletResult with multi-scale analysis
        """
        if len(text) < 16:
            return WaveletResult(
                energy_distribution={},
                dominant_scale=0,
                anomaly_score=0.0,
                is_anomaly=False,
                transients_detected=0,
                interpretation="Text too short",
            )

        self._stats["analyses"] += 1

        # Convert to signal
        signal = self._text_to_signal(text)

        # Decompose
        coeffs = self._dwt_decompose(signal)

        # Calculate energy distribution
        energy = self._calculate_energy(coeffs)

        # Find dominant scale
        dominant = max(energy.items(), key=lambda x: x[1])[
            0] if energy else "d1"
        dominant_scale = int(dominant[1:]) if dominant[0] == 'd' else 0

        # Detect transients
        transients = self._detect_transients(coeffs)

        # Calculate anomaly score
        anomaly_score = self._calculate_anomaly_score(energy, transients)
        is_anomaly = anomaly_score >= self.anomaly_threshold

        if is_anomaly:
            self._stats["anomalies_detected"] += 1
        self._stats["transients_found"] += len(transients)

        interpretation = self._interpret_results(
            energy, transients, dominant_scale)

        return WaveletResult(
            energy_distribution=energy,
            dominant_scale=dominant_scale,
            anomaly_score=round(anomaly_score, 3),
            is_anomaly=is_anomaly,
            transients_detected=len(transients),
            interpretation=interpretation,
        )

    def _text_to_signal(self, text: str) -> np.ndarray:
        """Convert text to signal for wavelet analysis."""
        # Pad to power of 2
        n = len(text)
        next_pow2 = 2 ** math.ceil(math.log2(max(n, 16)))

        signal = np.zeros(next_pow2)
        for i, c in enumerate(text):
            signal[i] = ord(c)

        # Normalize
        if signal.max() > signal.min():
            signal = (signal - signal.mean()) / signal.std()

        return signal

    def _dwt_decompose(
        self,
        signal: np.ndarray,
        levels: Optional[int] = None,
    ) -> Dict[str, np.ndarray]:
        """
        Discrete Wavelet Transform decomposition.

        Returns dict with:
        - 'a<n>': approximation at level n
        - 'd<n>': detail at level n
        """
        if levels is None:
            levels = min(self.max_levels, int(math.log2(len(signal))) - 2)

        coeffs = {}
        current = signal

        for level in range(1, levels + 1):
            if len(current) < 4:
                break

            if self.wavelet == "haar":
                approx = WaveletBasis.haar_low(current)
                detail = WaveletBasis.haar_high(current)
            else:  # db4
                approx = WaveletBasis.db4_low(current)
                detail = WaveletBasis.db4_high(current)

            coeffs[f"d{level}"] = detail
            current = approx

        coeffs[f"a{levels}"] = current

        return coeffs

    def _calculate_energy(
        self,
        coeffs: Dict[str, np.ndarray],
    ) -> Dict[str, float]:
        """Calculate energy at each decomposition level."""
        total_energy = sum(np.sum(c ** 2) for c in coeffs.values())

        if total_energy == 0:
            return {}

        return {
            key: round(np.sum(val ** 2) / total_energy, 4)
            for key, val in coeffs.items()
        }

    def _detect_transients(
        self,
        coeffs: Dict[str, np.ndarray],
    ) -> List[TransientEvent]:
        """Detect transient events (spikes) in detail coefficients."""
        transients = []

        for level_name, detail in coeffs.items():
            if not level_name.startswith('d'):
                continue

            level = int(level_name[1:])

            # Calculate threshold (MAD-based)
            median = np.median(np.abs(detail))
            threshold = 3.0 * median / 0.6745  # MAD estimator

            # Find spikes
            for i, val in enumerate(detail):
                if abs(val) > threshold:
                    transients.append(TransientEvent(
                        position=i * (2 ** level),  # Map to original position
                        scale=level,
                        magnitude=abs(val),
                        significance=abs(val) /
                        threshold if threshold > 0 else 0,
                    ))

        return transients[:20]  # Limit

    def _calculate_anomaly_score(
        self,
        energy: Dict[str, float],
        transients: List[TransientEvent],
    ) -> float:
        """Calculate wavelet-based anomaly score."""
        score = 0.0

        # Energy concentration anomaly
        if energy:
            # High energy in high-frequency details = noisy/obfuscated
            high_freq_energy = sum(
                v for k, v in energy.items()
                if k.startswith('d') and int(k[1:]) <= 2
            )
            if high_freq_energy > 0.5:
                score += 0.3

            # Very uniform energy distribution = synthetic
            values = list(energy.values())
            if len(values) > 2:
                std = np.std(values)
                if std < 0.05:  # Too uniform
                    score += 0.2

        # Transient-based anomaly
        if transients:
            # Many transients = potential injection markers
            if len(transients) > 10:
                score += 0.3
            elif len(transients) > 5:
                score += 0.15

            # High-significance transients
            max_sig = max(t.significance for t in transients)
            if max_sig > 5:
                score += 0.2

        return min(1.0, score)

    def _interpret_results(
        self,
        energy: Dict[str, float],
        transients: List[TransientEvent],
        dominant_scale: int,
    ) -> str:
        """Generate interpretation."""
        parts = []

        if dominant_scale <= 2:
            parts.append("High-frequency dominant (detailed/noisy)")
        elif dominant_scale >= 4:
            parts.append("Low-frequency dominant (smooth structure)")

        if len(transients) > 5:
            parts.append(f"{len(transients)} transients detected")

        if not parts:
            parts.append("Normal wavelet structure")

        return "; ".join(parts)

    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return self._stats


# ============================================================================
# Factory
# ============================================================================


_wavelet_engine: Optional[WaveletEngine] = None


def get_wavelet_engine() -> WaveletEngine:
    """Get or create wavelet engine."""
    global _wavelet_engine
    if _wavelet_engine is None:
        _wavelet_engine = WaveletEngine()
    return _wavelet_engine
