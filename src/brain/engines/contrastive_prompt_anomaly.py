"""
Contrastive Prompt Anomaly Engine - Self-Supervised Detection

Uses contrastive learning for anomaly detection:
- Positive/negative pair analysis
- No labels required
- Embedding space distances
- Anomaly scoring

Addresses: OWASP ASI-01 (Prompt Injection)
Research: self_supervised_learning_deep_dive.md
Invention: Contrastive Prompt Anomaly (#22)
"""

import math
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("ContrastivePromptAnomaly")


# ============================================================================
# Data Classes
# ============================================================================


class ContrastiveAnomalyType(Enum):
    """Types of contrastive anomalies."""

    DISTANT_EMBEDDING = "distant_embedding"
    NEGATIVE_SIMILAR = "negative_similar"
    CLUSTER_OUTLIER = "cluster_outlier"


@dataclass
class ContrastiveResult:
    """Result from contrastive analysis."""

    is_anomaly: bool
    anomaly_score: float
    positive_distance: float
    negative_distance: float
    anomaly_types: List[ContrastiveAnomalyType] = field(default_factory=list)
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_anomaly": self.is_anomaly,
            "anomaly_score": self.anomaly_score,
            "positive_distance": self.positive_distance,
            "negative_distance": self.negative_distance,
            "types": [t.value for t in self.anomaly_types],
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Simple Embedder
# ============================================================================


class SimpleEmbedder:
    """
    Simple text embedder (character n-gram based).
    """

    def __init__(self, dim: int = 64, n: int = 3):
        self.dim = dim
        self.n = n

    def embed(self, text: str) -> List[float]:
        """Embed text to vector."""
        text = text.lower()

        # Character n-grams
        ngrams = []
        for i in range(len(text) - self.n + 1):
            ngrams.append(text[i: i + self.n])

        # Hash to vector
        vec = [0.0] * self.dim
        for ng in ngrams:
            idx = hash(ng) % self.dim
            vec[idx] += 1.0

        # Normalize
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def distance(self, v1: List[float], v2: List[float]) -> float:
        """Euclidean distance."""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))

    def cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Cosine similarity."""
        dot = sum(a * b for a, b in zip(v1, v2))
        n1 = math.sqrt(sum(a * a for a in v1)) or 1.0
        n2 = math.sqrt(sum(b * b for b in v2)) or 1.0
        return dot / (n1 * n2)


# ============================================================================
# Contrastive Learner
# ============================================================================


class ContrastiveLearner:
    """
    Learns contrastive representations.
    """

    def __init__(self, margin: float = 0.5):
        self.margin = margin
        self._positives: deque = deque(maxlen=100)
        self._negatives: deque = deque(maxlen=50)
        self._embedder = SimpleEmbedder()

    def add_positive(self, text: str) -> None:
        """Add positive (normal) example."""
        emb = self._embedder.embed(text)
        self._positives.append(emb)

    def add_negative(self, text: str) -> None:
        """Add negative (attack) example."""
        emb = self._embedder.embed(text)
        self._negatives.append(emb)

    def analyze(self, text: str) -> Tuple[float, float, float]:
        """
        Analyze text against learned examples.

        Returns:
            (anomaly_score, avg_pos_distance, avg_neg_distance)
        """
        emb = self._embedder.embed(text)

        # Calculate average distance to positives
        if self._positives:
            pos_dist = sum(
                self._embedder.distance(emb, p) for p in self._positives
            ) / len(self._positives)
        else:
            pos_dist = 0.0

        # Calculate average distance to negatives
        if self._negatives:
            neg_dist = sum(
                self._embedder.distance(emb, n) for n in self._negatives
            ) / len(self._negatives)
        else:
            neg_dist = float("inf")

        # Anomaly if closer to negatives than positives
        if neg_dist < float("inf"):
            score = pos_dist / (neg_dist + 0.01)
        else:
            score = pos_dist

        return min(1.0, score), pos_dist, neg_dist


# ============================================================================
# Cluster Analyzer
# ============================================================================


class ClusterAnalyzer:
    """
    Analyzes cluster membership.
    """

    def __init__(self):
        self._embedder = SimpleEmbedder()
        self._cluster_center: Optional[List[float]] = None
        self._cluster_radius: float = 0.0
        self._samples: deque = deque(maxlen=100)

    def update(self, text: str) -> None:
        """Update cluster with new sample."""
        emb = self._embedder.embed(text)
        self._samples.append(emb)

        # Recalculate center
        if self._samples:
            dim = len(self._samples[0])
            center = [0.0] * dim
            for s in self._samples:
                for i in range(dim):
                    center[i] += s[i]
            self._cluster_center = [c / len(self._samples) for c in center]

            # Calculate radius
            if len(self._samples) > 5:
                distances = [
                    self._embedder.distance(s, self._cluster_center)
                    for s in self._samples
                ]
                self._cluster_radius = sum(distances) / len(distances) * 2

    def is_outlier(self, text: str) -> Tuple[bool, float]:
        """Check if text is cluster outlier."""
        if not self._cluster_center or self._cluster_radius == 0:
            return False, 0.0

        emb = self._embedder.embed(text)
        distance = self._embedder.distance(emb, self._cluster_center)

        is_out = distance > self._cluster_radius
        return is_out, distance / (self._cluster_radius or 1.0)


# ============================================================================
# Main Engine
# ============================================================================


class ContrastivePromptAnomaly:
    """
    Contrastive Prompt Anomaly - Self-Supervised Detection

    Zero-label anomaly detection:
    - Contrastive learning
    - Cluster analysis
    - Embedding distances

    Invention #22 from research.
    Addresses OWASP ASI-01.
    """

    def __init__(self, threshold: float = 0.7):
        self.learner = ContrastiveLearner()
        self.cluster = ClusterAnalyzer()
        self.threshold = threshold

        logger.info("ContrastivePromptAnomaly initialized")

    def train_positive(self, texts: List[str]) -> None:
        """Train on positive (normal) examples."""
        for text in texts:
            self.learner.add_positive(text)
            self.cluster.update(text)

    def train_negative(self, texts: List[str]) -> None:
        """Train on negative (attack) examples."""
        for text in texts:
            self.learner.add_negative(text)

    def analyze(self, text: str) -> ContrastiveResult:
        """
        Analyze text for anomalies.

        Args:
            text: Input text

        Returns:
            ContrastiveResult
        """
        start = time.time()

        anomaly_types = []

        # Contrastive analysis
        score, pos_dist, neg_dist = self.learner.analyze(text)

        if score > self.threshold:
            anomaly_types.append(ContrastiveAnomalyType.DISTANT_EMBEDDING)

        if neg_dist < pos_dist and neg_dist < float("inf"):
            anomaly_types.append(ContrastiveAnomalyType.NEGATIVE_SIMILAR)

        # Cluster analysis
        is_outlier, outlier_ratio = self.cluster.is_outlier(text)
        if is_outlier:
            anomaly_types.append(ContrastiveAnomalyType.CLUSTER_OUTLIER)
            score = max(score, outlier_ratio)

        is_anomaly = len(anomaly_types) > 0

        if is_anomaly:
            logger.warning(
                f"Contrastive anomaly: {[t.value for t in anomaly_types]}")

        return ContrastiveResult(
            is_anomaly=is_anomaly,
            anomaly_score=score,
            positive_distance=pos_dist,
            negative_distance=neg_dist if neg_dist < float("inf") else -1,
            anomaly_types=anomaly_types,
            explanation=f"Score: {score:.2f}" if is_anomaly else "Normal",
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_engine: Optional[ContrastivePromptAnomaly] = None


def get_engine() -> ContrastivePromptAnomaly:
    global _default_engine
    if _default_engine is None:
        _default_engine = ContrastivePromptAnomaly()
    return _default_engine
