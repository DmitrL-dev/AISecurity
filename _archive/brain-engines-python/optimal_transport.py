"""
Optimal Transport Engine — SENTINEL Phase 4: Strange Math v3

Uses Wasserstein distance for distribution drift detection.
Philosophy: Measure "cost" of transforming normal to attack distribution.

Features:
- Wasserstein distance computation
- Barycenter comparison
- Sinkhorn divergence
- Distribution drift tracking

Author: Dmitry Labintsev
Contact: chg@live.ru | @DmLabincev
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import math
import numpy as np


@dataclass
class DistributionMetrics:
    """Metrics for a distribution"""

    mean: List[float]
    variance: List[float]
    centroid: List[float]


@dataclass
class TransportPlan:
    """Optimal transport plan"""

    cost: float
    assignments: List[tuple]
    is_anomalous: bool


@dataclass
class OptimalTransportResult:
    """Result of optimal transport analysis"""

    wasserstein_distance: float
    is_anomalous: bool
    distribution_metrics: DistributionMetrics
    transport_cost: float
    anomaly_type: Optional[str]
    confidence: float


class OptimalTransportEngine:
    """
    Uses Optimal Transport for attack detection.

    Theory:
    Wasserstein-p distance:
    Wₚ(μ,ν) = (inf_{γ∈Γ(μ,ν)} ∫∫ d(x,y)ᵖ dγ(x,y))^(1/p)

    Measures minimum "cost" to transform distribution μ into ν.

    Application:
    - Baseline = Wasserstein barycenter of normal prompts
    - Attack = high W₂ distance from barycenter

    Usage:
        engine = OptimalTransportEngine()
        engine.set_baseline(normal_embeddings)
        result = engine.analyze(test_embeddings)
        if result.is_anomalous:
            flag_attack()
    """

    ENGINE_NAME = "optimal_transport"
    ENGINE_VERSION = "1.0.0"
    IS_PROACTIVE = True

    # Configuration
    WASSERSTEIN_THRESHOLD = 0.5
    SINKHORN_REGULARIZATION = 0.1
    MAX_ITERATIONS = 100

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.baseline_barycenter: Optional[List[float]] = None
        self.baseline_metrics: Optional[DistributionMetrics] = None

    def set_baseline(self, normal_embeddings: List[List[float]]):
        """Set baseline from normal prompt embeddings"""
        if normal_embeddings is None or len(normal_embeddings) == 0:
            return

        # Compute barycenter (centroid for L2 Wasserstein)
        dim = len(normal_embeddings[0])
        n = len(normal_embeddings)

        barycenter = [0.0] * dim
        for emb in normal_embeddings:
            for d in range(dim):
                barycenter[d] += emb[d] / n

        self.baseline_barycenter = barycenter

        # Compute baseline metrics
        variance = [0.0] * dim
        for emb in normal_embeddings:
            for d in range(dim):
                variance[d] += (emb[d] - barycenter[d]) ** 2 / n

        self.baseline_metrics = DistributionMetrics(
            mean=barycenter[:], variance=variance, centroid=barycenter[:]
        )

    def analyze(self, embeddings: List[List[float]]) -> OptimalTransportResult:
        """Analyze embeddings using optimal transport"""

        if embeddings is None or len(embeddings) == 0:
            return self._empty_result()

        # Compute test distribution metrics
        test_metrics = self._compute_metrics(embeddings)

        # Compute Wasserstein distance to baseline
        w_distance = float(self._compute_wasserstein_distance(embeddings))

        # Compute transport cost
        transport_cost = float(self._compute_transport_cost(embeddings))

        # Determine anomaly
        compare = np.array(w_distance > self.WASSERSTEIN_THRESHOLD)
        is_anomalous = bool(compare.any())

        # Detect anomaly type
        anomaly_type = None
        if is_anomalous:
            if float(w_distance) > 2 * float(self.WASSERSTEIN_THRESHOLD):
                anomaly_type = "severe_distribution_shift"
            else:
                anomaly_type = "distribution_drift"

        # Confidence based on distance clarity
        confidence = min(float(w_distance) /
                         float(self.WASSERSTEIN_THRESHOLD), 1.0)

        return OptimalTransportResult(
            wasserstein_distance=w_distance,
            is_anomalous=is_anomalous,
            distribution_metrics=test_metrics,
            transport_cost=transport_cost,
            anomaly_type=anomaly_type,
            confidence=confidence,
        )

    def _compute_wasserstein_distance(self, embeddings: List[List[float]]) -> float:
        """Compute approximate Wasserstein-2 distance to baseline"""
        if not self.baseline_barycenter or not embeddings:
            return 0.0

        # Compute centroid of test distribution
        dim = len(embeddings[0])
        n = len(embeddings)

        test_centroid = [0.0] * dim
        for emb in embeddings:
            for d in range(dim):
                test_centroid[d] += emb[d] / n

        # W2 distance between Gaussians ≈ ||μ₁ - μ₂||₂
        # (simplified, assumes similar covariance)
        distance = math.sqrt(
            sum(
                (test_centroid[d] - self.baseline_barycenter[d]) ** 2
                for d in range(dim)
            )
        )

        # Normalize by dimension
        return distance / math.sqrt(dim)

    def _compute_transport_cost(self, embeddings: List[List[float]]) -> float:
        """Compute transport cost using Sinkhorn algorithm"""
        if not self.baseline_barycenter or not embeddings:
            return 0.0

        # Simplified: sum of distances to barycenter
        total_cost = 0.0
        for emb in embeddings:
            dist = math.sqrt(
                sum(
                    (emb[d] - self.baseline_barycenter[d]) ** 2 for d in range(len(emb))
                )
            )
            total_cost += dist

        return total_cost / len(embeddings)

    def _compute_metrics(self, embeddings: List[List[float]]) -> DistributionMetrics:
        """Compute distribution metrics"""
        if embeddings is None or len(embeddings) == 0:
            return DistributionMetrics([], [], [])

        dim = len(embeddings[0])
        n = len(embeddings)

        # Mean
        mean = [0.0] * dim
        for emb in embeddings:
            for d in range(dim):
                mean[d] += emb[d] / n

        # Variance
        variance = [0.0] * dim
        for emb in embeddings:
            for d in range(dim):
                variance[d] += (emb[d] - mean[d]) ** 2 / n

        return DistributionMetrics(mean=mean, variance=variance, centroid=mean[:])

    def compute_sinkhorn_divergence(
        self, embeddings_a: List[List[float]], embeddings_b: List[List[float]]
    ) -> float:
        """
        Compute Sinkhorn divergence (differentiable OT).

        OTε(μ,ν) = OTε(μ,ν) - ½OTε(μ,μ) - ½OTε(ν,ν)
        """
        ot_ab = self._sinkhorn_ot(embeddings_a, embeddings_b)
        ot_aa = self._sinkhorn_ot(embeddings_a, embeddings_a)
        ot_bb = self._sinkhorn_ot(embeddings_b, embeddings_b)

        return ot_ab - 0.5 * ot_aa - 0.5 * ot_bb

    def _sinkhorn_ot(
        self, embeddings_a: List[List[float]], embeddings_b: List[List[float]]
    ) -> float:
        """Compute entropic OT with Sinkhorn iterations"""
        if embeddings_a is None or len(embeddings_a) == 0 or embeddings_b is None or len(embeddings_b) == 0:
            return 0.0

        n, m = len(embeddings_a), len(embeddings_b)

        # Compute cost matrix
        cost = [[0.0] * m for _ in range(n)]
        for i in range(n):
            for j in range(m):
                cost[i][j] = sum(
                    (embeddings_a[i][d] - embeddings_b[j][d]) ** 2
                    for d in range(len(embeddings_a[0]))
                )

        # Initialize potentials
        u = [1.0 / n] * n
        v = [1.0 / m] * m

        # Sinkhorn iterations (simplified)
        for _ in range(min(self.MAX_ITERATIONS, 10)):
            # Update u
            for i in range(n):
                s = sum(
                    v[j] * math.exp(-cost[i][j] / self.SINKHORN_REGULARIZATION)
                    for j in range(m)
                )
                u[i] = 1.0 / max(s * n, 1e-10)

            # Update v
            for j in range(m):
                s = sum(
                    u[i] * math.exp(-cost[i][j] / self.SINKHORN_REGULARIZATION)
                    for i in range(n)
                )
                v[j] = 1.0 / max(s * m, 1e-10)

        # Compute OT cost
        ot_cost = 0.0
        for i in range(n):
            for j in range(m):
                transport = (
                    u[i] * v[j] *
                    math.exp(-cost[i][j] / self.SINKHORN_REGULARIZATION)
                )
                ot_cost += transport * cost[i][j]

        return ot_cost

    def _empty_result(self) -> OptimalTransportResult:
        """Return empty result"""
        return OptimalTransportResult(
            wasserstein_distance=0.0,
            is_anomalous=False,
            distribution_metrics=DistributionMetrics([], [], []),
            transport_cost=0.0,
            anomaly_type=None,
            confidence=0.0,
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return {
            "baseline_set": self.baseline_barycenter is not None,
            "wasserstein_threshold": self.WASSERSTEIN_THRESHOLD,
            "sinkhorn_regularization": self.SINKHORN_REGULARIZATION,
        }


# Factory
def create_engine(config: Optional[Dict[str, Any]] = None) -> OptimalTransportEngine:
    return OptimalTransportEngine(config)


if __name__ == "__main__":
    engine = OptimalTransportEngine()

    print("=== Optimal Transport Engine Test ===\n")

    import random

    random.seed(42)

    # Set baseline
    normal = [[random.gauss(0, 0.1) for _ in range(5)] for _ in range(100)]
    engine.set_baseline(normal)

    # Test normal
    test_normal = [[random.gauss(0, 0.1) for _ in range(5)] for _ in range(20)]
    result = engine.analyze(test_normal)
    print(
        f"Normal: W2={result.wasserstein_distance:.3f}, anomaly={result.is_anomalous}"
    )

    # Test attack (shifted distribution)
    test_attack = [[random.gauss(2, 0.1) for _ in range(5)] for _ in range(20)]
    result = engine.analyze(test_attack)
    print(
        f"Attack: W2={result.wasserstein_distance:.3f}, anomaly={result.is_anomalous}"
    )
    print(
        f"Anomaly type: {result.anomaly_type}, confidence: {result.confidence:.0%}")
