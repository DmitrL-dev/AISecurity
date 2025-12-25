"""
Hyperbolic Geometry Engine - Non-Euclidean Embedding Analysis

Based on 2025 research:
  - HiM (Hierarchical Mamba) 2025: Poincaré + state space models
  - MERU 2023: Hyperbolic vision-language models
  - Nickel & Kiela 2017: Original Poincaré embeddings

Theory:
  Hyperbolic space has constant negative curvature, allowing
  exponential growth - perfect for hierarchical structures.
  In the Poincaré ball model:
  - Center = root of hierarchy
  - Boundary = leaves
  - Norm = depth in hierarchy
  - Distance = semantic similarity

Security applications:
  - Detect hierarchy manipulation in prompts
  - Identify distorted reasoning chains
  - Compare embedding distributions across curvatures

Author: SENTINEL Team
Date: 2025-12-09
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any

logger = logging.getLogger("HyperbolicGeometry")


# ============================================================================
# Enums and Data Classes
# ============================================================================

class HyperbolicModel(str, Enum):
    """Models of hyperbolic space."""
    POINCARE_BALL = "poincare_ball"    # Most common for ML
    LORENTZ = "lorentz"                 # Hyperboloid model
    KLEIN = "klein"                      # Klein disk model


@dataclass
class HyperbolicPoint:
    """A point in hyperbolic space."""
    coordinates: np.ndarray
    model: HyperbolicModel = HyperbolicModel.POINCARE_BALL
    curvature: float = -1.0  # Negative curvature

    @property
    def dimension(self) -> int:
        return len(self.coordinates)

    @property
    def norm(self) -> float:
        """Euclidean norm (position in Poincaré ball)."""
        return float(np.linalg.norm(self.coordinates))

    @property
    def is_valid(self) -> bool:
        """Check if point is inside Poincaré ball (norm < 1)."""
        return self.norm < 1.0


@dataclass
class HyperbolicEmbedding:
    """Embedding in hyperbolic space."""
    points: np.ndarray  # Shape: (n_points, dimension)
    model: HyperbolicModel = HyperbolicModel.POINCARE_BALL
    curvature: float = -1.0

    @property
    def num_points(self) -> int:
        return len(self.points)

    @property
    def dimension(self) -> int:
        return self.points.shape[1] if len(self.points.shape) > 1 else 0

    def norms(self) -> np.ndarray:
        """Get norms of all points."""
        return np.linalg.norm(self.points, axis=1)

    def hierarchy_levels(self) -> np.ndarray:
        """Estimate hierarchy level from norm."""
        norms = self.norms()
        # Higher norm = deeper in hierarchy
        return norms / (1 - norms + 1e-10)


@dataclass
class HyperbolicMetrics:
    """Various hyperbolic metrics."""
    mean_norm: float
    norm_variance: float
    hierarchy_depth: float
    boundary_proximity: float  # How close to boundary
    centroid_distance: float
    distortion_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mean_norm": self.mean_norm,
            "norm_variance": self.norm_variance,
            "hierarchy_depth": self.hierarchy_depth,
            "boundary_proximity": self.boundary_proximity,
            "centroid_distance": self.centroid_distance,
            "distortion_score": self.distortion_score
        }


@dataclass
class HyperbolicAnomaly:
    """Detected hyperbolic anomaly."""
    is_anomalous: bool
    anomaly_score: float
    anomaly_type: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_anomalous": self.is_anomalous,
            "anomaly_score": self.anomaly_score,
            "anomaly_type": self.anomaly_type,
            "details": self.details
        }


# ============================================================================
# Poincaré Ball Operations
# ============================================================================

class PoincareBall:
    """
    Operations in the Poincaré ball model of hyperbolic space.

    The Poincaré ball is the unit ball in R^n with the metric:
    ds² = 4 * ||dx||² / (1 - ||x||²)²
    """

    def __init__(self, curvature: float = -1.0, epsilon: float = 1e-7):
        self.curvature = curvature
        self.c = abs(curvature)  # Positive curvature constant
        self.epsilon = epsilon

    def project(self, x: np.ndarray, max_norm: float = 0.99) -> np.ndarray:
        """Project point into Poincaré ball."""
        norm = np.linalg.norm(x)
        if norm >= max_norm:
            return x / norm * max_norm
        return x

    def mobius_add(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """
        Möbius addition in Poincaré ball.

        x ⊕ y = ((1 + 2c⟨x,y⟩ + c||y||²)x + (1 - c||x||²)y) / 
                (1 + 2c⟨x,y⟩ + c²||x||²||y||²)
        """
        c = self.c

        x_norm_sq = np.dot(x, x)
        y_norm_sq = np.dot(y, y)
        xy_dot = np.dot(x, y)

        num = (1 + 2*c*xy_dot + c*y_norm_sq) * x + (1 - c*x_norm_sq) * y
        denom = 1 + 2*c*xy_dot + c*c*x_norm_sq*y_norm_sq + self.epsilon

        result = num / denom
        return self.project(result)

    def mobius_scalar(self, r: float, x: np.ndarray) -> np.ndarray:
        """
        Möbius scalar multiplication.

        r ⊗ x = tanh(r * arctanh(√c||x||)) * x / (√c||x||)
        """
        c = self.c
        sqrt_c = np.sqrt(c)

        x_norm = np.linalg.norm(x) + self.epsilon

        # tanh(r * arctanh(sqrt_c * ||x||)) / (sqrt_c * ||x||)
        scaled_norm = sqrt_c * x_norm
        scaled_norm = min(scaled_norm, 1 - self.epsilon)  # Clamp

        factor = np.tanh(r * np.arctanh(scaled_norm)) / (sqrt_c * x_norm)

        return self.project(factor * x)

    def distance(self, x: np.ndarray, y: np.ndarray) -> float:
        """
        Geodesic distance in Poincaré ball.

        d(x,y) = (2/√c) arctanh(√c ||−x ⊕ y||)
        """
        c = self.c
        sqrt_c = np.sqrt(c)

        # -x ⊕ y
        neg_x = -x
        diff = self.mobius_add(neg_x, y)
        diff_norm = np.linalg.norm(diff)

        # Clamp to avoid numerical issues
        diff_norm = min(sqrt_c * diff_norm, 1 - self.epsilon)

        return (2 / sqrt_c) * np.arctanh(diff_norm)

    def exp_map(self, x: np.ndarray, v: np.ndarray) -> np.ndarray:
        """
        Exponential map: project tangent vector onto manifold.

        exp_x(v) = x ⊕ (tanh(√c λ_x ||v|| / 2) * v / (√c ||v||))
        """
        c = self.c
        sqrt_c = np.sqrt(c)

        x_norm_sq = np.dot(x, x)
        lambda_x = 2 / (1 - c * x_norm_sq + self.epsilon)

        v_norm = np.linalg.norm(v) + self.epsilon

        second_term = np.tanh(sqrt_c * lambda_x *
                              v_norm / 2) * v / (sqrt_c * v_norm)

        return self.mobius_add(x, second_term)

    def log_map(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """
        Logarithmic map: project point to tangent space.

        log_x(y) = (2 / (√c λ_x)) arctanh(√c ||-x ⊕ y||) * (-x ⊕ y) / ||-x ⊕ y||
        """
        c = self.c
        sqrt_c = np.sqrt(c)

        x_norm_sq = np.dot(x, x)
        lambda_x = 2 / (1 - c * x_norm_sq + self.epsilon)

        neg_x = -x
        diff = self.mobius_add(neg_x, y)
        diff_norm = np.linalg.norm(diff) + self.epsilon

        scaled = min(sqrt_c * diff_norm, 1 - self.epsilon)

        return (2 / (sqrt_c * lambda_x)) * np.arctanh(scaled) * diff / diff_norm


# ============================================================================
# Hyperbolic Centroid and Aggregation
# ============================================================================

class HyperbolicAggregator:
    """
    Aggregation operations in hyperbolic space.
    """

    def __init__(self, ball: PoincareBall):
        self.ball = ball

    def frechet_mean(
        self,
        points: np.ndarray,
        weights: Optional[np.ndarray] = None,
        max_iter: int = 100,
        tol: float = 1e-6
    ) -> np.ndarray:
        """
        Compute Fréchet mean (hyperbolic centroid).

        Minimizes sum of squared geodesic distances.
        """
        n = len(points)
        if n == 0:
            return np.zeros(points.shape[1] if len(points.shape) > 1 else 1)
        if n == 1:
            return points[0]

        if weights is None:
            weights = np.ones(n) / n
        weights = weights / weights.sum()

        # Initialize with weighted Euclidean mean projected to ball
        mean = self.ball.project(np.average(
            points, weights=weights, axis=0) * 0.5)

        for _ in range(max_iter):
            # Compute gradient: sum of log maps
            gradient = np.zeros_like(mean)
            for i, p in enumerate(points):
                gradient += weights[i] * self.ball.log_map(mean, p)

            # Update using exponential map
            new_mean = self.ball.exp_map(mean, gradient)

            if np.linalg.norm(new_mean - mean) < tol:
                break
            mean = new_mean

        return mean

    def variance(
        self,
        points: np.ndarray,
        mean: Optional[np.ndarray] = None
    ) -> float:
        """Compute variance in hyperbolic space."""
        if mean is None:
            mean = self.frechet_mean(points)

        distances_sq = np.array([
            self.ball.distance(mean, p) ** 2 for p in points
        ])

        return float(np.mean(distances_sq))


# ============================================================================
# Hierarchy Analyzer
# ============================================================================

class HierarchyAnalyzer:
    """
    Analyzes hierarchical structure in hyperbolic embeddings.
    """

    def __init__(self, ball: PoincareBall):
        self.ball = ball

    def estimate_depth(self, embedding: HyperbolicEmbedding) -> np.ndarray:
        """
        Estimate hierarchical depth of each point.

        In Poincaré ball, depth ≈ norm (closer to boundary = deeper).
        """
        norms = embedding.norms()
        # Map norm to depth using artanh (inverse of boundary distance)
        depths = np.arctanh(np.clip(norms, 0, 0.99))
        return depths

    def find_root(self, embedding: HyperbolicEmbedding) -> int:
        """Find the root node (closest to center)."""
        norms = embedding.norms()
        return int(np.argmin(norms))

    def find_leaves(
        self,
        embedding: HyperbolicEmbedding,
        threshold: float = 0.8
    ) -> np.ndarray:
        """Find leaf nodes (close to boundary)."""
        norms = embedding.norms()
        return np.where(norms > threshold)[0]

    def hierarchy_distortion(
        self,
        embedding: HyperbolicEmbedding
    ) -> float:
        """
        Measure how well embedding preserves hierarchy.

        Low distortion = clear hierarchical structure.
        """
        norms = embedding.norms()

        # Ideal: uniform distribution of depths
        sorted_norms = np.sort(norms)
        n = len(sorted_norms)
        ideal = np.linspace(0, 0.9, n)

        # KS-like statistic
        distortion = np.max(np.abs(sorted_norms - ideal))

        return float(distortion)

    def parent_child_ratio(
        self,
        embedding: HyperbolicEmbedding
    ) -> float:
        """
        Estimate parent-child relationships quality.

        Good hierarchy: parents closer to center than children.
        """
        depths = self.estimate_depth(embedding)

        # For each point, count how many points are "above" (lower depth)
        n = len(depths)
        if n < 2:
            return 1.0

        above_counts = [(depths < d).sum() for d in depths]

        # Ideal distribution
        ideal_above = np.arange(n)

        correlation = np.corrcoef(above_counts, ideal_above)[0, 1]

        return float(correlation) if not np.isnan(correlation) else 0.0


# ============================================================================
# Anomaly Detector
# ============================================================================

class HyperbolicAnomalyDetector:
    """
    Detects anomalies in hyperbolic embeddings.
    """

    def __init__(
        self,
        ball: PoincareBall,
        boundary_threshold: float = 0.95,
        distortion_threshold: float = 0.5
    ):
        self.ball = ball
        self.aggregator = HyperbolicAggregator(ball)
        self.hierarchy = HierarchyAnalyzer(ball)
        self.boundary_threshold = boundary_threshold
        self.distortion_threshold = distortion_threshold

    def detect(self, embedding: HyperbolicEmbedding) -> HyperbolicAnomaly:
        """Detect anomalies in embedding."""
        anomalies = []
        details = {}
        total_score = 0.0

        norms = embedding.norms()

        # 1. Check for points outside ball
        outside = np.sum(norms >= 1.0)
        if outside > 0:
            anomalies.append("invalid_points")
            total_score += 0.3
            details["outside_ball"] = int(outside)

        # 2. Check for boundary clustering (too deep)
        near_boundary = np.sum(norms > self.boundary_threshold)
        if near_boundary > len(norms) * 0.8:
            anomalies.append("boundary_clustering")
            total_score += 0.2
            details["near_boundary_ratio"] = float(near_boundary / len(norms))

        # 3. Check hierarchy distortion
        distortion = self.hierarchy.hierarchy_distortion(embedding)
        if distortion > self.distortion_threshold:
            anomalies.append("hierarchy_distortion")
            total_score += 0.3
            details["distortion"] = distortion

        # 4. Check for center clustering (flat hierarchy)
        near_center = np.sum(norms < 0.1)
        if near_center > len(norms) * 0.8:
            anomalies.append("flat_hierarchy")
            total_score += 0.2
            details["near_center_ratio"] = float(near_center / len(norms))

        anomaly_type = anomalies[0] if anomalies else "none"

        return HyperbolicAnomaly(
            is_anomalous=len(anomalies) > 0,
            anomaly_score=min(1.0, total_score),
            anomaly_type=anomaly_type,
            details=details
        )


# ============================================================================
# Euclidean to Hyperbolic Projection
# ============================================================================

class EuclideanToHyperbolic:
    """
    Projects Euclidean embeddings to hyperbolic space.
    """

    def __init__(self, ball: PoincareBall):
        self.ball = ball

    def project_simple(self, embeddings: np.ndarray) -> HyperbolicEmbedding:
        """Simple projection via normalization."""
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        max_norm = norms.max() + 1e-10

        # Scale to fit in ball
        scaled = embeddings / max_norm * 0.9

        return HyperbolicEmbedding(
            points=scaled,
            model=HyperbolicModel.POINCARE_BALL,
            curvature=self.ball.curvature
        )

    def project_exponential(
        self,
        embeddings: np.ndarray,
        scale: float = 0.1
    ) -> HyperbolicEmbedding:
        """
        Project using exponential map from origin.

        Preserves distances better for hierarchical data.
        """
        origin = np.zeros(embeddings.shape[1])

        projected = []
        for v in embeddings:
            # Scale tangent vector
            v_scaled = v * scale
            # Apply exponential map from origin
            p = self.ball.exp_map(origin, v_scaled)
            projected.append(p)

        return HyperbolicEmbedding(
            points=np.array(projected),
            model=HyperbolicModel.POINCARE_BALL,
            curvature=self.ball.curvature
        )


# ============================================================================
# Main Hyperbolic Geometry Engine
# ============================================================================

class HyperbolicGeometryEngine:
    """
    Main engine for hyperbolic geometry operations.

    Provides:
    - Poincaré ball operations
    - Hyperbolic distance computation
    - Hierarchy analysis
    - Euclidean to hyperbolic projection
    - Anomaly detection
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        curvature = self.config.get("curvature", -1.0)
        self.ball = PoincareBall(curvature=curvature)
        self.aggregator = HyperbolicAggregator(self.ball)
        self.hierarchy = HierarchyAnalyzer(self.ball)
        self.projector = EuclideanToHyperbolic(self.ball)
        self.anomaly_detector = HyperbolicAnomalyDetector(self.ball)

        self.analysis_count = 0

        logger.info("HyperbolicGeometryEngine initialized")

    def project_embeddings(
        self,
        embeddings: np.ndarray,
        method: str = "exponential"
    ) -> HyperbolicEmbedding:
        """Project Euclidean embeddings to Poincaré ball."""
        if method == "simple":
            return self.projector.project_simple(embeddings)
        else:
            return self.projector.project_exponential(embeddings)

    def compute_distance(
        self,
        point1: np.ndarray,
        point2: np.ndarray
    ) -> float:
        """Compute hyperbolic distance between points."""
        return self.ball.distance(point1, point2)

    def compute_centroid(self, embedding: HyperbolicEmbedding) -> np.ndarray:
        """Compute Fréchet mean of embedding."""
        return self.aggregator.frechet_mean(embedding.points)

    def analyze_hierarchy(
        self,
        embedding: HyperbolicEmbedding
    ) -> Dict[str, Any]:
        """Analyze hierarchical structure."""
        depths = self.hierarchy.estimate_depth(embedding)
        root_idx = self.hierarchy.find_root(embedding)
        leaves = self.hierarchy.find_leaves(embedding)
        distortion = self.hierarchy.hierarchy_distortion(embedding)
        pc_ratio = self.hierarchy.parent_child_ratio(embedding)

        self.analysis_count += 1

        return {
            "root_index": root_idx,
            "num_leaves": len(leaves),
            "mean_depth": float(np.mean(depths)),
            "max_depth": float(np.max(depths)),
            "distortion": distortion,
            "parent_child_correlation": pc_ratio
        }

    def analyze_embeddings(
        self,
        euclidean_embeddings: np.ndarray
    ) -> Dict[str, Any]:
        """Full hyperbolic analysis of Euclidean embeddings."""
        # Project to hyperbolic
        hyp_embedding = self.project_embeddings(euclidean_embeddings)

        # Compute metrics
        norms = hyp_embedding.norms()
        centroid = self.compute_centroid(hyp_embedding)
        variance = self.aggregator.variance(hyp_embedding.points, centroid)

        # Hierarchy analysis
        hierarchy_info = self.analyze_hierarchy(hyp_embedding)

        # Anomaly detection
        anomaly = self.anomaly_detector.detect(hyp_embedding)

        metrics = HyperbolicMetrics(
            mean_norm=float(np.mean(norms)),
            norm_variance=float(np.var(norms)),
            hierarchy_depth=hierarchy_info["mean_depth"],
            boundary_proximity=float(np.max(norms)),
            centroid_distance=float(np.linalg.norm(centroid)),
            distortion_score=hierarchy_info["distortion"]
        )

        return {
            "metrics": metrics.to_dict(),
            "hierarchy": hierarchy_info,
            "anomaly": anomaly.to_dict(),
            "num_points": hyp_embedding.num_points
        }

    def compare_distributions(
        self,
        embeddings1: np.ndarray,
        embeddings2: np.ndarray
    ) -> Dict[str, Any]:
        """Compare two embedding distributions in hyperbolic space."""
        hyp1 = self.project_embeddings(embeddings1)
        hyp2 = self.project_embeddings(embeddings2)

        centroid1 = self.compute_centroid(hyp1)
        centroid2 = self.compute_centroid(hyp2)

        centroid_distance = self.ball.distance(centroid1, centroid2)

        var1 = self.aggregator.variance(hyp1.points, centroid1)
        var2 = self.aggregator.variance(hyp2.points, centroid2)

        return {
            "centroid_distance": centroid_distance,
            "variance_ratio": var1 / (var2 + 1e-10),
            "mean_norm_diff": abs(np.mean(hyp1.norms()) - np.mean(hyp2.norms()))
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "analyses_performed": self.analysis_count,
            "curvature": self.ball.curvature,
            "capabilities": [
                "poincare_projection",
                "hyperbolic_distance",
                "frechet_mean",
                "hierarchy_analysis",
                "anomaly_detection"
            ]
        }
