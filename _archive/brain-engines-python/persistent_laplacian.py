"""
Persistent Laplacian Engine — SENTINEL Phase 4: Strange Math v3

Combines spectral methods with persistent homology for attack detection.
Philosophy: Track eigenvalue evolution across filtration scales.

Features:
- Persistent Betti numbers
- Spectral gap evolution
- Multi-scale detection
- TDA + spectral fusion

Author: Dmitry Labintsev
Contact: chg@live.ru | @DmLabincev
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import math


@dataclass
class FiltrationLevel:
    """A single level in the filtration"""

    scale: float
    betti_numbers: List[int]  # β0, β1, β2, ...
    spectral_gap: float
    eigenvalues: List[float]


@dataclass
class PersistentFeature:
    """A topological feature that persists across scales"""

    birth_scale: float
    death_scale: float
    dimension: int
    persistence: float  # death - birth


@dataclass
class PersistentLaplacianResult:
    """Result of persistent Laplacian analysis"""

    is_anomalous: bool
    filtration: List[FiltrationLevel]
    persistent_features: List[PersistentFeature]
    spectral_gap_evolution: List[float]
    combined_score: float
    anomaly_type: Optional[str]


class PersistentLaplacianEngine:
    """
    Combines Graph Laplacian with Persistent Homology.

    Theory:
    - Combinatorial Laplacian: Lₖ = ∂ₖ₊₁∂*ₖ₊₁ + ∂*ₖ∂ₖ
    - Persistent Laplacian: Lₖᵗ·ˢ for filtration F^t ⊆ F^s
    - Persistent Betti: βₖᵗ·ˢ = dim(ker Lₖᵗ·ˢ)

    Key insight: eigenvalues of Lₖᵗ·ˢ encode BOTH
    spectral AND topological information.

    Advantage over pure TDA:
    - Faster (matrix eigenvalues vs homology)
    - More information (non-zero eigenvalues matter)
    - Better interpolation between scales

    Usage:
        engine = PersistentLaplacianEngine()
        result = engine.analyze(embeddings)
        if result.is_anomalous:
            flag_attack()
    """

    ENGINE_NAME = "persistent_laplacian"
    ENGINE_VERSION = "1.0.0"
    IS_PROACTIVE = True

    # Configuration
    NUM_FILTRATION_LEVELS = 10
    SPECTRAL_GAP_THRESHOLD = 0.1
    PERSISTENCE_THRESHOLD = 0.3

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

    def analyze(self, embeddings: List[List[float]]) -> PersistentLaplacianResult:
        """Analyze embeddings using persistent Laplacian"""

        if len(embeddings) < 2:
            return self._empty_result()

        # 1. Build filtration
        filtration = self._build_filtration(embeddings)

        # 2. Extract persistent features
        features = self._extract_persistent_features(filtration)

        # 3. Analyze spectral gap evolution
        gap_evolution = [f.spectral_gap for f in filtration]

        # 4. Compute combined score
        combined_score = self._compute_combined_score(
            filtration, features, gap_evolution
        )

        # 5. Detect anomaly type
        anomaly_type = self._detect_anomaly_type(filtration, features, gap_evolution)

        return PersistentLaplacianResult(
            is_anomalous=combined_score > 0.5,
            filtration=filtration,
            persistent_features=features,
            spectral_gap_evolution=gap_evolution,
            combined_score=combined_score,
            anomaly_type=anomaly_type,
        )

    def _build_filtration(self, embeddings: List[List[float]]) -> List[FiltrationLevel]:
        """Build filtration of simplicial complexes"""
        filtration = []

        # Compute all pairwise distances
        n = len(embeddings)
        distances = []
        for i in range(n):
            for j in range(i + 1, n):
                d = self._distance(embeddings[i], embeddings[j])
                distances.append(d)

        if not distances:
            return filtration

        max_dist = max(distances)

        # Create filtration levels
        for level in range(self.NUM_FILTRATION_LEVELS):
            scale = (level + 1) * max_dist / self.NUM_FILTRATION_LEVELS

            # Build graph at this scale (edges where distance <= scale)
            edges = []
            for i in range(n):
                for j in range(i + 1, n):
                    if self._distance(embeddings[i], embeddings[j]) <= scale:
                        edges.append((i, j))

            # Compute Laplacian eigenvalues
            eigenvalues = self._compute_laplacian_eigenvalues(n, edges)

            # Compute Betti numbers (simplified)
            betti = self._compute_betti_numbers(n, edges)

            # Spectral gap = second smallest eigenvalue
            spectral_gap = eigenvalues[1] if len(eigenvalues) > 1 else 0

            filtration.append(
                FiltrationLevel(
                    scale=scale,
                    betti_numbers=betti,
                    spectral_gap=spectral_gap,
                    eigenvalues=eigenvalues,
                )
            )

        return filtration

    def _compute_laplacian_eigenvalues(
        self, n: int, edges: List[Tuple[int, int]]
    ) -> List[float]:
        """Compute eigenvalues of graph Laplacian (simplified)"""
        # Build degree matrix
        degrees = [0] * n
        for i, j in edges:
            degrees[i] += 1
            degrees[j] += 1

        # Simplified eigenvalue estimation
        # Real implementation would use numpy.linalg.eigvalsh
        if not edges:
            return [0.0] * n

        avg_degree = sum(degrees) / max(n, 1)
        max_degree = max(degrees) if degrees else 0

        # Approximate eigenvalue distribution
        eigenvalues = [0.0]  # Always have 0 eigenvalue
        for i in range(1, n):
            # Cheeger-like approximation
            eigenvalues.append(min(avg_degree, 2 * i * avg_degree / n))

        return sorted(eigenvalues)

    def _compute_betti_numbers(self, n: int, edges: List[Tuple[int, int]]) -> List[int]:
        """Compute Betti numbers (simplified)"""
        # β0 = number of connected components
        # β1 = number of independent cycles

        # Use union-find for connected components
        parent = list(range(n))

        def find(x):
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x, y):
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py

        for i, j in edges:
            union(i, j)

        # Count components
        components = len(set(find(i) for i in range(n)))

        # Euler characteristic: V - E + F = β0 - β1 + β2
        # For graph: β0 = components, β1 = E - V + components
        beta_0 = components
        beta_1 = max(0, len(edges) - n + components)

        return [beta_0, beta_1, 0]  # β2 = 0 for graphs

    def _extract_persistent_features(
        self, filtration: List[FiltrationLevel]
    ) -> List[PersistentFeature]:
        """Extract persistent features from filtration"""
        features = []

        if len(filtration) < 2:
            return features

        # Track Betti number changes
        for dim in range(2):  # β0, β1
            birth_scale = None
            prev_betti = None

            for level in filtration:
                curr_betti = (
                    level.betti_numbers[dim] if dim < len(level.betti_numbers) else 0
                )

                if prev_betti is not None and curr_betti != prev_betti:
                    if curr_betti > prev_betti:
                        # Feature born
                        birth_scale = level.scale
                    elif birth_scale is not None:
                        # Feature died
                        features.append(
                            PersistentFeature(
                                birth_scale=birth_scale,
                                death_scale=level.scale,
                                dimension=dim,
                                persistence=level.scale - birth_scale,
                            )
                        )
                        birth_scale = None

                prev_betti = curr_betti

        return features

    def _compute_combined_score(
        self,
        filtration: List[FiltrationLevel],
        features: List[PersistentFeature],
        gap_evolution: List[float],
    ) -> float:
        """Compute combined anomaly score"""
        score = 0.0

        # 1. Spectral gap irregularity
        if len(gap_evolution) >= 2:
            # Check for sudden changes
            for i in range(1, len(gap_evolution)):
                change = abs(gap_evolution[i] - gap_evolution[i - 1])
                if change > self.SPECTRAL_GAP_THRESHOLD:
                    score += 0.2

        # 2. High-persistence features
        for feature in features:
            if feature.persistence > self.PERSISTENCE_THRESHOLD:
                score += 0.15

        # 3. Betti number anomalies
        for level in filtration:
            if len(level.betti_numbers) > 1 and level.betti_numbers[1] > 3:
                score += 0.1  # Too many cycles

        return min(score, 1.0)

    def _detect_anomaly_type(
        self,
        filtration: List[FiltrationLevel],
        features: List[PersistentFeature],
        gap_evolution: List[float],
    ) -> Optional[str]:
        """Detect specific type of anomaly"""

        # Check for injection signature
        if len(gap_evolution) >= 3:
            mid = len(gap_evolution) // 2
            if gap_evolution[mid] > 2 * gap_evolution[0]:
                return "injection_signature"

        # Check for unusual persistence
        high_persistence = [f for f in features if f.persistence > 0.5]
        if len(high_persistence) >= 2:
            return "multi_scale_attack"

        return None

    def _distance(self, a: List[float], b: List[float]) -> float:
        """Euclidean distance"""
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))

    def _empty_result(self) -> PersistentLaplacianResult:
        """Return empty result"""
        return PersistentLaplacianResult(
            is_anomalous=False,
            filtration=[],
            persistent_features=[],
            spectral_gap_evolution=[],
            combined_score=0.0,
            anomaly_type=None,
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return {
            "filtration_levels": self.NUM_FILTRATION_LEVELS,
            "spectral_gap_threshold": self.SPECTRAL_GAP_THRESHOLD,
            "persistence_threshold": self.PERSISTENCE_THRESHOLD,
        }


# Factory
def create_engine(config: Optional[Dict[str, Any]] = None) -> PersistentLaplacianEngine:
    return PersistentLaplacianEngine(config)


if __name__ == "__main__":
    engine = PersistentLaplacianEngine()

    print("=== Persistent Laplacian Engine Test ===\n")

    # Normal embeddings (smooth cluster)
    import random

    random.seed(42)
    normal = [[random.gauss(0, 0.1) for _ in range(5)] for _ in range(20)]

    result = engine.analyze(normal)
    print(f"Normal: score={result.combined_score:.0%}, anomaly={result.anomaly_type}")

    # Attack embeddings (two clusters = injection)
    attack = [[random.gauss(0, 0.1) for _ in range(5)] for _ in range(10)] + [
        [random.gauss(5, 0.1) for _ in range(5)] for _ in range(10)
    ]

    result = engine.analyze(attack)
    print(f"Attack: score={result.combined_score:.0%}, anomaly={result.anomaly_type}")
    print(f"Persistent features: {len(result.persistent_features)}")
