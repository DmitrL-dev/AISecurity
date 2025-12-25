"""
Spectral Graph Engine - Graph Spectral Analysis for Attention Patterns

Based on 2025 research:
  - SpGAT (arXiv 2025): Spectral Graph Attention Network
  - SAN: Spectral Attention Network with learned positional encodings
  - AAAI 2025: Graph Transformers and attention-based architectures
  - SAT: Spectral Adversarial Training for GNN robustness

Theory:
  Graph spectral analysis studies the eigenvalues/eigenvectors of
  graph Laplacian. For attention matrices viewed as graphs:
  - Eigenvalues reveal connectivity structure
  - Fiedler value indicates graph cohesion
  - Spectral gap measures separation
  - Graph Fourier Transform for frequency analysis

Author: SENTINEL Team
Date: 2025-12-09
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any

logger = logging.getLogger("SpectralGraph")


# ============================================================================
# Enums and Data Classes
# ============================================================================

class LaplacianType(str, Enum):
    """Types of graph Laplacian."""
    UNNORMALIZED = "unnormalized"  # L = D - A
    NORMALIZED = "normalized"      # L = I - D^(-1/2) A D^(-1/2)
    RANDOM_WALK = "random_walk"    # L = I - D^(-1) A


class SpectralFeatureType(str, Enum):
    """Types of spectral features."""
    EIGENVALUES = "eigenvalues"
    FIEDLER_VALUE = "fiedler_value"
    SPECTRAL_GAP = "spectral_gap"
    ALGEBRAIC_CONNECTIVITY = "algebraic_connectivity"


@dataclass
class LaplacianMatrix:
    """Graph Laplacian matrix and components."""
    laplacian: np.ndarray
    degree_matrix: np.ndarray
    adjacency_matrix: np.ndarray
    laplacian_type: LaplacianType

    @property
    def size(self) -> int:
        return self.laplacian.shape[0] if self.laplacian is not None else 0


@dataclass
class SpectralDecomposition:
    """Eigendecomposition of Laplacian."""
    eigenvalues: np.ndarray
    eigenvectors: np.ndarray
    fiedler_value: float  # Second smallest eigenvalue
    fiedler_vector: np.ndarray  # Corresponding eigenvector
    spectral_gap: float  # λ_2 - λ_1
    algebraic_connectivity: float  # Same as Fiedler value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "num_eigenvalues": len(self.eigenvalues),
            "fiedler_value": self.fiedler_value,
            "spectral_gap": self.spectral_gap,
            "algebraic_connectivity": self.algebraic_connectivity,
            "min_eigenvalue": float(self.eigenvalues.min()),
            "max_eigenvalue": float(self.eigenvalues.max())
        }


@dataclass
class GraphFourierTransform:
    """Graph Fourier Transform representation."""
    coefficients: np.ndarray
    frequencies: np.ndarray  # Eigenvalues as frequencies
    energy_distribution: np.ndarray

    def low_frequency_energy(self, k: int = 5) -> float:
        """Energy in first k frequency components."""
        return float(np.sum(self.energy_distribution[:k]))

    def high_frequency_energy(self, k: int = 5) -> float:
        """Energy in last k frequency components."""
        return float(np.sum(self.energy_distribution[-k:]))


@dataclass
class SpectralClustering:
    """Result of spectral clustering."""
    labels: np.ndarray
    num_clusters: int
    cluster_sizes: List[int]
    silhouette_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "num_clusters": self.num_clusters,
            "cluster_sizes": self.cluster_sizes,
            "silhouette_score": self.silhouette_score
        }


@dataclass
class SpectralAnomaly:
    """Detected spectral anomaly."""
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
# Laplacian Builder
# ============================================================================

class LaplacianBuilder:
    """
    Constructs graph Laplacian from adjacency or attention matrices.
    """

    def __init__(self, epsilon: float = 1e-10):
        self.epsilon = epsilon

    def from_attention(
        self,
        attention: np.ndarray,
        threshold: float = 0.0,
        laplacian_type: LaplacianType = LaplacianType.NORMALIZED
    ) -> LaplacianMatrix:
        """
        Build Laplacian from attention matrix.

        Attention weights become edge weights.
        """
        n = attention.shape[0]

        # Threshold to create adjacency
        adjacency = np.where(attention > threshold, attention, 0.0)

        # Make symmetric (undirected graph)
        adjacency = (adjacency + adjacency.T) / 2

        return self.from_adjacency(adjacency, laplacian_type)

    def from_adjacency(
        self,
        adjacency: np.ndarray,
        laplacian_type: LaplacianType = LaplacianType.NORMALIZED
    ) -> LaplacianMatrix:
        """Build Laplacian from adjacency matrix."""
        n = adjacency.shape[0]

        # Degree matrix
        degrees = adjacency.sum(axis=1)
        degree_matrix = np.diag(degrees)

        if laplacian_type == LaplacianType.UNNORMALIZED:
            laplacian = degree_matrix - adjacency

        elif laplacian_type == LaplacianType.NORMALIZED:
            # L = I - D^(-1/2) A D^(-1/2)
            d_inv_sqrt = np.diag(1.0 / np.sqrt(degrees + self.epsilon))
            laplacian = np.eye(n) - d_inv_sqrt @ adjacency @ d_inv_sqrt

        elif laplacian_type == LaplacianType.RANDOM_WALK:
            # L = I - D^(-1) A
            d_inv = np.diag(1.0 / (degrees + self.epsilon))
            laplacian = np.eye(n) - d_inv @ adjacency

        return LaplacianMatrix(
            laplacian=laplacian,
            degree_matrix=degree_matrix,
            adjacency_matrix=adjacency,
            laplacian_type=laplacian_type
        )

    def from_embeddings(
        self,
        embeddings: np.ndarray,
        k_neighbors: int = 5,
        laplacian_type: LaplacianType = LaplacianType.NORMALIZED
    ) -> LaplacianMatrix:
        """Build Laplacian from embedding similarity graph."""
        n = len(embeddings)

        # Build k-NN similarity graph
        adjacency = np.zeros((n, n))

        for i in range(n):
            # Compute distances
            distances = np.linalg.norm(embeddings - embeddings[i], axis=1)

            # Find k nearest neighbors
            nearest = np.argsort(distances)[1:k_neighbors+1]

            for j in nearest:
                similarity = 1.0 / (1.0 + distances[j])
                adjacency[i, j] = similarity
                adjacency[j, i] = similarity

        return self.from_adjacency(adjacency, laplacian_type)


# ============================================================================
# Spectral Analyzer
# ============================================================================

class SpectralAnalyzer:
    """
    Analyzes spectral properties of graph Laplacian.
    """

    def decompose(self, laplacian: LaplacianMatrix) -> SpectralDecomposition:
        """Compute eigendecomposition of Laplacian."""
        L = laplacian.laplacian

        # Compute eigenvalues and eigenvectors
        eigenvalues, eigenvectors = np.linalg.eigh(L)

        # Sort by eigenvalue
        idx = np.argsort(eigenvalues)
        eigenvalues = eigenvalues[idx]
        eigenvectors = eigenvectors[:, idx]

        # Fiedler value (second smallest eigenvalue)
        fiedler_value = float(eigenvalues[1]) if len(eigenvalues) > 1 else 0.0
        fiedler_vector = eigenvectors[:, 1] if len(
            eigenvalues) > 1 else np.zeros(L.shape[0])

        # Spectral gap
        spectral_gap = fiedler_value - float(eigenvalues[0])

        return SpectralDecomposition(
            eigenvalues=eigenvalues,
            eigenvectors=eigenvectors,
            fiedler_value=fiedler_value,
            fiedler_vector=fiedler_vector,
            spectral_gap=spectral_gap,
            algebraic_connectivity=fiedler_value
        )

    def graph_fourier_transform(
        self,
        signal: np.ndarray,
        decomposition: SpectralDecomposition
    ) -> GraphFourierTransform:
        """
        Compute Graph Fourier Transform of signal.

        GFT = U^T * signal, where U is eigenvector matrix.
        """
        # Project signal onto eigenvector basis
        coefficients = decomposition.eigenvectors.T @ signal

        # Energy distribution
        energy = coefficients ** 2
        total_energy = np.sum(energy) + 1e-10
        energy_distribution = energy / total_energy

        return GraphFourierTransform(
            coefficients=coefficients,
            frequencies=decomposition.eigenvalues,
            energy_distribution=energy_distribution
        )

    def inverse_gft(
        self,
        gft: GraphFourierTransform,
        decomposition: SpectralDecomposition
    ) -> np.ndarray:
        """Inverse Graph Fourier Transform."""
        return decomposition.eigenvectors @ gft.coefficients

    def filter_signal(
        self,
        signal: np.ndarray,
        decomposition: SpectralDecomposition,
        filter_type: str = "low_pass",
        cutoff: int = 5
    ) -> np.ndarray:
        """Apply spectral filter to graph signal."""
        gft = self.graph_fourier_transform(signal, decomposition)

        if filter_type == "low_pass":
            # Keep only low frequency components
            filtered = gft.coefficients.copy()
            filtered[cutoff:] = 0
        elif filter_type == "high_pass":
            # Keep only high frequency components
            filtered = gft.coefficients.copy()
            filtered[:cutoff] = 0
        elif filter_type == "band_pass":
            # Keep middle frequencies
            filtered = gft.coefficients.copy()
            filtered[:cutoff//2] = 0
            filtered[-(cutoff//2):] = 0
        else:
            filtered = gft.coefficients

        return decomposition.eigenvectors @ filtered


# ============================================================================
# Spectral Clustering
# ============================================================================

class SpectralClusterer:
    """
    Spectral clustering using Laplacian eigenvectors.
    """

    def __init__(self, n_clusters: int = 2):
        self.n_clusters = n_clusters

    def cluster(
        self,
        decomposition: SpectralDecomposition
    ) -> SpectralClustering:
        """
        Perform spectral clustering using k smallest eigenvectors.
        """
        k = min(self.n_clusters, len(decomposition.eigenvalues) - 1)

        # Use k smallest non-trivial eigenvectors
        embedding = decomposition.eigenvectors[:, 1:k+1]

        # Simple k-means in spectral space
        labels = self._kmeans(embedding, k)

        # Compute cluster sizes
        unique_labels = np.unique(labels)
        cluster_sizes = [int(np.sum(labels == l)) for l in unique_labels]

        # Compute silhouette score
        silhouette = self._silhouette_score(embedding, labels)

        return SpectralClustering(
            labels=labels,
            num_clusters=len(unique_labels),
            cluster_sizes=cluster_sizes,
            silhouette_score=silhouette
        )

    def _kmeans(self, X: np.ndarray, k: int, max_iter: int = 100) -> np.ndarray:
        """Simple k-means clustering."""
        n = len(X)
        if n <= k:
            return np.arange(n)

        # Random initialization
        np.random.seed(42)
        idx = np.random.choice(n, k, replace=False)
        centroids = X[idx]

        for _ in range(max_iter):
            # Assign labels
            distances = np.zeros((n, k))
            for i in range(k):
                distances[:, i] = np.linalg.norm(X - centroids[i], axis=1)
            labels = np.argmin(distances, axis=1)

            # Update centroids
            new_centroids = np.zeros_like(centroids)
            for i in range(k):
                mask = labels == i
                if np.any(mask):
                    new_centroids[i] = X[mask].mean(axis=0)
                else:
                    new_centroids[i] = centroids[i]

            if np.allclose(centroids, new_centroids):
                break
            centroids = new_centroids

        return labels

    def _silhouette_score(self, X: np.ndarray, labels: np.ndarray) -> float:
        """Compute silhouette score."""
        n = len(X)
        if n < 2:
            return 0.0

        unique_labels = np.unique(labels)
        if len(unique_labels) < 2:
            return 0.0

        silhouettes = []
        for i in range(n):
            # Average distance to same cluster
            same_cluster = labels == labels[i]
            if np.sum(same_cluster) <= 1:
                a = 0
            else:
                a = np.mean(np.linalg.norm(X[same_cluster] - X[i], axis=1))

            # Minimum average distance to other clusters
            b = np.inf
            for label in unique_labels:
                if label != labels[i]:
                    other = labels == label
                    if np.sum(other) > 0:
                        b = min(b, np.mean(np.linalg.norm(
                            X[other] - X[i], axis=1)))

            if b == np.inf:
                b = 0

            s = (b - a) / (max(a, b) + 1e-10)
            silhouettes.append(s)

        return float(np.mean(silhouettes))


# ============================================================================
# Spectral Anomaly Detector
# ============================================================================

class SpectralAnomalyDetector:
    """
    Detects anomalies using spectral properties.
    """

    def __init__(
        self,
        fiedler_threshold: float = 0.01,
        gap_threshold: float = 0.1,
        energy_threshold: float = 0.3
    ):
        self.fiedler_threshold = fiedler_threshold
        self.gap_threshold = gap_threshold
        self.energy_threshold = energy_threshold

    def detect(
        self,
        decomposition: SpectralDecomposition,
        gft: Optional[GraphFourierTransform] = None
    ) -> SpectralAnomaly:
        """Detect spectral anomalies."""
        anomalies = []
        details = {}
        total_score = 0.0

        # 1. Check Fiedler value (algebraic connectivity)
        if decomposition.fiedler_value < self.fiedler_threshold:
            anomalies.append("low_connectivity")
            total_score += 0.3
            details["fiedler_value"] = decomposition.fiedler_value

        # 2. Check spectral gap
        if decomposition.spectral_gap < self.gap_threshold:
            anomalies.append("small_spectral_gap")
            total_score += 0.2
            details["spectral_gap"] = decomposition.spectral_gap

        # 3. Check for nearly zero eigenvalues (disconnected components)
        near_zero = np.sum(decomposition.eigenvalues < 1e-6)
        if near_zero > 1:
            anomalies.append("disconnected_graph")
            total_score += 0.3
            details["disconnected_components"] = int(near_zero)

        # 4. Check energy distribution if GFT available
        if gft is not None:
            high_freq_energy = gft.high_frequency_energy(5)
            if high_freq_energy > self.energy_threshold:
                anomalies.append("high_frequency_anomaly")
                total_score += 0.2
                details["high_freq_energy"] = high_freq_energy

        anomaly_type = anomalies[0] if anomalies else "none"

        return SpectralAnomaly(
            is_anomalous=len(anomalies) > 0,
            anomaly_score=min(1.0, total_score),
            anomaly_type=anomaly_type,
            details=details
        )


# ============================================================================
# Main Spectral Graph Engine
# ============================================================================

class SpectralGraphEngine:
    """
    Main engine for spectral graph analysis.

    Provides:
    - Laplacian construction from attention/embeddings
    - Eigenvalue analysis (Fiedler, spectral gap)
    - Graph Fourier Transform
    - Spectral clustering
    - Anomaly detection
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

        self.laplacian_builder = LaplacianBuilder()
        self.analyzer = SpectralAnalyzer()
        self.clusterer = SpectralClusterer(
            n_clusters=self.config.get("n_clusters", 3)
        )
        self.anomaly_detector = SpectralAnomalyDetector(
            fiedler_threshold=self.config.get("fiedler_threshold", 0.01),
            gap_threshold=self.config.get("gap_threshold", 0.1)
        )

        self.analysis_count = 0

        logger.info("SpectralGraphEngine initialized")

    def analyze_attention(
        self,
        attention: np.ndarray,
        threshold: float = 0.0
    ) -> Dict[str, Any]:
        """Full spectral analysis of attention matrix."""
        # Build Laplacian
        laplacian = self.laplacian_builder.from_attention(
            attention, threshold, LaplacianType.NORMALIZED
        )

        # Spectral decomposition
        decomposition = self.analyzer.decompose(laplacian)

        # Graph Fourier Transform of uniform signal
        signal = np.ones(attention.shape[0]) / attention.shape[0]
        gft = self.analyzer.graph_fourier_transform(signal, decomposition)

        # Anomaly detection
        anomaly = self.anomaly_detector.detect(decomposition, gft)

        self.analysis_count += 1

        return {
            "spectral": decomposition.to_dict(),
            "gft": {
                "low_freq_energy": gft.low_frequency_energy(5),
                "high_freq_energy": gft.high_frequency_energy(5)
            },
            "anomaly": anomaly.to_dict()
        }

    def analyze_embeddings(
        self,
        embeddings: np.ndarray,
        k_neighbors: int = 5
    ) -> Dict[str, Any]:
        """Spectral analysis of embedding similarity graph."""
        # Build Laplacian
        laplacian = self.laplacian_builder.from_embeddings(
            embeddings, k_neighbors, LaplacianType.NORMALIZED
        )

        # Spectral decomposition
        decomposition = self.analyzer.decompose(laplacian)

        # Clustering
        clustering = self.clusterer.cluster(decomposition)

        # Anomaly detection
        anomaly = self.anomaly_detector.detect(decomposition)

        self.analysis_count += 1

        return {
            "spectral": decomposition.to_dict(),
            "clustering": clustering.to_dict(),
            "anomaly": anomaly.to_dict()
        }

    def spectral_filter(
        self,
        attention: np.ndarray,
        signal: np.ndarray,
        filter_type: str = "low_pass",
        cutoff: int = 5
    ) -> np.ndarray:
        """Apply spectral filter to graph signal."""
        laplacian = self.laplacian_builder.from_attention(attention)
        decomposition = self.analyzer.decompose(laplacian)

        return self.analyzer.filter_signal(
            signal, decomposition, filter_type, cutoff
        )

    def cluster_attention_heads(
        self,
        attention_heads: List[np.ndarray]
    ) -> Dict[str, Any]:
        """Cluster attention heads by spectral similarity."""
        # Extract spectral features for each head
        features = []
        for head in attention_heads:
            laplacian = self.laplacian_builder.from_attention(head)
            decomp = self.analyzer.decompose(laplacian)

            # Use first few eigenvalues as features
            k = min(5, len(decomp.eigenvalues))
            features.append(decomp.eigenvalues[:k])

        # Pad to same length
        max_len = max(len(f) for f in features)
        features = [np.pad(f, (0, max_len - len(f))) for f in features]
        features = np.array(features)

        # Build similarity graph between heads
        laplacian = self.laplacian_builder.from_embeddings(
            features, k_neighbors=min(3, len(features) - 1)
        )
        decomposition = self.analyzer.decompose(laplacian)
        clustering = self.clusterer.cluster(decomposition)

        return {
            "head_clusters": clustering.labels.tolist(),
            "num_clusters": clustering.num_clusters,
            "silhouette": clustering.silhouette_score
        }

    def get_fiedler_vector(self, attention: np.ndarray) -> np.ndarray:
        """Get Fiedler vector for graph partitioning."""
        laplacian = self.laplacian_builder.from_attention(attention)
        decomposition = self.analyzer.decompose(laplacian)
        return decomposition.fiedler_vector

    def get_stats(self) -> Dict[str, Any]:
        return {
            "analyses_performed": self.analysis_count,
            "capabilities": [
                "laplacian_construction",
                "spectral_decomposition",
                "graph_fourier_transform",
                "spectral_clustering",
                "anomaly_detection"
            ]
        }
