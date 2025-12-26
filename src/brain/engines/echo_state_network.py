"""
Echo State Network (ESN) Engine — Temporal Pattern Detection

Reservoir computing approach for detecting temporal anomalies in:
- Conversation flow patterns
- Typing rhythm analysis
- Request timing sequences
- Behavioral state transitions

Based on:
- Jaeger (2001) "The Echo State Approach to Reservoir Computing"
- Reservoir Computing for anomaly detection

Author: SENTINEL Team
Date: 2025-12-26
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional
from enum import Enum
from collections import deque

logger = logging.getLogger("EchoStateNetwork")


# ============================================================================
# Enums and Data Classes
# ============================================================================


class TemporalAnomalyType(str, Enum):
    """Types of temporal anomalies detected."""
    RHYTHM_CHANGE = "rhythm_change"
    PATTERN_BREAK = "pattern_break"
    TIMING_ANOMALY = "timing_anomaly"
    STATE_JUMP = "state_jump"
    RESERVOIR_SATURATION = "reservoir_saturation"


@dataclass
class ReservoirState:
    """Current state of the echo state reservoir."""
    activation: np.ndarray
    memory_capacity: float
    spectral_radius: float
    activity_level: float

    def to_dict(self) -> dict:
        return {
            "activation_norm": float(np.linalg.norm(self.activation)),
            "memory_capacity": self.memory_capacity,
            "spectral_radius": self.spectral_radius,
            "activity_level": self.activity_level
        }


@dataclass
class ESNResult:
    """Result from Echo State Network analysis."""
    is_anomaly: bool
    anomaly_score: float
    anomaly_types: List[TemporalAnomalyType]
    evidence: List[str]
    prediction_error: float
    reservoir_state: ReservoirState

    def to_dict(self) -> dict:
        return {
            "is_anomaly": self.is_anomaly,
            "anomaly_score": self.anomaly_score,
            "anomaly_types": [a.value for a in self.anomaly_types],
            "evidence": self.evidence,
            "prediction_error": self.prediction_error,
            "reservoir_state": self.reservoir_state.to_dict()
        }


# ============================================================================
# Echo State Network Implementation
# ============================================================================


class EchoStateNetwork:
    """
    Echo State Network for temporal anomaly detection.

    Reservoir computing captures temporal dependencies without
    expensive backpropagation-through-time training.

    Key properties:
    - Echo State Property: reservoir forgets initial conditions
    - Spectral radius < 1: ensures echo state property
    - Sparse connectivity: computational efficiency
    """

    def __init__(
        self,
        input_dim: int = 10,
        reservoir_size: int = 100,
        output_dim: int = 10,
        spectral_radius: float = 0.9,
        sparsity: float = 0.1,
        input_scaling: float = 0.5,
        leak_rate: float = 0.3,
        seed: int = 42
    ):
        """
        Initialize Echo State Network.

        Args:
            input_dim: Dimension of input features
            reservoir_size: Number of reservoir neurons
            output_dim: Dimension of output
            spectral_radius: Controls memory length (< 1 for ESP)
            sparsity: Fraction of non-zero reservoir connections
            input_scaling: Scaling factor for input weights
            leak_rate: Leaky integration rate (0-1)
            seed: Random seed for reproducibility
        """
        self.input_dim = input_dim
        self.reservoir_size = reservoir_size
        self.output_dim = output_dim
        self.spectral_radius = spectral_radius
        self.sparsity = sparsity
        self.input_scaling = input_scaling
        self.leak_rate = leak_rate

        np.random.seed(seed)

        # Initialize weights
        self._init_weights()

        # State
        self.state = np.zeros(reservoir_size)
        self.state_history: deque = deque(maxlen=100)

        # Output weights (to be trained)
        self.W_out = np.zeros((output_dim, reservoir_size))
        self.is_trained = False

        logger.info(
            "ESN initialized: reservoir=%d, spectral_radius=%.2f",
            reservoir_size, spectral_radius
        )

    def _init_weights(self):
        """Initialize reservoir and input weights."""
        # Input weights
        self.W_in = np.random.uniform(
            -self.input_scaling, self.input_scaling,
            (self.reservoir_size, self.input_dim)
        )

        # Reservoir weights (sparse)
        W_res = np.random.randn(self.reservoir_size, self.reservoir_size)
        mask = np.random.rand(self.reservoir_size,
                              self.reservoir_size) < self.sparsity
        W_res *= mask

        # Scale to target spectral radius
        current_radius = np.max(np.abs(np.linalg.eigvals(W_res)))
        if current_radius > 0:
            W_res *= self.spectral_radius / current_radius

        self.W_res = W_res

    def update(self, input_vec: np.ndarray) -> np.ndarray:
        """
        Update reservoir state with new input.

        Args:
            input_vec: Input vector (input_dim,)

        Returns:
            New reservoir state
        """
        # Ensure correct input dimension
        if len(input_vec) < self.input_dim:
            input_vec = np.pad(input_vec, (0, self.input_dim - len(input_vec)))
        elif len(input_vec) > self.input_dim:
            input_vec = input_vec[:self.input_dim]

        # Leaky integration update
        pre_activation = (
            np.dot(self.W_in, input_vec) +
            np.dot(self.W_res, self.state)
        )
        new_state = (
            (1 - self.leak_rate) * self.state +
            self.leak_rate * np.tanh(pre_activation)
        )

        self.state = new_state
        self.state_history.append(new_state.copy())

        return new_state

    def predict(self) -> np.ndarray:
        """Predict output from current reservoir state."""
        return np.dot(self.W_out, self.state)

    def train_output(self, states: np.ndarray, targets: np.ndarray, ridge: float = 1e-6):
        """
        Train output weights using ridge regression.

        Args:
            states: Collected reservoir states (n_samples, reservoir_size)
            targets: Target outputs (n_samples, output_dim)
            ridge: Ridge regularization parameter
        """
        # Ridge regression: W_out = targets^T @ states @ (states^T @ states + ridge*I)^-1
        n = states.shape[0]
        reg = ridge * np.eye(self.reservoir_size)
        self.W_out = np.linalg.solve(
            states.T @ states + reg,
            states.T @ targets
        ).T
        self.is_trained = True
        logger.info("ESN output weights trained on %d samples", n)

    def get_memory_capacity(self) -> float:
        """
        Estimate memory capacity of reservoir.

        Higher values = longer temporal memory.
        """
        if len(self.state_history) < 10:
            return 0.5

        # Use autocorrelation of state norms
        norms = [np.linalg.norm(s) for s in self.state_history]
        if len(norms) < 2:
            return 0.5

        mean_norm = np.mean(norms)
        var_norm = np.var(norms)
        if var_norm < 1e-10:
            return 1.0

        # Lag-1 autocorrelation
        autocorr = np.mean([
            (norms[i] - mean_norm) * (norms[i+1] - mean_norm)
            for i in range(len(norms) - 1)
        ]) / var_norm

        return float(np.clip(autocorr, 0, 1))

    def get_activity_level(self) -> float:
        """Get current reservoir activity level."""
        return float(np.mean(np.abs(self.state)))

    def reset(self):
        """Reset reservoir state."""
        self.state = np.zeros(self.reservoir_size)
        self.state_history.clear()


# ============================================================================
# Temporal Anomaly Detector
# ============================================================================


class TemporalAnomalyDetector:
    """
    Uses Echo State Network for temporal anomaly detection.

    Applications:
    - Conversation rhythm analysis
    - Typing pattern detection
    - Request timing anomalies
    - Behavioral state transitions
    """

    ANOMALY_THRESHOLD = 0.6
    PREDICTION_ERROR_THRESHOLD = 0.4
    ACTIVITY_ANOMALY_THRESHOLD = 0.8

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        # Initialize ESN
        self.esn = EchoStateNetwork(
            input_dim=self.config.get("input_dim", 10),
            reservoir_size=self.config.get("reservoir_size", 100),
            output_dim=self.config.get("output_dim", 10),
            spectral_radius=self.config.get("spectral_radius", 0.9)
        )

        # History for training
        self.feature_history: deque = deque(maxlen=1000)
        self.baseline_established = False
        self.baseline_error = 0.1

        logger.info("TemporalAnomalyDetector initialized")

    def extract_features(self, data: Dict) -> np.ndarray:
        """
        Extract temporal features from input data.

        Expected data keys:
        - timestamp: float
        - message_length: int
        - token_count: int (optional)
        - response_time_ms: float (optional)
        """
        features = np.zeros(10)

        # Time-based features
        timestamp = data.get("timestamp", 0.0)
        features[0] = np.sin(timestamp % 3600 / 3600 * 2 * np.pi)  # Hour cycle
        features[1] = np.cos(timestamp % 3600 / 3600 * 2 * np.pi)

        # Message features
        msg_len = data.get("message_length", 0)
        features[2] = np.log1p(msg_len) / 10  # Normalized log length

        token_count = data.get("token_count", msg_len // 4)
        features[3] = np.log1p(token_count) / 10

        # Response time
        response_time = data.get("response_time_ms", 100)
        features[4] = np.log1p(response_time) / 10

        # Delta features (if history available)
        if len(self.feature_history) > 0:
            prev = self.feature_history[-1]
            features[5] = features[2] - prev[2]  # Length delta
            features[6] = features[4] - prev[4]  # Response time delta

        # Normalize
        features = np.clip(features, -1, 1)

        return features

    def analyze(self, data: Dict) -> ESNResult:
        """
        Analyze temporal data for anomalies.

        Args:
            data: Dict with temporal features

        Returns:
            ESNResult with anomaly analysis
        """
        anomaly_types = []
        evidence = []

        # Extract features
        features = self.extract_features(data)
        self.feature_history.append(features)

        # Update reservoir
        state = self.esn.update(features)

        # Get prediction (if trained)
        prediction_error = 0.0
        if self.esn.is_trained:
            prediction = self.esn.predict()
            prediction_error = float(np.linalg.norm(
                prediction - features[:self.esn.output_dim]))

            if prediction_error > self.PREDICTION_ERROR_THRESHOLD:
                anomaly_types.append(TemporalAnomalyType.PATTERN_BREAK)
                evidence.append(f"Prediction error: {prediction_error:.3f}")

        # Analyze reservoir state
        memory_capacity = self.esn.get_memory_capacity()
        activity_level = self.esn.get_activity_level()

        reservoir_state = ReservoirState(
            activation=state,
            memory_capacity=memory_capacity,
            spectral_radius=self.esn.spectral_radius,
            activity_level=activity_level
        )

        # Check for activity anomalies
        if activity_level > self.ACTIVITY_ANOMALY_THRESHOLD:
            anomaly_types.append(TemporalAnomalyType.RESERVOIR_SATURATION)
            evidence.append(f"High reservoir activity: {activity_level:.3f}")

        # Check for state jumps
        if len(self.esn.state_history) >= 2:
            state_delta = np.linalg.norm(
                self.esn.state_history[-1] - self.esn.state_history[-2]
            )
            if state_delta > 0.5:
                anomaly_types.append(TemporalAnomalyType.STATE_JUMP)
                evidence.append(f"State jump: {state_delta:.3f}")

        # Calculate overall anomaly score
        anomaly_score = 0.0
        if anomaly_types:
            anomaly_score = min(1.0, len(anomaly_types)
                                * 0.3 + prediction_error)

        is_anomaly = anomaly_score > self.ANOMALY_THRESHOLD

        if is_anomaly:
            logger.warning(
                "Temporal anomaly detected: %s (score=%.2f)",
                [a.value for a in anomaly_types], anomaly_score
            )

        return ESNResult(
            is_anomaly=is_anomaly,
            anomaly_score=anomaly_score,
            anomaly_types=anomaly_types,
            evidence=evidence,
            prediction_error=prediction_error,
            reservoir_state=reservoir_state
        )

    def train_baseline(self, data_sequence: List[Dict]):
        """
        Train ESN on baseline normal behavior.

        Args:
            data_sequence: List of temporal data points
        """
        if len(data_sequence) < 10:
            logger.warning("Need at least 10 samples for baseline training")
            return

        # Collect states and targets
        self.esn.reset()
        states = []
        targets = []

        for data in data_sequence:
            features = self.extract_features(data)
            state = self.esn.update(features)
            states.append(state)
            targets.append(features[:self.esn.output_dim])

        states = np.array(states[:-1])  # All but last
        targets = np.array(targets[1:])  # All but first (predict next)

        # Train output weights
        self.esn.train_output(states, targets)
        self.baseline_established = True

        # Calculate baseline error
        predictions = states @ self.esn.W_out.T
        self.baseline_error = float(
            np.mean(np.linalg.norm(predictions - targets, axis=1)))

        logger.info("Baseline established with error=%.3f",
                    self.baseline_error)


# ============================================================================
# Factory
# ============================================================================


_detector: Optional[TemporalAnomalyDetector] = None


def get_temporal_anomaly_detector() -> TemporalAnomalyDetector:
    """Get singleton temporal anomaly detector."""
    global _detector
    if _detector is None:
        _detector = TemporalAnomalyDetector()
    return _detector


def create_engine(config: Optional[Dict] = None) -> TemporalAnomalyDetector:
    """Create a new TemporalAnomalyDetector instance."""
    return TemporalAnomalyDetector(config)
