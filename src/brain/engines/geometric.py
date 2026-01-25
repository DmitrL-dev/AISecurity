"""
Geometric Kernel v2.0 - Topological Data Analysis for Prompt Security

Layers:
  1. Embedding - sentence-transformers vectorization
  2. Homology - H0 + H1 + H2 persistent homology (ripser)
  3. Landscape - Persistence landscapes for stable comparison
  4. Adaptive - Dynamic thresholds (μ + 2σ)
  5. Anomaly - Multi-signal fusion detector

Features:
  - Betti numbers (β0, β1, β2) for topological features
  - Persistence entropy and total persistence
  - Landscape distance for trajectory comparison
  - Adaptive thresholds from historical data
  - Rich explainability with topological insights
"""

import logging
import numpy as np
import hashlib
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
from sentence_transformers import SentenceTransformer

try:
    from ripser import ripser
    RIPSER_AVAILABLE = True
except ImportError:
    RIPSER_AVAILABLE = False

logger = logging.getLogger("GeometricKernel")


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class BettiNumbers:
    """Betti numbers representing topological features."""
    b0: int = 0  # Connected components
    b1: int = 0  # Loops/cycles
    b2: int = 0  # Voids/cavities

    def to_dict(self) -> dict:
        return {"b0": self.b0, "b1": self.b1, "b2": self.b2}


@dataclass
class PersistenceStats:
    """Statistics from persistence diagram."""
    entropy: float = 0.0
    total_persistence: float = 0.0
    max_lifetime: float = 0.0
    betti: BettiNumbers = field(default_factory=BettiNumbers)

    def to_dict(self) -> dict:
        return {
            "entropy": self.entropy,
            "total_persistence": self.total_persistence,
            "max_lifetime": self.max_lifetime,
            "betti": self.betti.to_dict()
        }


@dataclass
class GeometricResult:
    """Result from Geometric Kernel analysis."""
    risk_score: float = 0.0
    is_anomalous: bool = False
    anomaly_type: str = "none"
    explanation: str = ""
    stats: Optional[PersistenceStats] = None
    signals: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "tda_score": self.risk_score,
            "is_anomalous": self.is_anomalous,
            "anomaly_type": self.anomaly_type,
            "reason": self.explanation,
            "stats": self.stats.to_dict() if self.stats else None,
            "signals": self.signals
        }


# ============================================================================
# Homology Engine (H0, H1, H2)
# ============================================================================

class HomologyEngine:
    """Computes persistent homology up to H2."""

    def __init__(self, max_dim: int = 2):
        self.max_dim = max_dim

    def compute(self, embeddings: np.ndarray) -> Tuple[PersistenceStats, List[np.ndarray]]:
        """
        Compute persistent homology.

        Returns:
            (PersistenceStats, list of persistence diagrams per dimension)
        """
        stats = PersistenceStats()
        diagrams = []

        if not RIPSER_AVAILABLE or len(embeddings) < 3:
            return stats, diagrams

        try:
            # Compute persistence with ripser
            result = ripser(embeddings, maxdim=self.max_dim)
            diagrams = result['dgms']

            # Calculate Betti numbers and statistics
            betti = BettiNumbers()
            total_entropy = 0.0
            total_persistence = 0.0
            max_lifetime = 0.0

            for dim, dgm in enumerate(diagrams):
                if len(dgm) == 0:
                    continue

                # Filter finite points
                finite = dgm[dgm[:, 1] < np.inf]

                if len(finite) > 0:
                    lifetimes = finite[:, 1] - finite[:, 0]
                    lifetimes = lifetimes[lifetimes > 0]

                    if len(lifetimes) > 0:
                        # Update Betti number
                        if dim == 0:
                            betti.b0 = len(lifetimes)
                        elif dim == 1:
                            betti.b1 = len(lifetimes)
                        elif dim == 2:
                            betti.b2 = len(lifetimes)

                        # Total persistence
                        total_persistence += lifetimes.sum()

                        # Max lifetime
                        max_lifetime = max(max_lifetime, lifetimes.max())

                        # Entropy
                        p = lifetimes / lifetimes.sum()
                        total_entropy -= np.sum(p * np.log(p + 1e-10))

            stats = PersistenceStats(
                entropy=total_entropy,
                total_persistence=total_persistence,
                max_lifetime=max_lifetime,
                betti=betti
            )

        except Exception as e:
            logger.warning(f"Homology computation failed: {e}")

        return stats, diagrams


# ============================================================================
# Persistence Landscape Layer
# ============================================================================

class PersistenceLandscape:
    """Computes persistence landscapes for stable vectorization."""

    def __init__(self, num_landscapes: int = 5, resolution: int = 100):
        self.num_landscapes = num_landscapes
        self.resolution = resolution

    def compute(self, diagram: np.ndarray) -> np.ndarray:
        """
        Compute persistence landscape from diagram.
        Returns array of shape (num_landscapes, resolution).
        """
        if len(diagram) == 0:
            return np.zeros((self.num_landscapes, self.resolution))

        # Filter finite points
        finite = diagram[diagram[:, 1] < np.inf]
        if len(finite) == 0:
            return np.zeros((self.num_landscapes, self.resolution))

        # Get range
        births = finite[:, 0]
        deaths = finite[:, 1]
        t_min = births.min()
        t_max = deaths.max()

        if t_max <= t_min:
            return np.zeros((self.num_landscapes, self.resolution))

        # Create grid
        t_grid = np.linspace(t_min, t_max, self.resolution)

        # Compute tent functions for each point
        landscapes = np.zeros((self.num_landscapes, self.resolution))

        for i, t in enumerate(t_grid):
            # Compute height at t for each bar
            heights = []
            for b, d in zip(births, deaths):
                mid = (b + d) / 2
                half_life = (d - b) / 2
                if b <= t <= d:
                    height = half_life - abs(t - mid)
                    heights.append(height)

            # Sort heights descending
            heights = sorted(heights, reverse=True)

            # Fill landscapes
            for k in range(min(len(heights), self.num_landscapes)):
                landscapes[k, i] = heights[k]

        return landscapes

    def distance(self, landscape1: np.ndarray, landscape2: np.ndarray) -> float:
        """L2 distance between two landscapes."""
        if landscape1.shape != landscape2.shape:
            return 0.0
        return float(np.linalg.norm(landscape1 - landscape2))


# ============================================================================
# Adaptive Threshold
# ============================================================================

class AdaptiveThreshold:
    """Adaptive thresholds based on historical statistics."""

    def __init__(self, window_size: int = 100, num_sigmas: float = 2.0):
        self.window_size = window_size
        self.num_sigmas = num_sigmas
        self.history: Dict[str, deque] = {}

    def update(self, metric_name: str, value: float):
        """Add new observation."""
        if metric_name not in self.history:
            self.history[metric_name] = deque(maxlen=self.window_size)
        self.history[metric_name].append(value)

    def get_threshold(self, metric_name: str, default: float = 2.0) -> float:
        """Get adaptive threshold (μ + num_sigmas * σ)."""
        if metric_name not in self.history or len(self.history[metric_name]) < 10:
            return default

        values = np.array(self.history[metric_name])
        return float(values.mean() + self.num_sigmas * values.std())

    def is_anomalous(self, metric_name: str, value: float, default_threshold: float = 2.0) -> bool:
        """Check if value exceeds adaptive threshold."""
        threshold = self.get_threshold(metric_name, default_threshold)
        return value > threshold


# ============================================================================
# Main Geometric Kernel
# ============================================================================

class GeometricKernel:
    """
    Geometric Kernel v2.0 - Multi-layer TDA for prompt security.

    Uses topological data analysis to detect:
    - Unusual prompt trajectories
    - Topic drift attacks
    - Adversarial embedding manipulation
    """

    def __init__(self, max_history: int = 100, cache_size: int = 1000):
        logger.info("Initializing Geometric Kernel v2.0 (TDA with H2)...")

        # Embedding model (shared or lazy loaded)
        self._embedder = None

        # Embedding cache (key: text hash, value: embedding)
        self._embedding_cache: Dict[str, np.ndarray] = {}
        self._cache_size = cache_size
        self._cache_hits = 0
        self._cache_misses = 0

        # History
        self.embedding_history: List[np.ndarray] = []
        self.max_history = max_history

        # Layers
        self.homology = HomologyEngine(max_dim=2)
        self.landscape = PersistenceLandscape()
        self.thresholds = AdaptiveThreshold()

        # Baseline landscape (for comparison)
        self.baseline_landscape: Optional[np.ndarray] = None

        logger.info("Geometric Kernel v2.0 initialized with embedding cache.")

    @property
    def embedder(self):
        """Lazy load embedder."""
        if self._embedder is None:
            self._embedder = SentenceTransformer('all-MiniLM-L6-v2')
        return self._embedder

    def _get_text_hash(self, text: str) -> str:
        """Get hash of text for cache key."""
        return hashlib.md5(text.encode()).hexdigest()

    def embed(self, text: str) -> np.ndarray:
        """Convert text to embedding vector with caching."""
        text_hash = self._get_text_hash(text)

        # Check cache
        if text_hash in self._embedding_cache:
            self._cache_hits += 1
            return self._embedding_cache[text_hash]

        # Cache miss - compute embedding
        self._cache_misses += 1
        embedding = self.embedder.encode(text, convert_to_numpy=True)

        # Evict oldest if cache full (simple FIFO)
        if len(self._embedding_cache) >= self._cache_size:
            oldest_key = next(iter(self._embedding_cache))
            del self._embedding_cache[oldest_key]

        self._embedding_cache[text_hash] = embedding
        return embedding

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "cache_size": len(self._embedding_cache),
            "hit_rate_percent": round(hit_rate, 1)
        }

    def add_to_history(self, embedding: np.ndarray):
        """Add embedding to history."""
        self.embedding_history.append(embedding)
        if len(self.embedding_history) > self.max_history:
            self.embedding_history = self.embedding_history[-self.max_history:]

    def _compute_signals(self, embedding: np.ndarray,
                         stats: PersistenceStats,
                         diagrams: List[np.ndarray]) -> Dict[str, float]:
        """Compute all anomaly signals."""
        signals = {}

        # 1. Distance from centroid
        if len(self.embedding_history) >= 5:
            recent = np.array(self.embedding_history[-20:])
            centroid = recent.mean(axis=0)
            signals["centroid_distance"] = float(
                np.linalg.norm(embedding - centroid))

        # 2. Entropy signal
        signals["entropy"] = stats.entropy

        # 3. Total persistence
        signals["total_persistence"] = stats.total_persistence

        # 4. Betti number ratio (H1/H0 indicates loop complexity)
        if stats.betti.b0 > 0:
            signals["loop_ratio"] = stats.betti.b1 / stats.betti.b0

        # 5. H2 presence (voids indicate complex structure)
        signals["has_voids"] = float(stats.betti.b2 > 0)

        # 6. Landscape distance from baseline
        if len(diagrams) > 1 and self.baseline_landscape is not None:
            current_landscape = self.landscape.compute(
                diagrams[1])  # H1 diagram
            signals["landscape_distance"] = self.landscape.distance(
                current_landscape, self.baseline_landscape
            )

        return signals

    def _update_baseline(self, diagrams: List[np.ndarray]):
        """Update baseline landscape from current diagrams."""
        if len(diagrams) > 1:
            self.baseline_landscape = self.landscape.compute(diagrams[1])

    def analyze(self, text: str) -> dict:
        """
        Analyze text using TDA.

        Returns dict with:
          - tda_score: Risk score (0-100)
          - is_anomalous: Boolean flag
          - anomaly_type: Type of detected anomaly
          - reason: Human-readable explanation
          - stats: Persistence statistics
          - signals: Raw signal values
        """
        result = GeometricResult()

        # Get embedding
        embedding = self.embed(text)
        self.add_to_history(embedding)

        # Need sufficient history
        if len(self.embedding_history) < 10:
            result.explanation = "Insufficient history for TDA"
            return result.to_dict()

        # Compute homology on recent embeddings
        recent = np.array(self.embedding_history[-30:])
        stats, diagrams = self.homology.compute(recent)
        result.stats = stats

        # Compute signals
        signals = self._compute_signals(embedding, stats, diagrams)
        result.signals = signals

        # Update adaptive thresholds
        for name, value in signals.items():
            self.thresholds.update(name, value)

        # Check for anomalies
        anomalies = []
        risk_contributions = []

        # Distance anomaly
        if "centroid_distance" in signals:
            if self.thresholds.is_anomalous("centroid_distance", signals["centroid_distance"], 1.5):
                anomalies.append("trajectory_deviation")
                risk_contributions.append(
                    min(30, signals["centroid_distance"] * 15))

        # Entropy anomaly
        if self.thresholds.is_anomalous("entropy", signals["entropy"], 2.0):
            anomalies.append("high_entropy")
            risk_contributions.append(min(20, signals["entropy"] * 5))

        # Loop ratio anomaly
        if signals.get("loop_ratio", 0) > 2.0:
            anomalies.append("complex_topology")
            risk_contributions.append(20)

        # Void detection (H2)
        if signals.get("has_voids", 0) > 0:
            anomalies.append("topological_void")
            risk_contributions.append(15)

        # Landscape drift
        if signals.get("landscape_distance", 0) > 5.0:
            anomalies.append("landscape_drift")
            risk_contributions.append(
                min(25, signals["landscape_distance"] * 3))

        # Aggregate result
        if anomalies:
            result.is_anomalous = True
            result.anomaly_type = anomalies[0]
            result.risk_score = min(50.0, sum(risk_contributions))
            result.explanation = f"TDA anomaly: {', '.join(anomalies)} | " \
                f"β0={stats.betti.b0}, β1={stats.betti.b1}, β2={stats.betti.b2}"
        else:
            result.explanation = "Normal topology"
            # Update baseline if normal
            if len(self.embedding_history) > 20:
                self._update_baseline(diagrams)

        return result.to_dict()


# ============================================================================
# Backward Compatibility
# ============================================================================

# Legacy alias
def compute_persistence(embeddings: np.ndarray) -> dict:
    """Legacy function for backward compatibility."""
    engine = HomologyEngine(max_dim=1)
    stats, _ = engine.compute(embeddings)
    return {
        "entropy": stats.entropy,
        "num_features": stats.betti.b0 + stats.betti.b1
    }
