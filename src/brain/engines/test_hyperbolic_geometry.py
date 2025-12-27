"""
Unit tests for Hyperbolic Geometry Engine.
"""

import pytest
import numpy as np
from hyperbolic_geometry import (
    HyperbolicGeometryEngine,
    PoincareBall,
    HyperbolicAggregator,
    HierarchyAnalyzer,
    EuclideanToHyperbolic,
    HyperbolicAnomalyDetector,
    HyperbolicEmbedding,
    HyperbolicModel,
)


class TestPoincareBall:
    """Tests for PoincareBall operations."""

    def setup_method(self):
        self.ball = PoincareBall(curvature=-1.0)

    def test_project_inside(self):
        """Test projection of point inside ball."""
        x = np.array([0.3, 0.4])
        result = self.ball.project(x)
        np.testing.assert_array_almost_equal(x, result)

    def test_project_outside(self):
        """Test projection of point outside ball."""
        x = np.array([1.5, 0.0])
        result = self.ball.project(x)
        assert np.linalg.norm(result) < 1.0

    def test_mobius_add_origin(self):
        """Test Möbius addition with origin."""
        x = np.array([0.0, 0.0])
        y = np.array([0.3, 0.4])
        result = self.ball.mobius_add(x, y)
        np.testing.assert_array_almost_equal(result, y)

    def test_mobius_add_inverse(self):
        """Test x ⊕ (-x) ≈ 0."""
        x = np.array([0.3, 0.2])
        neg_x = -x
        result = self.ball.mobius_add(x, neg_x)
        assert np.linalg.norm(result) < 0.1

    def test_distance_symmetric(self):
        """Test distance symmetry."""
        x = np.array([0.2, 0.3])
        y = np.array([0.4, -0.1])
        d1 = self.ball.distance(x, y)
        d2 = self.ball.distance(y, x)
        assert abs(d1 - d2) < 1e-6

    def test_distance_to_self(self):
        """Test distance to self is zero."""
        x = np.array([0.3, 0.4])
        d = self.ball.distance(x, x)
        assert abs(d) < 1e-6

    def test_distance_increases_near_boundary(self):
        """Test distances are larger near boundary."""
        origin = np.array([0.0, 0.0])
        near_center = np.array([0.1, 0.0])
        near_boundary = np.array([0.9, 0.0])

        d1 = self.ball.distance(origin, near_center)
        d2 = self.ball.distance(origin, near_boundary)

        assert d2 > d1

    def test_exp_log_inverse(self):
        """Test exp and log are inverses."""
        x = np.array([0.2, 0.3])
        v = np.array([0.1, 0.05])

        y = self.ball.exp_map(x, v)
        v_recovered = self.ball.log_map(x, y)

        np.testing.assert_array_almost_equal(v, v_recovered, decimal=3)


class TestHyperbolicAggregator:
    """Tests for HyperbolicAggregator."""

    def setup_method(self):
        self.ball = PoincareBall()
        self.aggregator = HyperbolicAggregator(self.ball)

    def test_frechet_mean_single_point(self):
        """Test Fréchet mean of single point."""
        points = np.array([[0.3, 0.4]])
        mean = self.aggregator.frechet_mean(points)
        np.testing.assert_array_almost_equal(mean, points[0])

    def test_frechet_mean_symmetric(self):
        """Test Fréchet mean of symmetric points."""
        points = np.array([
            [0.3, 0.0],
            [-0.3, 0.0]
        ])
        mean = self.aggregator.frechet_mean(points)
        # Mean should be near origin
        assert np.linalg.norm(mean) < 0.2

    def test_variance(self):
        """Test variance computation."""
        points = np.array([
            [0.1, 0.0],
            [0.2, 0.0],
            [0.3, 0.0]
        ])
        var = self.aggregator.variance(points)
        assert var > 0


class TestHierarchyAnalyzer:
    """Tests for HierarchyAnalyzer."""

    def setup_method(self):
        self.ball = PoincareBall()
        self.analyzer = HierarchyAnalyzer(self.ball)

    def test_estimate_depth(self):
        """Test depth estimation."""
        points = np.array([
            [0.1, 0.0],  # Near center = shallow
            [0.5, 0.0],  # Middle
            [0.9, 0.0]   # Near boundary = deep
        ])
        embedding = HyperbolicEmbedding(points=points)

        depths = self.analyzer.estimate_depth(embedding)

        # Depths should increase with norm
        assert depths[0] < depths[1] < depths[2]

    def test_find_root(self):
        """Test root finding."""
        points = np.array([
            [0.5, 0.0],
            [0.1, 0.1],  # Closest to center
            [0.7, 0.3]
        ])
        embedding = HyperbolicEmbedding(points=points)

        root = self.analyzer.find_root(embedding)
        assert root == 1

    def test_find_leaves(self):
        """Test leaf finding."""
        points = np.array([
            [0.1, 0.0],
            [0.5, 0.0],
            [0.85, 0.0],
            [0.9, 0.0]
        ])
        embedding = HyperbolicEmbedding(points=points)

        leaves = self.analyzer.find_leaves(embedding, threshold=0.8)
        assert len(leaves) == 2


class TestEuclideanToHyperbolic:
    """Tests for EuclideanToHyperbolic."""

    def setup_method(self):
        self.ball = PoincareBall()
        self.projector = EuclideanToHyperbolic(self.ball)

    def test_project_simple(self):
        """Test simple projection."""
        euclidean = np.random.randn(10, 5)
        hyp = self.projector.project_simple(euclidean)

        # All points should be inside ball
        assert all(np.linalg.norm(p) < 1.0 for p in hyp.points)

    def test_project_exponential(self):
        """Test exponential projection."""
        euclidean = np.random.randn(10, 5)
        hyp = self.projector.project_exponential(euclidean)

        # All points should be inside ball
        assert all(np.linalg.norm(p) < 1.0 for p in hyp.points)


class TestHyperbolicAnomalyDetector:
    """Tests for HyperbolicAnomalyDetector."""

    def setup_method(self):
        self.ball = PoincareBall()
        self.detector = HyperbolicAnomalyDetector(self.ball)

    def test_detect_normal(self):
        """Test detection on normal embedding."""
        # Spread across ball
        points = np.array([
            [0.1, 0.0],
            [0.3, 0.2],
            [0.5, -0.1],
            [0.7, 0.3]
        ])
        embedding = HyperbolicEmbedding(points=points)

        anomaly = self.detector.detect(embedding)
        # Should not be highly anomalous
        assert anomaly.anomaly_score < 0.5

    def test_detect_boundary_clustering(self):
        """Test detection of boundary clustering."""
        # All points near boundary
        points = np.array([
            [0.96, 0.0],
            [0.97, 0.1],
            [0.95, -0.1],
            [0.98, 0.05]
        ])
        embedding = HyperbolicEmbedding(points=points)

        anomaly = self.detector.detect(embedding)
        # Should detect anomaly
        assert anomaly.is_anomalous


class TestHyperbolicGeometryEngine:
    """Tests for main HyperbolicGeometryEngine."""

    def setup_method(self):
        self.engine = HyperbolicGeometryEngine()

    def test_project_embeddings(self):
        """Test embedding projection."""
        euclidean = np.random.randn(20, 10)
        hyp = self.engine.project_embeddings(euclidean)

        assert hyp.num_points == 20
        assert hyp.dimension == 10

    def test_compute_distance(self):
        """Test distance computation."""
        p1 = np.array([0.2, 0.3])
        p2 = np.array([0.5, -0.1])

        dist = self.engine.compute_distance(p1, p2)
        assert dist > 0

    def test_compute_centroid(self):
        """Test centroid computation."""
        points = np.random.randn(15, 5) * 0.3
        embedding = HyperbolicEmbedding(
            points=self.engine.ball.project(points[0]).reshape(1, -1)
        )

        # Project all points
        projected = np.array([self.engine.ball.project(p) for p in points])
        embedding = HyperbolicEmbedding(points=projected)

        centroid = self.engine.compute_centroid(embedding)
        assert len(centroid) == 5

    def test_analyze_hierarchy(self):
        """Test hierarchy analysis."""
        euclidean = np.random.randn(25, 8)
        hyp = self.engine.project_embeddings(euclidean)

        result = self.engine.analyze_hierarchy(hyp)

        assert "root_index" in result
        assert "num_leaves" in result
        assert "distortion" in result

    def test_analyze_embeddings(self):
        """Test full embedding analysis."""
        euclidean = np.random.randn(30, 12)
        result = self.engine.analyze_embeddings(euclidean)

        assert "metrics" in result
        assert "hierarchy" in result
        assert "anomaly" in result

    def test_compare_distributions(self):
        """Test distribution comparison."""
        emb1 = np.random.randn(20, 8)
        emb2 = np.random.randn(20, 8) + 2

        result = self.engine.compare_distributions(emb1, emb2)

        assert "centroid_distance" in result
        assert result["centroid_distance"] > 0

    def test_stats(self):
        """Test statistics."""
        self.engine.analyze_embeddings(np.random.randn(10, 5))
        stats = self.engine.get_stats()

        assert stats["analyses_performed"] >= 1
        assert "capabilities" in stats


class TestIntegration:
    """Integration tests."""

    def test_full_pipeline(self):
        """Test complete analysis pipeline."""
        engine = HyperbolicGeometryEngine()

        # Create hierarchical-like data
        levels = []
        for depth in [0.1, 0.3, 0.5, 0.7, 0.9]:
            n_points = int(5 * (1 + depth))
            level_points = np.random.randn(n_points, 10) * depth
            levels.append(level_points)

        all_points = np.vstack(levels)

        # Analyze
        result = engine.analyze_embeddings(all_points)

        assert result["num_points"] == len(all_points)
        assert result["hierarchy"]["mean_depth"] > 0

    def test_anomaly_detection_pipeline(self):
        """Test anomaly detection on different embeddings."""
        engine = HyperbolicGeometryEngine()

        # Normal hierarchical data
        normal = np.random.randn(30, 8)
        normal_result = engine.analyze_embeddings(normal)

        # Flat data (everything near center)
        flat = np.random.randn(30, 8) * 0.01
        flat_result = engine.analyze_embeddings(flat)

        # Both should complete
        assert "anomaly" in normal_result
        assert "anomaly" in flat_result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
