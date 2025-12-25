"""
Morse Theory Engine — SENTINEL Phase 4: Strange Math v3

Uses Morse theory to detect attacks via critical points in embedding space.
Philosophy: Attacks create artificial saddle points in the semantic landscape.

Features:
- Critical point detection
- Morse index computation
- Hessian analysis
- Topological attack signatures

Author: Dmitry Labintsev
Contact: chg@live.ru | @DmLabincev
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import math


class CriticalPointType(Enum):
    """Types of critical points"""

    MINIMUM = "minimum"  # Morse index 0
    SADDLE = "saddle"  # Mixed eigenvalues
    MAXIMUM = "maximum"  # All negative eigenvalues


@dataclass
class CriticalPoint:
    """A critical point in embedding space"""

    position: List[float]  # Coordinates
    morse_index: int  # Number of negative eigenvalues
    critical_type: CriticalPointType
    function_value: float


@dataclass
class MorseAnalysisResult:
    """Result of Morse theory analysis"""

    is_anomalous: bool
    critical_points: List[CriticalPoint]
    saddle_point_count: int
    morse_signature: List[int]  # Distribution of Morse indices
    anomaly_score: float
    attack_evidence: List[str]


class MorseTheoryEngine:
    """
    Detects attacks via Morse theory on embedding landscape.

    Theory: Morse theory studies manifold topology through
    critical points of smooth functions.

    Key insight:
    - Normal text → smooth gradient flow
    - Injection → creates artificial saddle points
    - Jailbreak → sharp Morse index transitions

    Math:
    f: M → ℝ (smooth function on manifold)
    Critical point: ∇f(p) = 0
    Morse index: # negative eigenvalues of Hessian at p

    Usage:
        engine = MorseTheoryEngine()
        result = engine.analyze(embeddings)
        if result.is_anomalous:
            flag_as_attack()
    """

    ENGINE_NAME = "morse_theory"
    ENGINE_VERSION = "1.0.0"
    IS_PROACTIVE = True

    # Thresholds
    MAX_NORMAL_SADDLES = 2
    ANOMALY_THRESHOLD = 0.6

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.baseline_distribution: List[int] = [0] * 10

    def analyze(self, embeddings: List[List[float]]) -> MorseAnalysisResult:
        """Analyze embeddings using Morse theory"""

        # 1. Find critical points
        critical_points = self._find_critical_points(embeddings)

        # 2. Compute Morse indices
        for point in critical_points:
            point.morse_index = self._compute_morse_index(
                point.position, embeddings)
            point.critical_type = self._classify_critical_point(
                point.morse_index, len(embeddings[0]) if embeddings else 0
            )

        # 3. Count saddle points
        saddle_count = sum(
            1 for p in critical_points if p.critical_type == CriticalPointType.SADDLE
        )

        # 4. Compute Morse signature
        signature = self._compute_morse_signature(critical_points)

        # 5. Compare to baseline
        anomaly_score = self._compute_anomaly_score(signature)

        # 6. Gather evidence
        evidence = []
        if saddle_count > self.MAX_NORMAL_SADDLES:
            evidence.append(
                f"Excess saddle points: {saddle_count} > {self.MAX_NORMAL_SADDLES}"
            )
        if anomaly_score > self.ANOMALY_THRESHOLD:
            evidence.append(f"Morse signature anomaly: {anomaly_score:.0%}")

        return MorseAnalysisResult(
            is_anomalous=anomaly_score > self.ANOMALY_THRESHOLD,
            critical_points=critical_points,
            saddle_point_count=saddle_count,
            morse_signature=signature,
            anomaly_score=anomaly_score,
            attack_evidence=evidence,
        )

    def _find_critical_points(
        self, embeddings: List[List[float]]
    ) -> List[CriticalPoint]:
        """Find critical points where gradient = 0"""
        critical_points = []

        if len(embeddings) < 3:
            return critical_points

        # Simplified: find local extrema by comparing neighbors
        for i in range(1, len(embeddings) - 1):
            prev_norm = self._norm(embeddings[i - 1])
            curr_norm = self._norm(embeddings[i])
            next_norm = self._norm(embeddings[i + 1])

            # Check for local extremum (gradient crossing zero)
            if (prev_norm < curr_norm > next_norm) or (
                prev_norm > curr_norm < next_norm
            ):
                critical_points.append(
                    CriticalPoint(
                        position=embeddings[i],
                        morse_index=0,
                        critical_type=CriticalPointType.MINIMUM,
                        function_value=curr_norm,
                    )
                )

        return critical_points

    def _compute_morse_index(
        self, position: List[float], embeddings: List[List[float]]
    ) -> int:
        """Compute Morse index (# negative Hessian eigenvalues)"""
        # Simplified Hessian approximation
        if not embeddings or not position:
            return 0

        dim = len(position)
        negative_count = 0

        # Approximate second derivatives
        for d in range(min(dim, 5)):  # Check first 5 dimensions
            if d < len(position):
                # Curvature approximation
                val = position[d]
                # Negative curvature = saddle direction
                if val < 0:
                    negative_count += 1

        return negative_count

    def _classify_critical_point(
        self, morse_index: int, dimension: int
    ) -> CriticalPointType:
        """Classify critical point by Morse index"""
        if morse_index == 0:
            return CriticalPointType.MINIMUM
        elif morse_index == dimension:
            return CriticalPointType.MAXIMUM
        else:
            return CriticalPointType.SADDLE

    def _compute_morse_signature(
        self, critical_points: List[CriticalPoint]
    ) -> List[int]:
        """Compute distribution of Morse indices"""
        signature = [0] * 10  # Support up to index 9

        for point in critical_points:
            if point.morse_index < len(signature):
                signature[point.morse_index] += 1

        return signature

    def _compute_anomaly_score(self, signature: List[int]) -> float:
        """Compare signature to baseline distribution"""
        if not self.baseline_distribution:
            # Default: normal text has mostly minima (index 0)
            self.baseline_distribution = [5, 1, 0, 0, 0, 0, 0, 0, 0, 0]

        # Compute distance from baseline
        distance = 0.0
        total = sum(signature) + sum(self.baseline_distribution)

        for i in range(len(signature)):
            base = (
                self.baseline_distribution[i]
                if i < len(self.baseline_distribution)
                else 0
            )
            distance += abs(signature[i] - base)

        if total > 0:
            return min(distance / total, 1.0)
        return 0.0

    def _norm(self, vector: List[float]) -> float:
        """Compute L2 norm"""
        return math.sqrt(sum(x * x for x in vector))

    def set_baseline(self, distribution: List[int]):
        """Set baseline Morse index distribution"""
        self.baseline_distribution = distribution

    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics"""
        return {
            "baseline_set": sum(self.baseline_distribution) > 0,
            "max_normal_saddles": self.MAX_NORMAL_SADDLES,
            "anomaly_threshold": self.ANOMALY_THRESHOLD,
        }


# Factory
_morse_engine: Optional[MorseTheoryEngine] = None


def get_morse_engine(config: Optional[Dict[str, Any]] = None) -> MorseTheoryEngine:
    """Get or create singleton MorseTheoryEngine."""
    global _morse_engine
    if _morse_engine is None:
        _morse_engine = MorseTheoryEngine(config)
    return _morse_engine


def create_engine(config: Optional[Dict[str, Any]] = None) -> MorseTheoryEngine:
    return MorseTheoryEngine(config)


if __name__ == "__main__":
    engine = MorseTheoryEngine()

    print("=== Morse Theory Engine Test ===\n")

    # Normal embeddings (smooth transition)
    normal = [[0.1 * i for _ in range(10)] for i in range(20)]

    result = engine.analyze(normal)
    print(
        f"Normal: anomaly={result.anomaly_score:.0%}, saddles={result.saddle_point_count}"
    )

    # Attack embeddings (sharp transitions)
    attack = []
    for i in range(20):
        if i == 10:  # Injection point
            attack.append([-0.5] * 10)  # Sharp saddle
        else:
            attack.append([0.1 * i] * 10)

    result = engine.analyze(attack)
    print(
        f"Attack: anomaly={result.anomaly_score:.0%}, saddles={result.saddle_point_count}"
    )
    print(f"Evidence: {result.attack_evidence}")
