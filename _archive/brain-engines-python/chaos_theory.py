"""
Strange Math Engine — Chaos Theory Module
Uses Lyapunov exponents and phase space analysis for pattern detection.
Detects chaotic vs structured behavior in user interactions.
"""

import logging
import math
from dataclasses import dataclass
from typing import List, Optional
import numpy as np
from collections import deque

logger = logging.getLogger("StrangeMath.Chaos")


@dataclass
class LyapunovResult:
    """Result of Lyapunov exponent calculation."""
    exponent: float  # Positive = chaotic, Negative = stable
    is_chaotic: bool
    stability_score: float  # 0 = chaotic, 100 = stable
    classification: str  # "stable", "edge_of_chaos", "chaotic"


@dataclass
class PhaseSpaceResult:
    """Result of phase space analysis."""
    embedding_dimension: int
    correlation_dimension: float
    attractor_type: str  # "point", "periodic", "strange"
    predictability: float  # 0-1


class ChaosTheoryEngine:
    """
    Chaos theory-based analysis of user behavior patterns.
    Uses Lyapunov exponents and phase space reconstruction.
    """

    def __init__(self):
        logger.info("Initializing Chaos Theory Engine...")

        # Time series buffers per user
        self.user_time_series: dict = {}  # user_id -> deque of features
        self.buffer_size = 100

        # Thresholds
        self.lyapunov_chaos_threshold = 0.1  # Above = chaotic
        self.lyapunov_stable_threshold = -0.1  # Below = very stable

        logger.info("Chaos Theory Engine initialized")

    def record_interaction(self, user_id: str, features: dict):
        """
        Record user interaction for time series analysis.
        Features: prompt_length, risk_score, time_delta, etc.
        """
        if user_id not in self.user_time_series:
            self.user_time_series[user_id] = deque(maxlen=self.buffer_size)

        # Convert features to numeric vector
        numeric_features = [
            features.get("prompt_length", 0),
            features.get("risk_score", 0),
            features.get("time_delta", 0),
            features.get("word_count", 0),
        ]

        self.user_time_series[user_id].append(numeric_features)

    def calculate_lyapunov(self, time_series: List[List[float]]) -> LyapunovResult:
        """
        Calculate largest Lyapunov exponent from time series.

        Positive exponent → sensitive to initial conditions → chaotic
        Negative exponent → trajectories converge → stable/predictable
        Zero → edge of chaos
        """
        if len(time_series) < 10:
            return LyapunovResult(
                exponent=0.0,
                is_chaotic=False,
                stability_score=50,
                classification="insufficient_data"
            )

        # Convert to numpy array
        data = np.array(time_series)
        n_points = len(data)

        # Simplified Lyapunov estimation using nearest neighbors
        # In production, use proper algorithms like Wolf or Rosenstein

        lyapunov_sum = 0.0
        count = 0

        for i in range(n_points - 1):
            # Find nearest neighbor (not itself)
            min_dist = float('inf')
            min_idx = -1

            for j in range(n_points):
                if abs(i - j) > 1:  # Not adjacent
                    dist = np.linalg.norm(data[i] - data[j])
                    if 0 < dist < min_dist:
                        min_dist = dist
                        min_idx = j

            if min_idx > 0 and min_idx < n_points - 1:
                # Calculate divergence
                next_dist = np.linalg.norm(data[i + 1] - data[min_idx + 1])

                if min_dist > 0 and next_dist > 0:
                    lyapunov_sum += math.log(next_dist / min_dist)
                    count += 1

        # Average Lyapunov exponent
        exponent = lyapunov_sum / count if count > 0 else 0.0

        # Classification
        if exponent > self.lyapunov_chaos_threshold:
            classification = "chaotic"
            is_chaotic = True
            stability_score = max(0, 50 - exponent * 100)
        elif exponent < self.lyapunov_stable_threshold:
            classification = "stable"
            is_chaotic = False
            stability_score = min(100, 50 - exponent * 100)
        else:
            classification = "edge_of_chaos"
            is_chaotic = False
            stability_score = 50

        return LyapunovResult(
            exponent=exponent,
            is_chaotic=is_chaotic,
            stability_score=stability_score,
            classification=classification,
        )

    def analyze_phase_space(self, time_series: List[float], embedding_dim: int = 3, delay: int = 1) -> PhaseSpaceResult:
        """
        Reconstruct phase space using Takens' embedding theorem.
        Analyze the structure of the attractor.
        """
        if len(time_series) < embedding_dim * delay + 10:
            return PhaseSpaceResult(
                embedding_dimension=embedding_dim,
                correlation_dimension=0,
                attractor_type="unknown",
                predictability=0.5,
            )

        # Phase space reconstruction
        n_vectors = len(time_series) - (embedding_dim - 1) * delay
        embedded = np.zeros((n_vectors, embedding_dim))

        for i in range(n_vectors):
            for j in range(embedding_dim):
                embedded[i, j] = time_series[i + j * delay]

        # Calculate correlation dimension (simplified)
        # Count pairs within distance r
        distances = []
        for i in range(min(100, len(embedded))):
            for j in range(i + 1, min(100, len(embedded))):
                d = np.linalg.norm(embedded[i] - embedded[j])
                if d > 0:
                    distances.append(d)

        if not distances:
            return PhaseSpaceResult(
                embedding_dimension=embedding_dim,
                correlation_dimension=0,
                attractor_type="point",
                predictability=1.0,
            )

        # Estimate correlation dimension using log-log slope
        r_values = np.percentile(distances, [10, 20, 30, 40, 50])
        c_values = []

        for r in r_values:
            count = sum(1 for d in distances if d < r)
            c_values.append(count / len(distances))

        # Simple slope estimation
        if len(c_values) >= 2 and c_values[0] > 0 and c_values[-1] > 0:
            log_r = np.log(r_values)
            log_c = np.log(np.maximum(c_values, 1e-10))

            # Linear regression for slope
            correlation_dim = np.polyfit(log_r, log_c, 1)[0]
        else:
            correlation_dim = 0

        # Classify attractor type
        if correlation_dim < 0.5:
            attractor_type = "point"
            predictability = 0.95
        elif correlation_dim < 2.0:
            attractor_type = "periodic"
            predictability = 0.7
        else:
            attractor_type = "strange"
            predictability = 0.3

        return PhaseSpaceResult(
            embedding_dimension=embedding_dim,
            correlation_dimension=correlation_dim,
            attractor_type=attractor_type,
            predictability=predictability,
        )

    def analyze_user_behavior(self, user_id: str) -> dict:
        """
        Full chaos analysis of user behavior.
        """
        if user_id not in self.user_time_series:
            return {
                "status": "no_data",
                "lyapunov": None,
                "phase_space": None,
            }

        time_series = list(self.user_time_series[user_id])

        if len(time_series) < 10:
            return {
                "status": "insufficient_data",
                "data_points": len(time_series),
                "lyapunov": None,
                "phase_space": None,
            }

        # Lyapunov analysis
        lyapunov_result = self.calculate_lyapunov(time_series)

        # Phase space analysis (using first feature dimension)
        first_dim = [ts[0] for ts in time_series]
        phase_result = self.analyze_phase_space(first_dim)

        # Combined assessment
        if lyapunov_result.is_chaotic:
            behavior_type = "unpredictable"
            risk_modifier = 20  # Add to risk score
        elif lyapunov_result.classification == "edge_of_chaos":
            behavior_type = "transitional"
            risk_modifier = 10
        else:
            behavior_type = "predictable"
            risk_modifier = 0

        logger.info(
            f"Chaos analysis for {user_id}: exponent={lyapunov_result.exponent:.3f}, "
            f"type={behavior_type}"
        )

        return {
            "status": "analyzed",
            "data_points": len(time_series),
            "lyapunov": {
                "exponent": lyapunov_result.exponent,
                "is_chaotic": lyapunov_result.is_chaotic,
                "stability_score": lyapunov_result.stability_score,
                "classification": lyapunov_result.classification,
            },
            "phase_space": {
                "correlation_dimension": phase_result.correlation_dimension,
                "attractor_type": phase_result.attractor_type,
                "predictability": phase_result.predictability,
            },
            "behavior_type": behavior_type,
            "risk_modifier": risk_modifier,
        }

    def detect_regime_change(self, user_id: str, window_size: int = 20) -> Optional[dict]:
        """
        Detect sudden changes in behavioral dynamics (regime change).
        Could indicate account takeover or intentional obfuscation.
        """
        if user_id not in self.user_time_series:
            return None

        ts = list(self.user_time_series[user_id])

        if len(ts) < window_size * 2:
            return None

        # Compare early vs recent behavior
        early = ts[:window_size]
        recent = ts[-window_size:]

        early_lyapunov = self.calculate_lyapunov(early)
        recent_lyapunov = self.calculate_lyapunov(recent)

        # Detect significant change
        exponent_change = abs(recent_lyapunov.exponent -
                              early_lyapunov.exponent)

        if exponent_change > 0.5:
            return {
                "detected": True,
                "early_exponent": early_lyapunov.exponent,
                "recent_exponent": recent_lyapunov.exponent,
                "change_magnitude": exponent_change,
                "interpretation": "Significant behavioral dynamics change detected",
            }

        return {"detected": False}


# Singleton
_chaos_engine = None


def get_chaos_engine() -> ChaosTheoryEngine:
    global _chaos_engine
    if _chaos_engine is None:
        _chaos_engine = ChaosTheoryEngine()
    return _chaos_engine
