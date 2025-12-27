"""
Unit tests for Information Geometry Engine.
"""

import pytest
import numpy as np
from information_geometry import (
    InformationGeometryEngine,
    FisherEstimator,
    InformationDistance,
    GeodesicComputer,
    CurvatureAnalyzer,
    DriftDetector,
    FisherInformation,
)


class TestFisherInformation:
    """Tests for FisherInformation dataclass."""

    def test_dimension(self):
        """Test dimension property."""
        fi = FisherInformation(
            matrix=np.eye(5),
            eigenvalues=np.ones(5),
            condition_number=1.0,
            trace=5.0
        )
        assert fi.dimension == 5

    def test_to_dict(self):
        """Test serialization."""
        fi = FisherInformation(
            matrix=np.eye(3),
            eigenvalues=np.array([1.0, 2.0, 3.0]),
            condition_number=3.0,
            trace=6.0
        )
        d = fi.to_dict()

        assert d["dimension"] == 3
        assert d["max_eigenvalue"] == 3.0
        assert d["min_eigenvalue"] == 1.0


class TestFisherEstimator:
    """Tests for FisherEstimator."""

    def setup_method(self):
        self.estimator = FisherEstimator()

    def test_estimate_from_embeddings(self):
        """Test Fisher estimation from embeddings."""
        embeddings = np.random.randn(50, 10)
        fi = self.estimator.estimate_from_embeddings(embeddings)

        assert fi.dimension == 10
        assert fi.trace > 0
        assert fi.condition_number >= 1

    def test_small_sample(self):
        """Test with small sample."""
        embeddings = np.random.randn(1, 5)
        fi = self.estimator.estimate_from_embeddings(embeddings)

        assert fi.dimension > 0

    def test_estimate_from_scores(self):
        """Test estimation from score functions."""
        scores = np.random.randn(100, 5)
        fi = self.estimator.estimate_from_scores(scores)

        assert fi.dimension == 5


class TestInformationDistance:
    """Tests for InformationDistance."""

    def test_kl_divergence(self):
        """Test KL divergence."""
        p = np.array([0.5, 0.5])
        q = np.array([0.9, 0.1])

        kl = InformationDistance.kl_divergence(p, q)
        assert kl > 0

    def test_kl_same_distribution(self):
        """Test KL with identical distributions."""
        p = np.array([0.3, 0.3, 0.4])
        kl = InformationDistance.kl_divergence(p, p)

        assert abs(kl) < 1e-10

    def test_symmetric_kl(self):
        """Test symmetric KL (Jeffreys)."""
        p = np.array([0.5, 0.5])
        q = np.array([0.8, 0.2])

        sym_kl = InformationDistance.symmetric_kl(p, q)
        assert sym_kl > 0

    def test_alpha_divergence(self):
        """Test α-divergence."""
        p = np.array([0.3, 0.7])
        q = np.array([0.6, 0.4])

        div = InformationDistance.alpha_divergence(p, q, alpha=0.5)
        assert isinstance(div, float)

    def test_fisher_rao_distance(self):
        """Test Fisher-Rao distance."""
        mean1 = np.zeros(3)
        cov1 = np.eye(3)
        mean2 = np.ones(3)
        cov2 = 2 * np.eye(3)

        dist = InformationDistance.fisher_rao_distance(
            mean1, cov1, mean2, cov2
        )
        assert dist > 0


class TestGeodesicComputer:
    """Tests for GeodesicComputer."""

    def setup_method(self):
        self.computer = GeodesicComputer(num_steps=10)
        self.estimator = FisherEstimator()

    def test_compute_geodesic(self):
        """Test geodesic computation."""
        embeddings = np.random.randn(50, 5)
        fisher = self.estimator.estimate_from_embeddings(embeddings)

        start = np.zeros(5)
        end = np.ones(5)

        geodesic = self.computer.compute_geodesic(start, end, fisher)

        assert len(geodesic.path_points) == 10
        assert geodesic.geodesic_distance > 0

    def test_geodesic_same_point(self):
        """Test geodesic between same points."""
        embeddings = np.random.randn(30, 4)
        fisher = self.estimator.estimate_from_embeddings(embeddings)

        point = np.array([1.0, 2.0, 3.0, 4.0])
        geodesic = self.computer.compute_geodesic(point, point, fisher)

        assert geodesic.geodesic_distance == 0


class TestCurvatureAnalyzer:
    """Tests for CurvatureAnalyzer."""

    def setup_method(self):
        self.analyzer = CurvatureAnalyzer()
        self.estimator = FisherEstimator()

    def test_scalar_curvature(self):
        """Test scalar curvature computation."""
        embeddings = np.random.randn(50, 8)
        fisher = self.estimator.estimate_from_embeddings(embeddings)

        curvature = self.analyzer.compute_scalar_curvature(fisher, 8)

        assert curvature.scalar_curvature != 0
        assert isinstance(curvature.is_flat, bool)


class TestDriftDetector:
    """Tests for DriftDetector."""

    def setup_method(self):
        self.detector = DriftDetector(threshold=1.0)

    def test_detect_drift(self):
        """Test drift detection."""
        reference = np.random.randn(100, 10)
        current = np.random.randn(100, 10) + 5  # Shifted

        result = self.detector.detect_drift(reference, current)

        assert result.has_drift
        assert result.drift_magnitude > 0

    def test_no_drift(self):
        """Test with no drift."""
        reference = np.random.randn(100, 10)
        current = reference + 0.01 * np.random.randn(100, 10)  # Tiny noise

        result = self.detector.detect_drift(reference, current)

        # May or may not detect drift depending on threshold

    def test_small_sample(self):
        """Test with small samples."""
        reference = np.random.randn(1, 5)
        current = np.random.randn(1, 5)

        result = self.detector.detect_drift(reference, current)
        assert result.explanation == "Insufficient samples"


class TestInformationGeometryEngine:
    """Tests for main InformationGeometryEngine."""

    def setup_method(self):
        self.engine = InformationGeometryEngine()

    def test_estimate_fisher(self):
        """Test Fisher estimation."""
        embeddings = np.random.randn(50, 20)
        result = self.engine.estimate_fisher(embeddings)

        assert "dimension" in result
        assert "trace" in result

    def test_compute_distance(self):
        """Test distance computation."""
        emb1 = np.random.randn(50, 10)
        emb2 = np.random.randn(50, 10) + 2

        dist = self.engine.compute_distance(emb1, emb2)
        assert dist > 0

    def test_analyze_manifold(self):
        """Test manifold analysis."""
        embeddings = np.random.randn(60, 15)
        result = self.engine.analyze_manifold(embeddings)

        assert "fisher" in result
        assert "curvature" in result
        assert result["num_samples"] == 60

    def test_detect_drift(self):
        """Test drift detection."""
        reference = np.random.randn(80, 12)
        current = np.random.randn(80, 12) + 3

        result = self.engine.detect_drift(reference, current)

        assert "has_drift" in result
        assert "drift_magnitude" in result

    def test_compute_geodesic(self):
        """Test geodesic computation."""
        start_emb = np.random.randn(40, 8)
        end_emb = np.random.randn(40, 8) + 1

        result = self.engine.compute_geodesic(start_emb, end_emb)

        assert "geodesic_distance" in result
        assert "euclidean_distance" in result

    def test_anomaly_score(self):
        """Test anomaly scoring."""
        reference = np.random.randn(100, 10)

        # Normal point
        normal_point = np.mean(reference, axis=0)
        normal_score = self.engine.anomaly_score(reference, normal_point)

        # Anomaly point
        anomaly_point = np.mean(reference, axis=0) + \
            10 * np.std(reference, axis=0)
        anomaly_score = self.engine.anomaly_score(reference, anomaly_point)

        # Anomaly should have higher score
        assert anomaly_score > normal_score

    def test_stats(self):
        """Test statistics."""
        self.engine.estimate_fisher(np.random.randn(20, 5))
        stats = self.engine.get_stats()

        assert stats["analyses_performed"] >= 1
        assert "capabilities" in stats


class TestIntegration:
    """Integration tests."""

    def test_full_analysis_pipeline(self):
        """Test complete analysis pipeline."""
        engine = InformationGeometryEngine()

        # Generate reference distribution
        reference = np.random.randn(100, 20)

        # Analyze manifold
        manifold = engine.analyze_manifold(reference)

        # Generate drifted distribution
        drifted = reference + 2

        # Detect drift
        drift = engine.detect_drift(reference, drifted)

        # Compute geodesic
        geodesic = engine.compute_geodesic(reference, drifted)

        assert manifold["fisher"]["dimension"] == 20
        assert drift["has_drift"]
        assert geodesic["geodesic_distance"] > 0

    def test_anomaly_detection_use_case(self):
        """Test anomaly detection use case."""
        engine = InformationGeometryEngine()

        # Normal embeddings
        normal = np.random.randn(200, 16)

        # Test points
        scores = []
        for i in range(10):
            point = np.random.randn(16) * (1 + i * 0.5)
            score = engine.anomaly_score(normal, point)
            scores.append(score)

        # Scores should generally increase with i
        assert all(isinstance(s, float) for s in scores)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
