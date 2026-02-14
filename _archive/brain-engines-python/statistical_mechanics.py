"""
Statistical Mechanics Engine

Physics-inspired analysis for AI security:
- Energy landscape modeling
- Boltzmann distribution for prompt likelihood
- "Temperature" profiling of conversations
- Phase transition detection

"Adversarial prompts are like high-energy states - they stand out."
"""

import logging
import numpy as np
from dataclasses import dataclass
from typing import List, Optional, Dict
from collections import defaultdict

logger = logging.getLogger("StatisticalMechanics")


@dataclass
class EnergyState:
    """Energy state of a prompt/embedding."""
    energy: float  # Lower = more natural
    temperature: float  # Sampling "temperature"
    probability: float  # Boltzmann probability
    partition_function: float
    entropy: float
    free_energy: float  # F = E - TS


@dataclass
class PhaseTransition:
    """Detected phase transition in conversation."""
    detected: bool
    transition_point: int  # Index where transition occurred
    order_parameter_before: float
    order_parameter_after: float
    phase_type: str  # "gradual", "sharp", "critical"


class EnergyLandscape:
    """
    Models the energy landscape of prompt embeddings.

    Key insight: Normal prompts cluster in low-energy basins.
    Attacks climb to high-energy peaks or unstable saddle points.

    Usage:
        landscape = EnergyLandscape()
        landscape.fit(normal_embeddings)

        state = landscape.compute_energy(test_embedding)
        if state.energy > threshold:
            # High energy = suspicious
    """

    def __init__(self, temperature: float = 1.0):
        self.temperature = temperature
        self._centers: List[np.ndarray] = []
        self._variances: List[float] = []
        self._weights: List[float] = []

    def fit(self, embeddings: List[np.ndarray], n_basins: int = 5) -> None:
        """
        Fit energy landscape with multiple basins.

        Uses simple k-means-like clustering to find energy minima.
        """
        if len(embeddings) < n_basins:
            n_basins = len(embeddings)

        embeddings_array = np.array(embeddings)

        # Simple k-means for finding basins
        indices = np.random.choice(len(embeddings), n_basins, replace=False)
        self._centers = [embeddings_array[i].copy() for i in indices]

        # Iterate to find stable centers
        for _ in range(10):
            # Assign to nearest center
            assignments = defaultdict(list)
            for emb in embeddings:
                distances = [np.linalg.norm(emb - c) for c in self._centers]
                nearest = np.argmin(distances)
                assignments[nearest].append(emb)

            # Update centers
            for k, points in assignments.items():
                if points:
                    self._centers[k] = np.mean(points, axis=0)

        # Compute variances (basin widths)
        self._variances = []
        self._weights = []

        for k, center in enumerate(self._centers):
            points = assignments.get(k, [])
            if points:
                variance = np.mean(
                    [np.linalg.norm(p - center)**2 for p in points])
                self._variances.append(max(variance, 1e-6))
                self._weights.append(len(points) / len(embeddings))
            else:
                self._variances.append(1.0)
                self._weights.append(0.0)

        logger.info("Fitted %d energy basins", len(self._centers))

    def compute_energy(self, embedding: np.ndarray) -> EnergyState:
        """
        Compute energy of an embedding in the landscape.

        Energy = distance to nearest basin minimum.
        """
        if not self._centers:
            return EnergyState(
                energy=0.0,
                temperature=self.temperature,
                probability=1.0,
                partition_function=1.0,
                entropy=0.0,
                free_energy=0.0
            )

        # Energy contributions from each basin
        energies = []
        for center, variance, weight in zip(self._centers, self._variances, self._weights):
            dist_sq = np.sum((embedding - center)**2)
            # Harmonic potential: E = (1/2) * k * x^2
            basin_energy = dist_sq / (2 * variance)
            energies.append(basin_energy)

        # Minimum energy (closest basin)
        min_energy = min(energies)

        # Boltzmann distribution
        # P(state) ∝ exp(-E / kT)
        boltzmann_factors = [np.exp(-e / self.temperature) for e in energies]
        partition_function = sum(
            w * b for w, b in zip(self._weights, boltzmann_factors))
        partition_function = max(partition_function, 1e-10)

        probability = np.exp(-min_energy / self.temperature) / \
            partition_function

        # Entropy: S = -sum(p * log(p))
        probs = [w * b / partition_function for w,
                 b in zip(self._weights, boltzmann_factors)]
        entropy = -sum(p * np.log(p + 1e-10) for p in probs if p > 0)

        # Free energy: F = E - TS
        free_energy = min_energy - self.temperature * entropy

        return EnergyState(
            energy=float(min_energy),
            temperature=self.temperature,
            probability=float(probability),
            partition_function=float(partition_function),
            entropy=float(entropy),
            free_energy=float(free_energy)
        )


class TemperatureProfiler:
    """
    Profiles the "temperature" of conversations.

    High temperature = chaotic, unpredictable tokens
    Low temperature = coherent, expected flow

    Sudden temperature spikes indicate manipulation attempts.
    """

    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self._history: List[float] = []

    def add_token_entropy(self, entropy: float) -> None:
        """Add entropy measurement for a token."""
        self._history.append(entropy)

        # Keep window
        if len(self._history) > self.window_size * 10:
            self._history = self._history[-self.window_size * 10:]

    def current_temperature(self) -> float:
        """Estimate current conversation temperature."""
        if len(self._history) < self.window_size:
            return 1.0  # Default

        recent = self._history[-self.window_size:]
        # Temperature ∝ variance of entropy
        return float(np.std(recent) + np.mean(recent))

    def detect_spike(self, threshold: float = 2.0) -> bool:
        """Detect sudden temperature spike (manipulation attempt)."""
        if len(self._history) < self.window_size * 2:
            return False

        old_window = self._history[-self.window_size*2:-self.window_size]
        new_window = self._history[-self.window_size:]

        old_temp = np.mean(old_window)
        new_temp = np.mean(new_window)

        return new_temp > old_temp * threshold

    def reset(self) -> None:
        """Reset temperature history."""
        self._history.clear()


class PhaseDetector:
    """
    Detects phase transitions in conversation trajectories.

    Inspired by Ising model phase transitions:
    - Order parameter = conversation coherence
    - Phase transition = attack begins
    """

    def __init__(self, critical_threshold: float = 0.3):
        self.critical_threshold = critical_threshold

    def detect_transition(
        self,
        embeddings: List[np.ndarray],
        window_size: int = 5
    ) -> PhaseTransition:
        """
        Detect phase transition in embedding sequence.

        Order parameter = average cosine similarity within window.
        """
        if len(embeddings) < window_size * 2:
            return PhaseTransition(
                detected=False,
                transition_point=-1,
                order_parameter_before=0.0,
                order_parameter_after=0.0,
                phase_type="none"
            )

        # Compute order parameter (coherence) for each position
        order_params = []

        for i in range(window_size, len(embeddings)):
            window = embeddings[i-window_size:i]
            # Order = average pairwise similarity
            similarities = []
            for j in range(len(window)):
                for k in range(j+1, len(window)):
                    sim = np.dot(window[j], window[k]) / (
                        np.linalg.norm(window[j]) *
                        np.linalg.norm(window[k]) + 1e-8
                    )
                    similarities.append(sim)
            order_params.append(np.mean(similarities) if similarities else 0.0)

        if len(order_params) < 2:
            return PhaseTransition(
                detected=False,
                transition_point=-1,
                order_parameter_before=0.0,
                order_parameter_after=0.0,
                phase_type="none"
            )

        # Find maximum change point
        changes = np.abs(np.diff(order_params))
        max_change_idx = np.argmax(changes)
        max_change = changes[max_change_idx]

        detected = max_change > self.critical_threshold

        if detected:
            before = order_params[max_change_idx]
            after = order_params[max_change_idx + 1]

            # Classify phase type
            if max_change > 0.6:
                phase_type = "critical"
            elif max_change > 0.4:
                phase_type = "sharp"
            else:
                phase_type = "gradual"

            return PhaseTransition(
                detected=True,
                transition_point=max_change_idx + window_size,
                order_parameter_before=float(before),
                order_parameter_after=float(after),
                phase_type=phase_type
            )

        return PhaseTransition(
            detected=False,
            transition_point=-1,
            order_parameter_before=float(np.mean(order_params)),
            order_parameter_after=float(np.mean(order_params)),
            phase_type="stable"
        )


class StatMechAnalyzer:
    """
    Combined statistical mechanics analysis.

    Uses physics principles to detect adversarial patterns:
    1. Energy landscape for out-of-distribution detection
    2. Temperature profiling for manipulation detection
    3. Phase transitions for attack onset detection
    """

    def __init__(self, dim: int = 768):
        self.landscape = EnergyLandscape(temperature=1.0)
        self.temp_profiler = TemperatureProfiler()
        self.phase_detector = PhaseDetector()
        self._fitted = False

    def fit(self, normal_embeddings: List[np.ndarray]) -> None:
        """Fit analyzer on normal data."""
        self.landscape.fit(normal_embeddings)
        self._fitted = True

    def analyze(self, embedding: np.ndarray, token_entropy: float = 1.0) -> Dict:
        """Analyze embedding using all physics methods."""
        results = {
            "energy_state": None,
            "temperature_spike": False,
            "is_high_energy": False,
            "anomaly_score": 0.0,
            "physics_interpretation": ""
        }

        if not self._fitted:
            return results

        # Energy analysis
        state = self.landscape.compute_energy(embedding)
        results["energy_state"] = state
        results["is_high_energy"] = state.energy > 5.0

        # Temperature tracking
        self.temp_profiler.add_token_entropy(token_entropy)
        results["temperature_spike"] = self.temp_profiler.detect_spike()

        # Anomaly score
        score = 0.0
        if state.energy > 3.0:
            score += min(50, state.energy * 10)
        if results["temperature_spike"]:
            score += 30
        if state.probability < 0.01:
            score += 20

        results["anomaly_score"] = min(100, score)

        # Interpretation
        if results["is_high_energy"] and results["temperature_spike"]:
            results["physics_interpretation"] = "High-energy state with thermal spike - likely adversarial"
        elif results["is_high_energy"]:
            results["physics_interpretation"] = "High-energy state - unusual input"
        elif results["temperature_spike"]:
            results["physics_interpretation"] = "Temperature spike - conversation manipulation"
        else:
            results["physics_interpretation"] = "Normal thermodynamic state"

        return results


# Singleton
_analyzer: Optional[StatMechAnalyzer] = None


def get_statmech_analyzer(dim: int = 768) -> StatMechAnalyzer:
    """Get singleton analyzer."""
    global _analyzer
    if _analyzer is None:
        _analyzer = StatMechAnalyzer(dim)
    return _analyzer
