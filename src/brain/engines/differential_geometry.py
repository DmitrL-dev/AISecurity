"""
Differential Geometry Engine

Riemannian manifold analysis for AI security:
- Embedding curvature detection
- Geodesic distance metrics
- Adversarial perturbation detection via curvature

"Normal prompts live on smooth manifolds. Attacks create sharp curvature."
"""

import logging
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Tuple

logger = logging.getLogger("DifferentialGeometry")


@dataclass
class CurvatureResult:
    """Result of curvature analysis."""
    gaussian_curvature: float
    mean_curvature: float
    principal_curvatures: Tuple[float, float]
    is_anomaly: bool
    anomaly_score: float  # 0-100
    interpretation: str


@dataclass
class GeodesicResult:
    """Result of geodesic distance calculation."""
    euclidean_distance: float
    geodesic_distance: float
    curvature_factor: float  # geodesic/euclidean ratio
    path_complexity: float


class RiemannianManifold:
    """
    Analyzes embeddings as points on a Riemannian manifold.

    Key insight: Normal text embeddings form smooth manifolds.
    Adversarial attacks create local curvature spikes.

    Usage:
        manifold = RiemannianManifold(dim=768)
        curvature = manifold.compute_curvature(embedding, neighbors)
        if curvature.is_anomaly:
            # Handle adversarial input
    """

    def __init__(self, dim: int = 768, curvature_threshold: float = 2.0):
        self.dim = dim
        self.curvature_threshold = curvature_threshold
        self._metric_tensor = np.eye(dim)  # Euclidean by default

    def set_learned_metric(self, metric_tensor: np.ndarray) -> None:
        """Set learned metric tensor from data."""
        if metric_tensor.shape != (self.dim, self.dim):
            raise ValueError(f"Metric must be {self.dim}x{self.dim}")
        self._metric_tensor = metric_tensor

    def compute_curvature(
        self,
        point: np.ndarray,
        neighbors: List[np.ndarray],
        eps: float = 1e-6
    ) -> CurvatureResult:
        """
        Compute local curvature at a point given neighbors.

        Uses discrete approximation of Gaussian and mean curvature.
        """
        if len(neighbors) < 3:
            return CurvatureResult(
                gaussian_curvature=0.0,
                mean_curvature=0.0,
                principal_curvatures=(0.0, 0.0),
                is_anomaly=False,
                anomaly_score=0.0,
                interpretation="Insufficient neighbors for curvature estimation"
            )

        # Compute local covariance (approximates metric structure)
        neighbors_array = np.array(neighbors)
        centered = neighbors_array - point

        # Local covariance matrix
        cov = np.cov(centered.T) + eps * np.eye(self.dim)

        # Eigenvalues give principal curvatures (in PCA sense)
        eigenvalues = np.linalg.eigvalsh(cov)
        eigenvalues = np.sort(eigenvalues)[::-1]

        # Use ratio of eigenvalues as curvature proxy
        # High ratio = embedding space is highly anisotropic = suspicious
        if eigenvalues[-1] > eps:
            condition_number = eigenvalues[0] / eigenvalues[-1]
        else:
            condition_number = eigenvalues[0] / eps

        # Gaussian curvature (product of principal curvatures)
        k1, k2 = eigenvalues[0], eigenvalues[1]
        gaussian = k1 * k2 / (np.sum(eigenvalues) + eps)

        # Mean curvature (average of principal curvatures)
        mean = np.mean(eigenvalues[:2])

        # Anomaly detection based on curvature
        curvature_magnitude = np.log1p(condition_number)
        is_anomaly = curvature_magnitude > self.curvature_threshold
        anomaly_score = min(100, curvature_magnitude * 20)

        interpretation = self._interpret_curvature(
            gaussian, mean, condition_number)

        return CurvatureResult(
            gaussian_curvature=float(gaussian),
            mean_curvature=float(mean),
            principal_curvatures=(float(k1), float(k2)),
            is_anomaly=is_anomaly,
            anomaly_score=float(anomaly_score),
            interpretation=interpretation
        )

    def geodesic_distance(
        self,
        p1: np.ndarray,
        p2: np.ndarray,
        intermediate_points: Optional[List[np.ndarray]] = None
    ) -> GeodesicResult:
        """
        Compute geodesic distance between two points.

        Geodesic = shortest path on the manifold (not straight line).
        Higher curvature = greater difference from Euclidean.
        """
        # Euclidean distance
        euclidean = float(np.linalg.norm(p2 - p1))

        if intermediate_points is None or len(intermediate_points) == 0:
            # Without intermediates, approximate using metric tensor
            diff = p2 - p1
            geodesic = float(np.sqrt(diff @ self._metric_tensor @ diff))
        else:
            # Sum of segment lengths through intermediate points
            all_points = [p1] + intermediate_points + [p2]
            geodesic = 0.0
            for i in range(len(all_points) - 1):
                diff = all_points[i+1] - all_points[i]
                geodesic += np.sqrt(diff @ self._metric_tensor @ diff)
            geodesic = float(geodesic)

        curvature_factor = geodesic / (euclidean + 1e-8)

        # Path complexity = how much longer geodesic is than Euclidean
        path_complexity = max(0, curvature_factor - 1.0)

        return GeodesicResult(
            euclidean_distance=euclidean,
            geodesic_distance=geodesic,
            curvature_factor=curvature_factor,
            path_complexity=path_complexity
        )

    def parallel_transport(
        self,
        vector: np.ndarray,
        path: List[np.ndarray]
    ) -> np.ndarray:
        """
        Parallel transport a vector along a path.

        Useful for detecting if context "drifts" during conversation.
        """
        transported = vector.copy()

        for i in range(len(path) - 1):
            # Simplified: project onto tangent space at each point
            direction = path[i+1] - path[i]
            direction = direction / (np.linalg.norm(direction) + 1e-8)

            # Remove component parallel to direction (crude approximation)
            parallel_component = np.dot(transported, direction) * direction
            transported = transported - 0.1 * parallel_component
            transported = transported / (np.linalg.norm(transported) + 1e-8)

        return transported * np.linalg.norm(vector)

    def _interpret_curvature(
        self,
        gaussian: float,
        mean: float,
        condition: float
    ) -> str:
        """Interpret curvature values."""
        if condition < 10:
            return "Normal: Smooth local embedding structure"
        elif condition < 50:
            return "Elevated: Moderate anisotropy in local space"
        elif condition < 200:
            return "High: Significant curvature, possible boundary region"
        else:
            return "Extreme: Sharp curvature spike - likely adversarial"


class ManifoldAnomalyDetector:
    """
    Detect anomalies using manifold geometry.

    Combines:
    - Local curvature analysis
    - Geodesic distance from normal cluster
    - Tangent space alignment
    """

    def __init__(self, dim: int = 768):
        self.manifold = RiemannianManifold(dim)
        self._reference_points: List[np.ndarray] = []
        self._reference_center: Optional[np.ndarray] = None

    def fit_reference(self, normal_embeddings: List[np.ndarray]) -> None:
        """Fit reference manifold from normal data."""
        self._reference_points = normal_embeddings
        if normal_embeddings:
            self._reference_center = np.mean(normal_embeddings, axis=0)

            # Learn metric from data covariance
            centered = np.array(normal_embeddings) - self._reference_center
            cov = np.cov(centered.T)
            # Inverse covariance as metric (Mahalanobis-like)
            try:
                self.manifold.set_learned_metric(
                    np.linalg.inv(cov + 0.01 * np.eye(len(cov))))
            except np.linalg.LinAlgError:
                pass  # Keep identity metric

    def detect(self, embedding: np.ndarray) -> dict:
        """Detect if embedding is anomalous using manifold analysis."""
        results = {
            "is_anomaly": False,
            "anomaly_score": 0.0,
            "curvature": None,
            "geodesic": None,
            "reasons": []
        }

        if not self._reference_points:
            return results

        # Find k-nearest neighbors
        distances = [np.linalg.norm(embedding - ref)
                     for ref in self._reference_points]
        k = min(10, len(self._reference_points))
        nearest_indices = np.argsort(distances)[:k]
        neighbors = [self._reference_points[i] for i in nearest_indices]

        # Curvature analysis
        curvature = self.manifold.compute_curvature(embedding, neighbors)
        results["curvature"] = curvature

        if curvature.is_anomaly:
            results["reasons"].append(
                f"High curvature: {curvature.interpretation}")

        # Geodesic distance from center
        if self._reference_center is not None:
            geodesic = self.manifold.geodesic_distance(
                embedding, self._reference_center, neighbors[:3]
            )
            results["geodesic"] = geodesic

            if geodesic.path_complexity > 0.5:
                results["reasons"].append(
                    f"High path complexity: {geodesic.path_complexity:.2f}")

        # Aggregate score
        score = curvature.anomaly_score
        if results["geodesic"]:
            score += results["geodesic"].path_complexity * 20

        results["anomaly_score"] = min(100, score)
        results["is_anomaly"] = score > 50 or curvature.is_anomaly

        return results


# Singleton
_detector: Optional[ManifoldAnomalyDetector] = None


def get_manifold_detector(dim: int = 768) -> ManifoldAnomalyDetector:
    """Get singleton detector."""
    global _detector
    if _detector is None:
        _detector = ManifoldAnomalyDetector(dim)
    return _detector
