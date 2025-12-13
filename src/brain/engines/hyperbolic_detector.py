"""
Hyperbolic Embedding Detector — SENTINEL Advanced Math Engine

Uses hyperbolic geometry (Poincaré ball model) for attack detection.
Based on research showing hierarchical data structures in embedding spaces.

Philosophy:
- Attacks often form distinct clusters in hyperbolic space
- Hierarchical prompt structures map naturally to hyperbolic geometry
- Distance-based anomaly detection in curved space

Dependencies: geoopt (Riemannian optimization library)

Author: SENTINEL Team  
Date: 2025-12-13
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum

# Geoopt for hyperbolic geometry
try:
    import torch
    import geoopt
    from geoopt.manifolds import PoincareBall
    GEOOPT_AVAILABLE = True
except ImportError:
    GEOOPT_AVAILABLE = False
    torch = None
    geoopt = None

logger = logging.getLogger("HyperbolicDetector")


# ============================================================================
# Data Classes
# ============================================================================


class DetectionMode(str, Enum):
    """Detection mode for hyperbolic analysis."""
    DISTANCE = "distance"           # Pure distance-based
    CLUSTERING = "clustering"       # Cluster membership
    CURVATURE = "curvature"         # Local curvature analysis
    HIERARCHICAL = "hierarchical"   # Tree-like structure detection


@dataclass
class HyperbolicPoint:
    """A point in the Poincaré ball."""
    coordinates: np.ndarray
    label: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def norm(self) -> float:
        """Euclidean norm (should be < 1 in Poincaré ball)."""
        return float(np.linalg.norm(self.coordinates))


@dataclass
class HyperbolicCluster:
    """A cluster in hyperbolic space."""
    center: HyperbolicPoint
    radius: float  # Hyperbolic radius
    members: List[HyperbolicPoint] = field(default_factory=list)
    label: str = ""


@dataclass
class HyperbolicAnalysisResult:
    """Result of hyperbolic analysis."""
    is_anomalous: bool
    anomaly_score: float  # 0-1
    nearest_cluster: Optional[str] = None
    hyperbolic_distance: float = 0.0
    detection_mode: DetectionMode = DetectionMode.DISTANCE
    explanation: str = ""


# ============================================================================
# Poincaré Ball Operations
# ============================================================================


class PoincareBallOps:
    """
    Mathematical operations in the Poincaré ball model.

    The Poincaré ball is the unit ball with hyperbolic metric:
    ds² = 4 / (1 - |x|²)² * |dx|²

    Properties:
    - Geodesics are circular arcs perpendicular to boundary
    - Distances grow exponentially near boundary
    - Naturally captures hierarchical structure
    """

    def __init__(self, curvature: float = -1.0, dimension: int = 64):
        self.c = -curvature  # Positive value for computations
        self.dim = dimension

        if GEOOPT_AVAILABLE:
            self.manifold = PoincareBall(c=self.c)
        else:
            self.manifold = None
            logger.warning("geoopt not available, using numpy fallback")

    def hyperbolic_distance(self, x: np.ndarray, y: np.ndarray) -> float:
        """
        Compute hyperbolic distance in Poincaré ball.

        d(x,y) = arcosh(1 + 2 * ||x-y||² / ((1-||x||²)(1-||y||²)))
        """
        x_sq = np.sum(x ** 2)
        y_sq = np.sum(y ** 2)
        diff_sq = np.sum((x - y) ** 2)

        # Clamp to avoid numerical issues near boundary
        x_sq = min(x_sq, 0.9999)
        y_sq = min(y_sq, 0.9999)

        denom = (1 - x_sq) * (1 - y_sq)
        if denom < 1e-10:
            return float('inf')

        arg = 1 + 2 * diff_sq / denom
        return float(np.arccosh(max(arg, 1.0)))

    def hyperbolic_centroid(self, points: List[np.ndarray]) -> np.ndarray:
        """
        Compute hyperbolic centroid (Einstein midpoint).

        Uses iterative algorithm for Fréchet mean.
        """
        if not points:
            return np.zeros(self.dim)

        if len(points) == 1:
            return points[0].copy()

        # Initialize with Euclidean mean projected to ball
        centroid = np.mean(points, axis=0)
        centroid = self._project_to_ball(centroid)

        # Iterative refinement (simplified)
        for _ in range(10):
            weights = []
            for p in points:
                dist = self.hyperbolic_distance(centroid, p)
                weights.append(1.0 / (1.0 + dist))

            # Weighted mean
            total_weight = sum(weights)
            new_centroid = sum(
                w * p for w, p in zip(weights, points)) / total_weight
            new_centroid = self._project_to_ball(new_centroid)

            if np.linalg.norm(new_centroid - centroid) < 1e-6:
                break
            centroid = new_centroid

        return centroid

    def mobius_addition(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """
        Möbius addition in Poincaré ball.

        x ⊕ y = ((1 + 2c⟨x,y⟩ + c|y|²)x + (1 - c|x|²)y) / 
                (1 + 2c⟨x,y⟩ + c²|x|²|y|²)
        """
        c = self.c
        x_sq = np.sum(x ** 2)
        y_sq = np.sum(y ** 2)
        xy = np.dot(x, y)

        num = (1 + 2*c*xy + c*y_sq) * x + (1 - c*x_sq) * y
        denom = 1 + 2*c*xy + c*c*x_sq*y_sq

        result = num / max(denom, 1e-10)
        return self._project_to_ball(result)

    def exponential_map(self, x: np.ndarray, v: np.ndarray) -> np.ndarray:
        """
        Exponential map: project tangent vector to manifold.

        exp_x(v) = x ⊕ (tanh(√c|v|λ_x/2) * v / (√c|v|))
        where λ_x = 2 / (1 - c|x|²) is the conformal factor
        """
        c = self.c
        x_sq = np.sum(x ** 2)
        v_norm = np.linalg.norm(v)

        if v_norm < 1e-10:
            return x.copy()

        lambda_x = 2.0 / max(1 - c * x_sq, 1e-10)

        coef = np.tanh(np.sqrt(c) * v_norm * lambda_x / 2) / \
            (np.sqrt(c) * v_norm)

        return self.mobius_addition(x, coef * v)

    def _project_to_ball(self, x: np.ndarray, eps: float = 1e-5) -> np.ndarray:
        """Project point to interior of unit ball."""
        norm = np.linalg.norm(x)
        max_norm = 1.0 - eps
        if norm >= max_norm:
            return x * (max_norm / norm)
        return x


# ============================================================================
# Hyperbolic Detector Engine
# ============================================================================


class HyperbolicDetector:
    """
    Attack detection using hyperbolic geometry.

    Key insight: Prompt embeddings often exhibit hierarchical structure
    that maps naturally to hyperbolic space. Attacks form distinct
    clusters that can be detected via hyperbolic distance metrics.

    Usage:
        detector = HyperbolicDetector()
        detector.add_attack_cluster(attack_embeddings, "injection")
        detector.add_benign_cluster(benign_embeddings, "normal")
        result = detector.analyze(new_embedding)
    """

    def __init__(
        self,
        dimension: int = 64,
        curvature: float = -1.0,
        anomaly_threshold: float = 2.0,
    ):
        self.dimension = dimension
        self.curvature = curvature
        self.anomaly_threshold = anomaly_threshold

        self.ops = PoincareBallOps(curvature, dimension)

        self.attack_clusters: List[HyperbolicCluster] = []
        self.benign_clusters: List[HyperbolicCluster] = []

        logger.info(
            f"HyperbolicDetector initialized (dim={dimension}, c={curvature})")

    def embed_to_hyperbolic(self, embedding: np.ndarray) -> np.ndarray:
        """
        Project Euclidean embedding to Poincaré ball.

        Uses exponential map from origin with scaling.
        """
        # Normalize and scale to fit in ball
        norm = np.linalg.norm(embedding)
        if norm < 1e-10:
            return np.zeros(len(embedding))

        # Scale to put most points well inside ball (0.8 max norm)
        scaled = embedding * 0.8 / (1 + norm)

        # Ensure inside ball
        return self.ops._project_to_ball(scaled)

    def add_attack_cluster(
        self,
        embeddings: List[np.ndarray],
        label: str = "attack"
    ):
        """Add a cluster of known attack patterns."""
        hyp_points = [
            HyperbolicPoint(self.embed_to_hyperbolic(e), label)
            for e in embeddings
        ]

        coords = [p.coordinates for p in hyp_points]
        center_coords = self.ops.hyperbolic_centroid(coords)
        center = HyperbolicPoint(center_coords, f"{label}_center")

        # Compute hyperbolic radius
        max_dist = max(
            self.ops.hyperbolic_distance(center_coords, p.coordinates)
            for p in hyp_points
        ) if hyp_points else 0.0

        cluster = HyperbolicCluster(
            center=center,
            radius=max_dist * 1.2,  # 20% margin
            members=hyp_points,
            label=label
        )

        self.attack_clusters.append(cluster)
        logger.info(
            f"Added attack cluster '{label}': {len(embeddings)} points, radius={max_dist:.3f}")

    def add_benign_cluster(
        self,
        embeddings: List[np.ndarray],
        label: str = "benign"
    ):
        """Add a cluster of known benign patterns."""
        hyp_points = [
            HyperbolicPoint(self.embed_to_hyperbolic(e), label)
            for e in embeddings
        ]

        coords = [p.coordinates for p in hyp_points]
        center_coords = self.ops.hyperbolic_centroid(coords)
        center = HyperbolicPoint(center_coords, f"{label}_center")

        max_dist = max(
            self.ops.hyperbolic_distance(center_coords, p.coordinates)
            for p in hyp_points
        ) if hyp_points else 0.0

        cluster = HyperbolicCluster(
            center=center,
            radius=max_dist * 1.2,
            members=hyp_points,
            label=label
        )

        self.benign_clusters.append(cluster)
        logger.info(
            f"Added benign cluster '{label}': {len(embeddings)} points")

    def analyze(
        self,
        embedding: np.ndarray,
        mode: DetectionMode = DetectionMode.DISTANCE
    ) -> HyperbolicAnalysisResult:
        """
        Analyze embedding for anomalies using hyperbolic geometry.
        """
        hyp_point = self.embed_to_hyperbolic(embedding)

        if mode == DetectionMode.DISTANCE:
            return self._analyze_distance(hyp_point)
        elif mode == DetectionMode.CLUSTERING:
            return self._analyze_clustering(hyp_point)
        else:
            return self._analyze_distance(hyp_point)

    def _analyze_distance(self, hyp_point: np.ndarray) -> HyperbolicAnalysisResult:
        """Distance-based anomaly detection."""

        # Find nearest attack cluster
        min_attack_dist = float('inf')
        nearest_attack = None

        for cluster in self.attack_clusters:
            dist = self.ops.hyperbolic_distance(
                hyp_point, cluster.center.coordinates
            )
            if dist < min_attack_dist:
                min_attack_dist = dist
                nearest_attack = cluster.label

        # Find nearest benign cluster
        min_benign_dist = float('inf')
        nearest_benign = None

        for cluster in self.benign_clusters:
            dist = self.ops.hyperbolic_distance(
                hyp_point, cluster.center.coordinates
            )
            if dist < min_benign_dist:
                min_benign_dist = dist
                nearest_benign = cluster.label

        # Compute anomaly score
        if min_attack_dist < min_benign_dist:
            # Closer to attack cluster
            is_anomalous = True
            anomaly_score = min(
                1.0, 1.0 - min_attack_dist / self.anomaly_threshold)
            nearest = nearest_attack
            explanation = f"Close to attack cluster '{nearest_attack}' (dist={min_attack_dist:.3f})"
        else:
            # Closer to benign cluster
            is_anomalous = min_benign_dist > self.anomaly_threshold
            anomaly_score = min(1.0, min_benign_dist /
                                self.anomaly_threshold - 0.5)
            anomaly_score = max(0.0, anomaly_score)
            nearest = nearest_benign

            if is_anomalous:
                explanation = f"Far from all benign clusters (dist={min_benign_dist:.3f})"
            else:
                explanation = f"Within benign cluster '{nearest_benign}'"

        return HyperbolicAnalysisResult(
            is_anomalous=is_anomalous,
            anomaly_score=anomaly_score,
            nearest_cluster=nearest,
            hyperbolic_distance=min(min_attack_dist, min_benign_dist),
            detection_mode=DetectionMode.DISTANCE,
            explanation=explanation
        )

    def _analyze_clustering(self, hyp_point: np.ndarray) -> HyperbolicAnalysisResult:
        """Cluster membership-based detection."""

        # Check membership in attack clusters
        for cluster in self.attack_clusters:
            dist = self.ops.hyperbolic_distance(
                hyp_point, cluster.center.coordinates
            )
            if dist <= cluster.radius:
                return HyperbolicAnalysisResult(
                    is_anomalous=True,
                    anomaly_score=0.9,
                    nearest_cluster=cluster.label,
                    hyperbolic_distance=dist,
                    detection_mode=DetectionMode.CLUSTERING,
                    explanation=f"Inside attack cluster '{cluster.label}'"
                )

        # Check membership in benign clusters
        for cluster in self.benign_clusters:
            dist = self.ops.hyperbolic_distance(
                hyp_point, cluster.center.coordinates
            )
            if dist <= cluster.radius:
                return HyperbolicAnalysisResult(
                    is_anomalous=False,
                    anomaly_score=0.1,
                    nearest_cluster=cluster.label,
                    hyperbolic_distance=dist,
                    detection_mode=DetectionMode.CLUSTERING,
                    explanation=f"Inside benign cluster '{cluster.label}'"
                )

        # Not in any cluster
        return HyperbolicAnalysisResult(
            is_anomalous=True,
            anomaly_score=0.5,
            nearest_cluster=None,
            hyperbolic_distance=0.0,
            detection_mode=DetectionMode.CLUSTERING,
            explanation="Point outside all known clusters"
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get detector statistics."""
        return {
            "dimension": self.dimension,
            "curvature": self.curvature,
            "attack_clusters": len(self.attack_clusters),
            "benign_clusters": len(self.benign_clusters),
            "total_attack_points": sum(len(c.members) for c in self.attack_clusters),
            "total_benign_points": sum(len(c.members) for c in self.benign_clusters),
            "geoopt_available": GEOOPT_AVAILABLE,
        }


# ============================================================================
# Factory Function
# ============================================================================


def create_hyperbolic_detector(
    dimension: int = 64,
    curvature: float = -1.0
) -> HyperbolicDetector:
    """Create a HyperbolicDetector instance."""
    return HyperbolicDetector(dimension=dimension, curvature=curvature)


if __name__ == "__main__":
    # Quick test
    detector = create_hyperbolic_detector(dimension=8)

    # Add some test clusters
    np.random.seed(42)
    attack_emb = [np.random.randn(8) + [1, 0, 0, 0, 0, 0, 0, 0]
                  for _ in range(10)]
    benign_emb = [np.random.randn(8) * 0.5 for _ in range(20)]

    detector.add_attack_cluster(attack_emb, "injection")
    detector.add_benign_cluster(benign_emb, "normal")

    # Test detection
    test_attack = np.random.randn(8) + [1, 0, 0, 0, 0, 0, 0, 0]
    result = detector.analyze(test_attack)
    print(
        f"Attack test: anomalous={result.is_anomalous}, score={result.anomaly_score:.3f}")

    test_benign = np.random.randn(8) * 0.3
    result = detector.analyze(test_benign)
    print(
        f"Benign test: anomalous={result.is_anomalous}, score={result.anomaly_score:.3f}")
