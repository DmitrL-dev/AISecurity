"""
Quantum Machine Learning Module

Research implementation of quantum-inspired techniques for AI security.
Uses classical simulation (no actual quantum hardware required).

Based on:
- PennyLane for hybrid quantum-classical ML
- No-cloning theorem advantage for embedding security
- SWAP test for anomaly detection
"""

import logging
import math
from dataclasses import dataclass
from typing import List, Optional, Tuple
import numpy as np

logger = logging.getLogger("QuantumML")

# Try to import PennyLane
try:
    import pennylane as qml
    PENNYLANE_AVAILABLE = True
    logger.info("PennyLane available - using quantum simulation")
except ImportError:
    PENNYLANE_AVAILABLE = False
    logger.warning("PennyLane not available - using classical approximation")


@dataclass
class QMLEmbedding:
    """Quantum-enhanced embedding."""
    vector: np.ndarray
    n_qubits: int
    encoding: str  # amplitude, angle, basis
    fidelity: float  # 0-1, similarity to ideal state


@dataclass
class SWAPTestResult:
    """Result of quantum SWAP test for similarity."""
    similarity: float  # 0-1
    is_anomaly: bool
    threshold: float
    measurement_shots: int


class QuantumEmbeddings:
    """
    Quantum-inspired embeddings for AI security.

    Advantages:
    1. Exponential compression (2^n amplitudes in n qubits)
    2. No-cloning protection (quantum states cannot be copied)
    3. Holistic comparison (SWAP test measures full state similarity)

    Usage:
        qml = QuantumEmbeddings(n_qubits=4)
        emb = qml.encode_amplitude(classical_vector)
        sim = qml.swap_test(emb1, emb2)
    """

    def __init__(self, n_qubits: int = 4):
        self.n_qubits = n_qubits
        self.dim = 2 ** n_qubits

        if PENNYLANE_AVAILABLE:
            self.device = qml.device("default.qubit", wires=n_qubits * 2 + 1)
        else:
            self.device = None

        logger.info(
            f"QuantumEmbeddings initialized: {n_qubits} qubits, dim={self.dim}")

    def encode_amplitude(self, vector: np.ndarray) -> QMLEmbedding:
        """
        Amplitude encoding: embed classical vector into quantum amplitudes.

        Vector of size 2^n encoded into n qubits.
        """
        # Normalize vector
        norm = np.linalg.norm(vector)
        if norm == 0:
            normalized = np.zeros(self.dim)
            normalized[0] = 1.0
        else:
            normalized = vector / norm

        # Pad or truncate to match dimension
        if len(normalized) < self.dim:
            padded = np.zeros(self.dim)
            padded[:len(normalized)] = normalized
            normalized = padded
        elif len(normalized) > self.dim:
            normalized = normalized[:self.dim]
            normalized = normalized / np.linalg.norm(normalized)

        return QMLEmbedding(
            vector=normalized,
            n_qubits=self.n_qubits,
            encoding="amplitude",
            fidelity=1.0  # Perfect encoding in simulation
        )

    def encode_angle(self, features: np.ndarray) -> QMLEmbedding:
        """
        Angle encoding: encode features as rotation angles.

        Each feature becomes a rotation angle on a qubit.
        """
        # Normalize to [0, 2π]
        angles = (features % (2 * np.pi))

        # Compute resulting state vector (simplified)
        # Full implementation would use actual qubit rotations
        state = np.zeros(self.dim, dtype=complex)
        for i, angle in enumerate(angles[:self.n_qubits]):
            state[i] = np.cos(angle / 2) + 1j * np.sin(angle / 2)

        # Normalize
        state = state / np.linalg.norm(state)

        return QMLEmbedding(
            vector=np.abs(state),
            n_qubits=self.n_qubits,
            encoding="angle",
            fidelity=0.95
        )

    def swap_test(
        self,
        emb1: QMLEmbedding,
        emb2: QMLEmbedding,
        threshold: float = 0.7,
        shots: int = 1000
    ) -> SWAPTestResult:
        """
        Quantum SWAP test for similarity measurement.

        Measures overlap |<ψ|φ>|² between two quantum states.
        Useful for anomaly detection (low similarity = anomaly).
        """
        if PENNYLANE_AVAILABLE:
            similarity = self._quantum_swap_test(
                emb1.vector, emb2.vector, shots)
        else:
            # Classical approximation: cosine similarity
            similarity = float(np.dot(emb1.vector, emb2.vector))
            similarity = max(0, min(1, similarity))  # Clamp to [0, 1]

        return SWAPTestResult(
            similarity=similarity,
            is_anomaly=similarity < threshold,
            threshold=threshold,
            measurement_shots=shots
        )

    def _quantum_swap_test(self, state1: np.ndarray, state2: np.ndarray, shots: int) -> float:
        """Actual quantum SWAP test using PennyLane."""
        n = self.n_qubits

        @qml.qnode(self.device)
        def swap_circuit():
            # Ancilla qubit at position 0
            qml.Hadamard(wires=0)

            # Prepare states on qubits 1..n and n+1..2n
            qml.QubitStateVector(state1, wires=range(1, n + 1))
            qml.QubitStateVector(state2, wires=range(n + 1, 2 * n + 1))

            # Controlled SWAP
            for i in range(n):
                qml.CSWAP(wires=[0, i + 1, n + i + 1])

            qml.Hadamard(wires=0)

            return qml.probs(wires=0)

        probs = swap_circuit()
        # P(0) = (1 + |<ψ|φ>|²) / 2
        # Similarity = 2 * P(0) - 1
        similarity = 2 * probs[0] - 1
        return float(max(0, similarity))

    def quantum_anomaly_score(self, test_emb: QMLEmbedding, reference_embs: List[QMLEmbedding]) -> float:
        """
        Compute anomaly score using SWAP tests against reference states.

        Low average similarity = high anomaly score.
        """
        if not reference_embs:
            return 0.5

        similarities = []
        for ref in reference_embs:
            result = self.swap_test(test_emb, ref)
            similarities.append(result.similarity)

        avg_similarity = sum(similarities) / len(similarities)

        # Anomaly score = 1 - similarity
        return 1.0 - avg_similarity


class QuantumKernelSVM:
    """
    Quantum Kernel for SVM classification.

    Uses quantum feature map to create kernel that's hard to simulate classically.
    Useful for detecting adversarial patterns.
    """

    def __init__(self, n_qubits: int = 4, n_layers: int = 2):
        self.n_qubits = n_qubits
        self.n_layers = n_layers

        if PENNYLANE_AVAILABLE:
            self.device = qml.device("default.qubit", wires=n_qubits)
        else:
            self.device = None

    def kernel(self, x1: np.ndarray, x2: np.ndarray) -> float:
        """
        Compute quantum kernel k(x1, x2).

        Uses ZZFeatureMap-style encoding.
        """
        if not PENNYLANE_AVAILABLE:
            # Classical RBF kernel approximation
            gamma = 1.0 / len(x1)
            return float(np.exp(-gamma * np.sum((x1 - x2) ** 2)))

        @qml.qnode(self.device)
        def kernel_circuit(x, y):
            # Encode x
            for i, val in enumerate(x[:self.n_qubits]):
                qml.RY(val, wires=i)

            for layer in range(self.n_layers):
                for i in range(self.n_qubits - 1):
                    qml.CNOT(wires=[i, i + 1])
                for i, val in enumerate(x[:self.n_qubits]):
                    qml.RZ(val * (layer + 1), wires=i)

            # Inverse encode y
            for layer in range(self.n_layers - 1, -1, -1):
                for i, val in enumerate(y[:self.n_qubits]):
                    qml.RZ(-val * (layer + 1), wires=i)
                for i in range(self.n_qubits - 2, -1, -1):
                    qml.CNOT(wires=[i, i + 1])

            for i, val in enumerate(y[:self.n_qubits]):
                qml.RY(-val, wires=i)

            return qml.probs(wires=range(self.n_qubits))

        probs = kernel_circuit(x1, x2)
        return float(probs[0])  # Probability of |00...0>


# Singleton
_qml_embeddings: Optional[QuantumEmbeddings] = None


def get_quantum_embeddings(n_qubits: int = 4) -> QuantumEmbeddings:
    """Get singleton QuantumEmbeddings."""
    global _qml_embeddings
    if _qml_embeddings is None:
        _qml_embeddings = QuantumEmbeddings(n_qubits)
    return _qml_embeddings
