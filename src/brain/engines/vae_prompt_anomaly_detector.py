"""
VAE Prompt Anomaly Detector Engine - Reconstruction-Based Detection

Uses autoencoder-style anomaly detection:
- Reconstruction error analysis
- Latent space anomaly detection
- Statistical threshold learning
- Zero-shot anomaly scoring

Addresses: OWASP ASI-01 (Prompt Injection Detection)
Research: autoencoder_anomaly_deep_dive.md
Invention: VAE Prompt Anomaly Detector (#31)
"""

import math
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("VAEPromptAnomalyDetector")


# ============================================================================
# Data Classes
# ============================================================================


class AnomalyType(Enum):
    """Types of detected anomalies."""

    HIGH_RECONSTRUCTION = "high_reconstruction_error"
    LATENT_OUTLIER = "latent_space_outlier"
    DISTRIBUTION_SHIFT = "distribution_shift"
    STATISTICAL_ANOMALY = "statistical_anomaly"


@dataclass
class AnomalyResult:
    """Result from anomaly detection."""

    is_anomaly: bool
    anomaly_score: float
    reconstruction_error: float
    anomaly_types: List[AnomalyType] = field(default_factory=list)
    threshold_used: float = 0.0
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_anomaly": self.is_anomaly,
            "anomaly_score": self.anomaly_score,
            "reconstruction_error": self.reconstruction_error,
            "types": [t.value for t in self.anomaly_types],
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Simple Encoder
# ============================================================================


class SimpleEncoder:
    """
    Simple text encoder (word frequency based).
    Production would use neural network.
    """

    def __init__(self, dim: int = 32):
        self.dim = dim
        self._vocab: Dict[str, int] = {}
        self._vocab_size = 0

    def encode(self, text: str) -> List[float]:
        """Encode text to latent vector."""
        words = text.lower().split()

        # Update vocab
        for word in words:
            if word not in self._vocab:
                self._vocab[word] = self._vocab_size
                self._vocab_size += 1

        # Simple bag-of-words encoding
        vec = [0.0] * self.dim
        for word in words:
            idx = self._vocab[word] % self.dim
            vec[idx] += 1.0

        # Normalize
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def decode(self, latent: List[float]) -> List[float]:
        """Decode (just return latent for simple impl)."""
        return latent


# ============================================================================
# Reconstruction Analyzer
# ============================================================================


class ReconstructionAnalyzer:
    """
    Analyzes reconstruction error.
    """

    def __init__(self):
        self._encoder = SimpleEncoder()

    def get_reconstruction_error(self, text: str) -> Tuple[float, List[float]]:
        """
        Get reconstruction error for text.

        Returns:
            (error, latent_vector)
        """
        latent = self._encoder.encode(text)
        reconstructed = self._encoder.decode(latent)

        # MSE between original encoding and reconstruction
        original = self._encoder.encode(text)
        error = sum((a - b) ** 2 for a, b in zip(original, reconstructed))
        error = math.sqrt(error / len(original))

        return error, latent


# ============================================================================
# Statistical Threshold
# ============================================================================


class AdaptiveThreshold:
    """
    Learns adaptive threshold from data.
    """

    def __init__(self, window_size: int = 100, std_multiplier: float = 2.5):
        self._history: deque = deque(maxlen=window_size)
        self._std_multiplier = std_multiplier
        self._base_threshold = 0.5

    def update(self, value: float) -> None:
        """Update threshold with new value."""
        self._history.append(value)

    def get_threshold(self) -> float:
        """Get current threshold."""
        if len(self._history) < 10:
            return self._base_threshold

        mean = sum(self._history) / len(self._history)
        variance = sum((x - mean) ** 2 for x in self._history) / \
            len(self._history)
        std = math.sqrt(variance)

        return mean + self._std_multiplier * std

    def is_anomaly(self, value: float) -> bool:
        """Check if value is anomalous."""
        return value > self.get_threshold()


# ============================================================================
# Latent Space Analyzer
# ============================================================================


class LatentSpaceAnalyzer:
    """
    Analyzes latent space for outliers.
    """

    def __init__(self, history_size: int = 100):
        self._history: deque = deque(maxlen=history_size)

    def add(self, latent: List[float]) -> None:
        """Add latent vector to history."""
        self._history.append(latent)

    def distance_from_centroid(self, latent: List[float]) -> float:
        """Calculate distance from centroid."""
        if not self._history:
            return 0.0

        # Calculate centroid
        dim = len(latent)
        centroid = [0.0] * dim

        for vec in self._history:
            for i in range(dim):
                centroid[i] += vec[i]

        centroid = [c / len(self._history) for c in centroid]

        # Calculate distance
        distance = math.sqrt(
            sum((a - b) ** 2 for a, b in zip(latent, centroid)))
        return distance

    def is_outlier(self, latent: List[float], threshold: float = 1.5) -> bool:
        """Check if latent is outlier."""
        if len(self._history) < 10:
            return False

        distance = self.distance_from_centroid(latent)

        # Calculate average distance
        avg_dist = sum(self.distance_from_centroid(v) for v in self._history) / len(
            self._history
        )

        return distance > threshold * avg_dist if avg_dist > 0 else False


# ============================================================================
# Main Engine
# ============================================================================


class VAEPromptAnomalyDetector:
    """
    VAE Prompt Anomaly Detector - Reconstruction-Based Detection

    Comprehensive anomaly detection:
    - Reconstruction error
    - Latent space analysis
    - Adaptive thresholds

    Invention #31 from research.
    Addresses OWASP ASI-01.
    """

    def __init__(
        self,
        base_threshold: float = 0.5,
        learn_threshold: bool = True,
    ):
        self.recon_analyzer = ReconstructionAnalyzer()
        self.threshold = AdaptiveThreshold()
        self.latent_analyzer = LatentSpaceAnalyzer()

        self.base_threshold = base_threshold
        self.learn_threshold = learn_threshold

        logger.info("VAEPromptAnomalyDetector initialized")

    def analyze(self, text: str, is_training: bool = False) -> AnomalyResult:
        """
        Analyze text for anomalies.

        Args:
            text: Input text
            is_training: If true, treat as normal data

        Returns:
            AnomalyResult
        """
        start = time.time()

        anomaly_types = []

        # Get reconstruction error
        recon_error, latent = self.recon_analyzer.get_reconstruction_error(
            text)

        # Check reconstruction threshold
        current_threshold = self.threshold.get_threshold()
        is_recon_anomaly = recon_error > current_threshold

        if is_recon_anomaly and not is_training:
            anomaly_types.append(AnomalyType.HIGH_RECONSTRUCTION)

        # Check latent space
        is_latent_outlier = self.latent_analyzer.is_outlier(latent)

        if is_latent_outlier and not is_training:
            anomaly_types.append(AnomalyType.LATENT_OUTLIER)

        # Update models if training
        if is_training or not anomaly_types:
            self.threshold.update(recon_error)
            self.latent_analyzer.add(latent)

        # Calculate anomaly score
        score = min(1.0, recon_error / max(current_threshold, 0.01))
        if is_latent_outlier:
            score = min(1.0, score * 1.3)

        is_anomaly = len(anomaly_types) > 0

        if is_anomaly:
            logger.warning(
                f"Anomaly detected: {[t.value for t in anomaly_types]}")

        return AnomalyResult(
            is_anomaly=is_anomaly,
            anomaly_score=score,
            reconstruction_error=recon_error,
            anomaly_types=anomaly_types,
            threshold_used=current_threshold,
            explanation=(
                f"Types: {[t.value for t in anomaly_types]}"
                if anomaly_types
                else "Normal"
            ),
            latency_ms=(time.time() - start) * 1000,
        )

    def train(self, texts: List[str]) -> None:
        """Train on normal texts."""
        for text in texts:
            self.analyze(text, is_training=True)


# ============================================================================
# Convenience
# ============================================================================

_default_detector: Optional[VAEPromptAnomalyDetector] = None


def get_detector() -> VAEPromptAnomalyDetector:
    global _default_detector
    if _default_detector is None:
        _default_detector = VAEPromptAnomalyDetector()
    return _default_detector
