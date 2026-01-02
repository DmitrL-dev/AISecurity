"""
Semantic Drift Detector Engine - Embedding-Based Attack Detection

Detects semantic manipulation through embedding analysis:
- Embedding distance monitoring
- Semantic shift detection
- Context drift analysis
- Adversarial perturbation detection

Addresses: OWASP ASI-01 (Prompt Injection via Semantic Shift)
Research: semantic_drift_detection_deep_dive.md
Invention: Semantic Drift Detector (#34)
"""

import math
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from collections import deque

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("SemanticDriftDetector")


# ============================================================================
# Data Classes
# ============================================================================


class DriftType(Enum):
    """Types of semantic drift."""

    INTENT_SHIFT = "intent_shift"
    TOPIC_DRIFT = "topic_drift"
    SENTIMENT_FLIP = "sentiment_flip"
    ADVERSARIAL_PERTURBATION = "adversarial_perturbation"
    MEEA_DRIFT = "meea_drift"  # Mere Exposure Effect Attack - gradual toxicity


@dataclass
class EmbeddingPoint:
    """Point in embedding space."""

    vector: List[float]
    text: str
    timestamp: float = 0.0
    label: str = ""


@dataclass
class DriftResult:
    """Result from drift detection."""

    is_safe: bool
    drift_detected: bool
    drift_type: Optional[DriftType] = None
    drift_score: float = 0.0
    distance: float = 0.0
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "drift_detected": self.drift_detected,
            "drift_type": self.drift_type.value if self.drift_type else None,
            "drift_score": self.drift_score,
            "distance": self.distance,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Embedding Analyzer
# ============================================================================


class EmbeddingAnalyzer:
    """
    Analyzes embeddings for semantic properties.
    """

    @staticmethod
    def cosine_similarity(v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity."""
        if len(v1) != len(v2) or len(v1) == 0:
            return 0.0

        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)

    @staticmethod
    def euclidean_distance(v1: List[float], v2: List[float]) -> float:
        """Compute Euclidean distance."""
        if len(v1) != len(v2):
            return float("inf")

        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))

    @staticmethod
    def magnitude(v: List[float]) -> float:
        """Compute vector magnitude."""
        return math.sqrt(sum(x * x for x in v))


# ============================================================================
# Baseline Manager
# ============================================================================


class BaselineManager:
    """
    Manages baseline embeddings for comparison.
    """

    def __init__(self, window_size: int = 10):
        self._baselines: Dict[str, EmbeddingPoint] = {}
        self._history: Dict[str, deque] = {}
        self._window_size = window_size

    def set_baseline(self, key: str, point: EmbeddingPoint) -> None:
        """Set baseline for a key."""
        self._baselines[key] = point
        if key not in self._history:
            self._history[key] = deque(maxlen=self._window_size)

    def get_baseline(self, key: str) -> Optional[EmbeddingPoint]:
        """Get baseline for key."""
        return self._baselines.get(key)

    def add_to_history(self, key: str, point: EmbeddingPoint) -> None:
        """Add point to history."""
        if key not in self._history:
            self._history[key] = deque(maxlen=self._window_size)
        self._history[key].append(point)

    def get_history(self, key: str) -> List[EmbeddingPoint]:
        """Get history for key."""
        return list(self._history.get(key, []))


# ============================================================================
# Drift Classifier
# ============================================================================


class DriftClassifier:
    """
    Classifies types of semantic drift.
    """

    def __init__(
        self,
        intent_threshold: float = 0.3,
        topic_threshold: float = 0.4,
        perturbation_threshold: float = 0.1,
    ):
        self.intent_threshold = intent_threshold
        self.topic_threshold = topic_threshold
        self.perturbation_threshold = perturbation_threshold

    def classify(
        self, baseline: EmbeddingPoint, current: EmbeddingPoint, similarity: float
    ) -> Tuple[bool, Optional[DriftType], float]:
        """
        Classify drift type.

        Returns:
            (is_drift, drift_type, severity)
        """
        distance = 1.0 - similarity

        # Small perturbation - possible adversarial
        if distance > 0.05 and distance < self.perturbation_threshold:
            # Check if texts are very similar but embeddings differ
            text_sim = self._text_similarity(baseline.text, current.text)
            if text_sim > 0.9:
                return True, DriftType.ADVERSARIAL_PERTURBATION, distance

        # Intent shift
        if distance > self.intent_threshold:
            return True, DriftType.INTENT_SHIFT, distance

        # Topic drift
        if distance > self.topic_threshold:
            return True, DriftType.TOPIC_DRIFT, distance

        return False, None, distance

    def _text_similarity(self, t1: str, t2: str) -> float:
        """Simple text similarity (word overlap)."""
        words1 = set(t1.lower().split())
        words2 = set(t2.lower().split())

        if not words1 or not words2:
            return 0.0

        overlap = len(words1 & words2)
        return overlap / max(len(words1), len(words2))


# ============================================================================
# Main Engine
# ============================================================================


class SemanticDriftDetector:
    """
    Semantic Drift Detector - Embedding-Based Attack Detection

    Comprehensive drift detection:
    - Baseline comparison
    - History tracking
    - Drift classification

    Invention #34 from research.
    Addresses OWASP ASI-01.
    """

    def __init__(
        self,
        drift_threshold: float = 0.3,
        window_size: int = 10,
    ):
        self.analyzer = EmbeddingAnalyzer()
        self.baseline_manager = BaselineManager(window_size)
        self.classifier = DriftClassifier(intent_threshold=drift_threshold)

        self.drift_threshold = drift_threshold

        logger.info("SemanticDriftDetector initialized")

    def set_baseline(
            self, key: str, embedding: List[float], text: str = "") -> None:
        """Set baseline embedding."""
        point = EmbeddingPoint(
            vector=embedding, text=text, timestamp=time.time(), label="baseline"
        )
        self.baseline_manager.set_baseline(key, point)

    def detect(
        self,
        key: str,
        current_embedding: List[float],
        current_text: str = "",
    ) -> DriftResult:
        """
        Detect semantic drift from baseline.

        Args:
            key: Baseline key
            current_embedding: Current embedding vector
            current_text: Current text (optional)

        Returns:
            DriftResult
        """
        start = time.time()

        baseline = self.baseline_manager.get_baseline(key)

        if not baseline:
            return DriftResult(
                is_safe=True,
                drift_detected=False,
                explanation="No baseline set",
                latency_ms=(time.time() - start) * 1000,
            )

        # Compute similarity
        similarity = self.analyzer.cosine_similarity(
            baseline.vector, current_embedding)

        distance = 1.0 - similarity

        # Create current point
        current = EmbeddingPoint(
            vector=current_embedding,
            text=current_text,
            timestamp=time.time(),
        )

        # Classify drift
        is_drift, drift_type, severity = self.classifier.classify(
            baseline, current, similarity
        )

        # Add to history
        self.baseline_manager.add_to_history(key, current)

        if is_drift:
            logger.warning(
                f"Drift detected: {drift_type.value}, distance={distance:.3f}"
            )

        return DriftResult(
            is_safe=not is_drift,
            drift_detected=is_drift,
            drift_type=drift_type,
            drift_score=severity,
            distance=distance,
            explanation=(
                f"Drift: {drift_type.value}" if is_drift else "Within threshold"
            ),
            latency_ms=(time.time() - start) * 1000,
        )

    def detect_trajectory_drift(
        self,
        key: str,
        embeddings: List[List[float]],
    ) -> DriftResult:
        """Detect drift across trajectory of embeddings."""
        start = time.time()

        if len(embeddings) < 2:
            return DriftResult(
                is_safe=True,
                drift_detected=False,
                explanation="Insufficient trajectory",
                latency_ms=(time.time() - start) * 1000,
            )

        # Check consecutive drift
        max_drift = 0.0
        for i in range(1, len(embeddings)):
            sim = self.analyzer.cosine_similarity(
                embeddings[i - 1], embeddings[i])
            drift = 1.0 - sim
            max_drift = max(max_drift, drift)

        is_drift = max_drift > self.drift_threshold

        return DriftResult(
            is_safe=not is_drift,
            drift_detected=is_drift,
            drift_type=DriftType.TOPIC_DRIFT if is_drift else None,
            drift_score=max_drift,
            distance=max_drift,
            explanation=f"Max trajectory drift: {max_drift:.3f}",
            latency_ms=(time.time() - start) * 1000,
        )

    def detect_meea_drift(
        self,
        key: str,
        toxicity_scores: List[float],
        threshold_increment: float = 0.05,
    ) -> DriftResult:
        """
        Detect Mere Exposure Effect Attack (MEEA).

        MEEA gradually shifts safety thresholds through a sequence of
        low-toxicity prompts, each slightly more toxic than the last.

        Args:
            key: Session key
            toxicity_scores: List of toxicity scores (0-1) over conversation
            threshold_increment: Max allowed increment per turn

        Returns:
            DriftResult with MEEA_DRIFT if gradual escalation detected
        """
        start = time.time()

        if len(toxicity_scores) < 3:
            return DriftResult(
                is_safe=True,
                drift_detected=False,
                explanation="Insufficient history for MEEA detection",
                latency_ms=(time.time() - start) * 1000,
            )

        # Analyze toxicity progression
        increments = []
        for i in range(1, len(toxicity_scores)):
            delta = toxicity_scores[i] - toxicity_scores[i - 1]
            increments.append(delta)

        # Count gradual increases (MEEA signature)
        gradual_increases = sum(1 for d in increments if 0 < d <= threshold_increment)

        # Check for monotonic drift
        total_drift = toxicity_scores[-1] - toxicity_scores[0]
        avg_increment = total_drift / len(increments) if increments else 0

        # MEEA indicators:
        # 1. Many small positive increments
        # 2. Overall upward trend
        # 3. No large jumps (would trigger normal filters)

        meea_ratio = gradual_increases / len(increments) if increments else 0
        is_meea = (
            meea_ratio > 0.5
            and total_drift > 0.15
            and max(increments) < threshold_increment * 2
        )

        severity = total_drift if is_meea else 0.0

        if is_meea:
            logger.warning(
                f"MEEA drift detected: {gradual_increases} gradual increments, "
                f"total drift={total_drift:.3f}"
            )

        return DriftResult(
            is_safe=not is_meea,
            drift_detected=is_meea,
            drift_type=DriftType.MEEA_DRIFT if is_meea else None,
            drift_score=severity,
            distance=total_drift,
            explanation=(
                f"MEEA: {gradual_increases}/{len(increments)} gradual increments"
                if is_meea
                else "No MEEA pattern"
            ),
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_detector: Optional[SemanticDriftDetector] = None


def get_detector() -> SemanticDriftDetector:
    global _default_detector
    if _default_detector is None:
        _default_detector = SemanticDriftDetector()
    return _default_detector
