"""
Unit tests for Spectral Graph Engine.
"""

import pytest
import numpy as np
from spectral_graph import (
    SpectralGraphEngine,
    LaplacianBuilder,
    SpectralAnalyzer,
    SpectralClusterer,
    SpectralAnomalyDetector,
    LaplacianType,
    LaplacianMatrix,
)


class TestLaplacianBuilder:
    """Tests for LaplacianBuilder."""

    def setup_method(self):
        self.builder = LaplacianBuilder()

    def test_from_attention(self):
        """Test Laplacian from attention matrix."""
        attention = np.random.rand(10, 10)
        attention = attention / attention.sum(axis=1, keepdims=True)

        laplacian = self.builder.from_attention(attention)

        assert laplacian.size == 10
        assert laplacian.laplacian.shape == (10, 10)

    def test_from_adjacency_unnormalized(self):
        """Test unnormalized Laplacian."""
        adjacency = np.array([
            [0, 1, 1, 0],
            [1, 0, 1, 0],
            [1, 1, 0, 1],
            [0, 0, 1, 0]
        ], dtype=float)

        laplacian = self.builder.from_adjacency(
            adjacency, LaplacianType.UNNORMALIZED
        )

        # L = D - A, so diagonal is degree
        assert laplacian.laplacian[0, 0] == 2  # degree of node 0
        assert laplacian.laplacian[2, 2] == 3  # degree of node 2

    def test_from_adjacency_normalized(self):
        """Test normalized Laplacian."""
        adjacency = np.ones((5, 5)) - np.eye(5)
        laplacian = self.builder.from_adjacency(
            adjacency, LaplacianType.NORMALIZED
        )

        # Normalized Laplacian has 1s on diagonal
        np.testing.assert_array_almost_equal(
            np.diag(laplacian.laplacian), np.ones(5)
        )

    def test_from_embeddings(self):
        """Test Laplacian from embeddings."""
        embeddings = np.random.randn(20, 10)
        laplacian = self.builder.from_embeddings(embeddings, k_neighbors=3)

        assert laplacian.size == 20


class TestSpectralAnalyzer:
    """Tests for SpectralAnalyzer."""

    def setup_method(self):
        self.analyzer = SpectralAnalyzer()
        self.builder = LaplacianBuilder()

    def test_decompose(self):
        """Test spectral decomposition."""
        adjacency = np.ones((8, 8)) - np.eye(8)
        laplacian = self.builder.from_adjacency(adjacency)

        decomp = self.analyzer.decompose(laplacian)

        assert len(decomp.eigenvalues) == 8
        assert decomp.eigenvalues[0] >= 0  # Positive semi-definite
        assert decomp.fiedler_value >= 0

    def test_fiedler_value(self):
        """Test Fiedler value for connected graph."""
        # Complete graph has high algebraic connectivity
        adjacency = np.ones((6, 6)) - np.eye(6)
        laplacian = self.builder.from_adjacency(adjacency)

        decomp = self.analyzer.decompose(laplacian)

        assert decomp.fiedler_value > 0  # Graph is connected

    def test_graph_fourier_transform(self):
        """Test GFT computation."""
        adjacency = np.random.rand(10, 10)
        adjacency = (adjacency + adjacency.T) / 2
        laplacian = self.builder.from_adjacency(adjacency)
        decomp = self.analyzer.decompose(laplacian)

        signal = np.random.randn(10)
        gft = self.analyzer.graph_fourier_transform(signal, decomp)

        assert len(gft.coefficients) == 10
        assert abs(np.sum(gft.energy_distribution) - 1.0) < 1e-6

    def test_inverse_gft(self):
        """Test inverse GFT recovers signal."""
        adjacency = np.random.rand(8, 8)
        adjacency = (adjacency + adjacency.T) / 2
        laplacian = self.builder.from_adjacency(adjacency)
        decomp = self.analyzer.decompose(laplacian)

        signal = np.random.randn(8)
        gft = self.analyzer.graph_fourier_transform(signal, decomp)
        recovered = self.analyzer.inverse_gft(gft, decomp)

        np.testing.assert_array_almost_equal(signal, recovered)

    def test_filter_signal(self):
        """Test spectral filtering."""
        adjacency = np.random.rand(12, 12)
        adjacency = (adjacency + adjacency.T) / 2
        laplacian = self.builder.from_adjacency(adjacency)
        decomp = self.analyzer.decompose(laplacian)

        signal = np.random.randn(12)
        filtered = self.analyzer.filter_signal(
            signal, decomp, "low_pass", cutoff=3
        )

        assert len(filtered) == 12


class TestSpectralClusterer:
    """Tests for SpectralClusterer."""

    def setup_method(self):
        self.clusterer = SpectralClusterer(n_clusters=3)
        self.builder = LaplacianBuilder()
        self.analyzer = SpectralAnalyzer()

    def test_cluster(self):
        """Test spectral clustering."""
        # Create block diagonal adjacency (clear clusters)
        adjacency = np.zeros((12, 12))
        for i in range(4):
            for j in range(4):
                adjacency[i, j] = 1
                adjacency[i + 4, j + 4] = 1
                adjacency[i + 8, j + 8] = 1
        np.fill_diagonal(adjacency, 0)

        laplacian = self.builder.from_adjacency(adjacency)
        decomp = self.analyzer.decompose(laplacian)

        clustering = self.clusterer.cluster(decomp)

        assert clustering.num_clusters >= 1
        assert len(clustering.labels) == 12

    def test_cluster_sizes(self):
        """Test cluster size computation."""
        adjacency = np.random.rand(10, 10)
        adjacency = (adjacency + adjacency.T) / 2
        laplacian = self.builder.from_adjacency(adjacency)
        decomp = self.analyzer.decompose(laplacian)

        clustering = self.clusterer.cluster(decomp)

        assert sum(clustering.cluster_sizes) == 10


class TestSpectralAnomalyDetector:
    """Tests for SpectralAnomalyDetector."""

    def setup_method(self):
        self.detector = SpectralAnomalyDetector()
        self.builder = LaplacianBuilder()
        self.analyzer = SpectralAnalyzer()

    def test_detect_connected_graph(self):
        """Test detection on well-connected graph."""
        adjacency = np.ones((10, 10)) - np.eye(10)
        laplacian = self.builder.from_adjacency(adjacency)
        decomp = self.analyzer.decompose(laplacian)

        anomaly = self.detector.detect(decomp)

        # Fully connected graph should not be anomalous
        assert not anomaly.is_anomalous or anomaly.anomaly_score < 0.5

    def test_detect_disconnected_graph(self):
        """Test detection on disconnected graph."""
        # Two disconnected components
        adjacency = np.zeros((10, 10))
        adjacency[:5, :5] = 1
        adjacency[5:, 5:] = 1
        np.fill_diagonal(adjacency, 0)

        laplacian = self.builder.from_adjacency(adjacency)
        decomp = self.analyzer.decompose(laplacian)

        anomaly = self.detector.detect(decomp)

        # Should detect disconnected graph
        assert anomaly.is_anomalous


class TestSpectralGraphEngine:
    """Tests for main SpectralGraphEngine."""

    def setup_method(self):
        self.engine = SpectralGraphEngine()

    def test_analyze_attention(self):
        """Test attention analysis."""
        attention = np.random.rand(15, 15)
        attention = attention / attention.sum(axis=1, keepdims=True)

        result = self.engine.analyze_attention(attention)

        assert "spectral" in result
        assert "gft" in result
        assert "anomaly" in result

    def test_analyze_embeddings(self):
        """Test embedding analysis."""
        embeddings = np.random.randn(25, 32)
        result = self.engine.analyze_embeddings(embeddings, k_neighbors=3)

        assert "spectral" in result
        assert "clustering" in result

    def test_spectral_filter(self):
        """Test spectral filtering."""
        attention = np.random.rand(10, 10)
        signal = np.random.randn(10)

        filtered = self.engine.spectral_filter(
            attention, signal, "low_pass", 3
        )

        assert len(filtered) == 10

    def test_cluster_attention_heads(self):
        """Test attention head clustering."""
        heads = [np.random.rand(8, 8) for _ in range(6)]

        result = self.engine.cluster_attention_heads(heads)

        assert "head_clusters" in result
        assert len(result["head_clusters"]) == 6

    def test_get_fiedler_vector(self):
        """Test Fiedler vector extraction."""
        attention = np.random.rand(12, 12)
        fiedler = self.engine.get_fiedler_vector(attention)

        assert len(fiedler) == 12

    def test_stats(self):
        """Test statistics."""
        self.engine.analyze_attention(np.random.rand(5, 5))
        stats = self.engine.get_stats()

        assert stats["analyses_performed"] >= 1
        assert "capabilities" in stats


class TestIntegration:
    """Integration tests."""

    def test_full_pipeline(self):
        """Test complete analysis pipeline."""
        engine = SpectralGraphEngine()

        # Analyze attention
        attention = np.random.rand(20, 20)
        attention = attention / attention.sum(axis=1, keepdims=True)
        attn_result = engine.analyze_attention(attention)

        # Analyze embeddings
        embeddings = np.random.randn(30, 64)
        emb_result = engine.analyze_embeddings(embeddings)

        # Cluster heads
        heads = [np.random.rand(10, 10) for _ in range(8)]
        head_result = engine.cluster_attention_heads(heads)

        assert attn_result["spectral"]["fiedler_value"] >= 0
        assert emb_result["clustering"]["num_clusters"] >= 1
        assert head_result["num_clusters"] >= 1

    def test_anomaly_detection_pipeline(self):
        """Test anomaly detection on different graphs."""
        engine = SpectralGraphEngine()

        # Normal attention
        normal = np.random.rand(10, 10) + 0.1
        normal = normal / normal.sum(axis=1, keepdims=True)
        normal_result = engine.analyze_attention(normal)

        # Sparse attention (potentially anomalous)
        sparse = np.eye(10) * 0.9 + np.random.rand(10, 10) * 0.1
        sparse = sparse / sparse.sum(axis=1, keepdims=True)
        sparse_result = engine.analyze_attention(sparse)

        # Both should complete without error
        assert "anomaly" in normal_result
        assert "anomaly" in sparse_result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
