"""
Unit tests for Enhanced TDA Module.
"""

import pytest
import numpy as np
from engines.tda_enhanced import (
    TDAEnhancedEngine,
    ZigzagEngine,
    AttentionTopologyEngine,
    TopologicalFingerprinter,
    PersistenceDistance,
    PersistenceDiagram,
    PersistencePair,
    ZigzagPersistence,
    TopologicalFingerprint,
)


class TestPersistencePair:
    """Tests for PersistencePair."""

    def test_lifetime(self):
        """Test lifetime computation."""
        pair = PersistencePair(birth=0.0, death=1.0, dimension=0)
        assert pair.lifetime == 1.0

    def test_lifetime_infinite(self):
        """Test infinite lifetime."""
        pair = PersistencePair(birth=0.0, death=np.inf, dimension=0)
        assert pair.lifetime == np.inf

    def test_midpoint(self):
        """Test midpoint computation."""
        pair = PersistencePair(birth=0.0, death=2.0, dimension=0)
        assert pair.midpoint == 1.0


class TestPersistenceDiagram:
    """Tests for PersistenceDiagram."""

    def setup_method(self):
        self.diagram = PersistenceDiagram()
        self.diagram.pairs = [
            PersistencePair(0.0, 1.0, 0),
            PersistencePair(0.0, 2.0, 0),
            PersistencePair(0.5, 1.5, 1),
            PersistencePair(0.5, 3.0, 1),
        ]

    def test_get_pairs(self):
        """Test getting pairs by dimension."""
        h0_pairs = self.diagram.get_pairs(0)
        h1_pairs = self.diagram.get_pairs(1)

        assert len(h0_pairs) == 2
        assert len(h1_pairs) == 2

    def test_betti_number(self):
        """Test Betti number computation."""
        assert self.diagram.betti_number(0) == 2
        assert self.diagram.betti_number(1) == 2

    def test_total_persistence(self):
        """Test total persistence."""
        # H0: 1.0 + 2.0 = 3.0
        assert self.diagram.total_persistence(0) == 3.0
        # H1: 1.0 + 2.5 = 3.5
        assert self.diagram.total_persistence(1) == 3.5

    def test_entropy(self):
        """Test persistence entropy."""
        entropy = self.diagram.entropy(0)
        assert entropy > 0

    def test_to_array(self):
        """Test conversion to array."""
        arr = self.diagram.to_array(0)
        assert arr.shape == (2, 2)


class TestPersistenceDistance:
    """Tests for distance metrics."""

    def test_bottleneck_empty(self):
        """Test bottleneck with empty diagrams."""
        dist = PersistenceDistance.bottleneck_distance(
            np.array([]).reshape(0, 2),
            np.array([]).reshape(0, 2)
        )
        assert dist == 0.0

    def test_bottleneck_same(self):
        """Test bottleneck with identical diagrams."""
        dgm = np.array([[0.0, 1.0], [0.5, 2.0]])
        dist = PersistenceDistance.bottleneck_distance(dgm, dgm)
        assert dist == 0.0

    def test_bottleneck_different(self):
        """Test bottleneck with different diagrams."""
        dgm1 = np.array([[0.0, 1.0]])
        dgm2 = np.array([[0.0, 2.0]])
        dist = PersistenceDistance.bottleneck_distance(dgm1, dgm2)
        assert dist > 0

    def test_wasserstein_empty(self):
        """Test Wasserstein with empty diagrams."""
        dist = PersistenceDistance.wasserstein_distance(
            np.array([]).reshape(0, 2),
            np.array([]).reshape(0, 2)
        )
        assert dist == 0.0

    def test_wasserstein_same(self):
        """Test Wasserstein with identical diagrams."""
        dgm = np.array([[0.0, 1.0], [0.5, 2.0]])
        dist = PersistenceDistance.wasserstein_distance(dgm, dgm)
        assert dist == 0.0

    def test_landscape_distance(self):
        """Test landscape distance."""
        l1 = np.random.randn(3, 50)
        l2 = np.random.randn(3, 50)
        dist = PersistenceDistance.landscape_distance(l1, l2)
        assert dist > 0


class TestZigzagEngine:
    """Tests for ZigzagEngine."""

    def setup_method(self):
        self.engine = ZigzagEngine(max_dim=1)

    def test_analyze_layer_sequence(self):
        """Test layer sequence analysis."""
        # Create synthetic layer activations
        layers = [
            np.random.randn(10, 64) for _ in range(5)
        ]

        result = self.engine.analyze_layer_sequence(layers)

        assert len(result.layer_diagrams) == 5
        assert len(result.feature_flow(0)) == 5

    def test_stability_score(self):
        """Test stability score computation."""
        layers = [
            np.random.randn(10, 32) for _ in range(4)
        ]

        result = self.engine.analyze_layer_sequence(layers)
        score = result.stability_score()

        assert 0.0 <= score <= 1.0

    def test_feature_flow(self):
        """Test feature flow tracking."""
        layers = [
            np.random.randn(15, 48) for _ in range(3)
        ]

        result = self.engine.analyze_layer_sequence(layers)
        h0_flow = result.feature_flow(0)
        h1_flow = result.feature_flow(1)

        assert len(h0_flow) == 3
        assert len(h1_flow) == 3


class TestAttentionTopologyEngine:
    """Tests for AttentionTopologyEngine."""

    def setup_method(self):
        self.engine = AttentionTopologyEngine(threshold=0.1)

    def test_analyze_attention(self):
        """Test attention analysis."""
        # Create random attention matrix
        attention = np.random.rand(20, 20)
        attention = attention / attention.sum(axis=1, keepdims=True)

        result = self.engine.analyze_attention(attention)

        assert "b0" in result.graph_betti
        assert result.attention_entropy >= 0

    def test_sparse_attention(self):
        """Test sparse attention patterns."""
        # Create sparse attention
        attention = np.zeros((10, 10))
        attention[np.arange(10), np.arange(10)] = 1.0  # Diagonal only

        result = self.engine.analyze_attention(attention)

        # High sparsity expected
        assert result.sparsity > 0.5

    def test_dense_attention(self):
        """Test dense attention patterns."""
        # Create dense uniform attention above threshold
        attention = np.ones((10, 10)) * 0.2  # Above 0.1 threshold

        result = self.engine.analyze_attention(attention)

        # Low sparsity expected (many edges)
        assert result.sparsity < 0.5

    def test_anomaly_detection(self):
        """Test anomaly detection in attention."""
        # Create anomalous pattern
        attention = np.eye(10) * 0.5
        for i in range(5):
            attention[i, (i + 1) % 10] = 0.5

        result = self.engine.analyze_attention(attention)

        # Should have some graph structure
        assert result.graph_betti["b0"] >= 1


class TestTopologicalFingerprinter:
    """Tests for TopologicalFingerprinter."""

    def setup_method(self):
        self.fingerprinter = TopologicalFingerprinter()

    def test_fingerprint(self):
        """Test fingerprint creation."""
        embeddings = np.random.randn(20, 128)
        fp = self.fingerprinter.fingerprint(embeddings)

        assert fp.fingerprint_id is not None
        assert len(fp.betti_signature) == 3
        assert len(fp.persistence_signature) == 3

    def test_fingerprint_similarity_same(self):
        """Test similarity of same fingerprint."""
        embeddings = np.random.randn(20, 128)
        fp1 = self.fingerprinter.fingerprint(embeddings)
        fp2 = self.fingerprinter.fingerprint(embeddings)

        # Same embeddings should produce similar fingerprints
        sim = fp1.similarity(fp2)
        assert sim >= 0.5

    def test_fingerprint_similarity_different(self):
        """Test similarity of different fingerprints."""
        fp1 = self.fingerprinter.fingerprint(np.random.randn(20, 128))
        fp2 = self.fingerprinter.fingerprint(np.random.randn(20, 128))

        sim = fp1.similarity(fp2)
        assert 0.0 <= sim <= 1.0


class TestTDAEnhancedEngine:
    """Tests for main TDAEnhancedEngine."""

    def setup_method(self):
        self.engine = TDAEnhancedEngine()

    def test_analyze_embeddings(self):
        """Test embedding analysis."""
        embeddings = np.random.randn(30, 64)
        result = self.engine.analyze_embeddings(embeddings)

        assert "fingerprint" in result
        assert "betti" in result["fingerprint"]

    def test_analyze_layer_sequence(self):
        """Test layer sequence analysis."""
        layers = [np.random.randn(20, 64) for _ in range(4)]
        result = self.engine.analyze_layer_sequence(layers)

        assert result["num_layers"] == 4
        assert "stability_score" in result

    def test_analyze_attention(self):
        """Test attention analysis."""
        attention = np.random.rand(15, 15)
        attention = attention / attention.sum(axis=1, keepdims=True)

        result = self.engine.analyze_attention(attention)

        assert "betti_numbers" in result
        assert "entropy" in result

    def test_compute_diagram_distance(self):
        """Test diagram distance computation."""
        dgm1 = np.array([[0.0, 1.0], [0.5, 2.0]])
        dgm2 = np.array([[0.0, 1.5], [0.5, 2.5]])

        w_dist = self.engine.compute_diagram_distance(
            dgm1, dgm2, "wasserstein")
        b_dist = self.engine.compute_diagram_distance(dgm1, dgm2, "bottleneck")

        assert w_dist >= 0
        assert b_dist >= 0

    def test_fingerprint_database(self):
        """Test fingerprint storage and retrieval."""
        # Add some fingerprints
        for _ in range(5):
            embeddings = np.random.randn(20, 64)
            fp = self.engine.fingerprinter.fingerprint(embeddings)
            self.engine.add_fingerprint(fp)

        assert len(self.engine.fingerprint_db) == 5

        # Search for similar
        query = self.engine.fingerprinter.fingerprint(np.random.randn(20, 64))
        matches = self.engine.find_similar_fingerprints(query, threshold=0.3)

        # Should find some matches at low threshold
        assert isinstance(matches, list)

    def test_get_stats(self):
        """Test statistics."""
        stats = self.engine.get_stats()

        assert "fingerprints_stored" in stats
        assert "capabilities" in stats
        assert "zigzag_persistence" in stats["capabilities"]


class TestIntegration:
    """Integration tests."""

    def test_full_analysis_pipeline(self):
        """Test complete analysis pipeline."""
        engine = TDAEnhancedEngine()

        # 1. Analyze embeddings
        embeddings = np.random.randn(50, 128)
        emb_result = engine.analyze_embeddings(embeddings)

        # 2. Analyze layer sequence (simulating LLM layers)
        layers = [np.random.randn(30, 64) for _ in range(6)]
        layer_result = engine.analyze_layer_sequence(layers)

        # 3. Analyze attention
        attention = np.random.rand(25, 25)
        attention = attention / attention.sum(axis=1, keepdims=True)
        attn_result = engine.analyze_attention(attention)

        # Verify all components work together
        assert emb_result["fingerprint"]["id"] is not None
        assert layer_result["stability_score"] >= 0
        assert attn_result["entropy"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
