"""
Unit tests for Semantic Drift Detector.
"""

import pytest
from engines.semantic_drift_detector import (
    SemanticDriftDetector,
    EmbeddingAnalyzer,
    BaselineManager,
    DriftClassifier,
    EmbeddingPoint,
    DriftType,
)


class TestEmbeddingAnalyzer:
    """Tests for embedding analysis."""

    def test_cosine_similarity_identical(self):
        """Identical vectors have similarity 1."""
        v = [1.0, 2.0, 3.0]

        sim = EmbeddingAnalyzer.cosine_similarity(v, v)

        assert abs(sim - 1.0) < 0.001

    def test_cosine_similarity_orthogonal(self):
        """Orthogonal vectors have similarity 0."""
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]

        sim = EmbeddingAnalyzer.cosine_similarity(v1, v2)

        assert abs(sim) < 0.001

    def test_euclidean_distance(self):
        """Euclidean distance is computed correctly."""
        v1 = [0.0, 0.0]
        v2 = [3.0, 4.0]

        dist = EmbeddingAnalyzer.euclidean_distance(v1, v2)

        assert abs(dist - 5.0) < 0.001


class TestBaselineManager:
    """Tests for baseline management."""

    def test_set_and_get_baseline(self):
        """Baseline can be set and retrieved."""
        manager = BaselineManager()
        point = EmbeddingPoint([1.0, 2.0], "test")

        manager.set_baseline("key1", point)
        retrieved = manager.get_baseline("key1")

        assert retrieved is not None
        assert retrieved.vector == [1.0, 2.0]

    def test_history_tracking(self):
        """History is tracked."""
        manager = BaselineManager(window_size=5)

        for i in range(3):
            point = EmbeddingPoint([float(i)], f"text{i}")
            manager.add_to_history("key1", point)

        history = manager.get_history("key1")

        assert len(history) == 3


class TestDriftClassifier:
    """Tests for drift classification."""

    def test_no_drift_when_similar(self):
        """No drift when embeddings are similar."""
        classifier = DriftClassifier(intent_threshold=0.3)

        base = EmbeddingPoint([1.0, 0.0], "hello")
        current = EmbeddingPoint([0.99, 0.1], "hello")

        # High similarity = low distance = no drift
        is_drift, drift_type, severity = classifier.classify(
            base, current, 0.98)

        assert is_drift is False

    def test_intent_shift_detected(self):
        """Intent shift is detected."""
        classifier = DriftClassifier(intent_threshold=0.3)

        base = EmbeddingPoint([1.0, 0.0], "hello")
        current = EmbeddingPoint([0.0, 1.0], "goodbye")

        is_drift, drift_type, severity = classifier.classify(
            base, current, 0.5)

        assert is_drift is True
        assert drift_type == DriftType.INTENT_SHIFT


class TestSemanticDriftDetector:
    """Integration tests."""

    def test_no_baseline_is_safe(self):
        """No baseline means safe."""
        detector = SemanticDriftDetector()

        result = detector.detect("key1", [1.0, 2.0])

        assert result.is_safe is True
        assert result.drift_detected is False

    def test_similar_embedding_is_safe(self):
        """Similar embedding is safe."""
        detector = SemanticDriftDetector(drift_threshold=0.3)

        baseline = [1.0, 0.0, 0.0]
        detector.set_baseline("key1", baseline, "original text")

        # Very similar embedding
        current = [0.99, 0.1, 0.0]
        result = detector.detect("key1", current)

        assert result.is_safe is True

    def test_different_embedding_triggers_drift(self):
        """Different embedding triggers drift."""
        detector = SemanticDriftDetector(drift_threshold=0.3)

        baseline = [1.0, 0.0, 0.0]
        detector.set_baseline("key1", baseline, "original")

        # Very different embedding
        current = [0.0, 1.0, 0.0]
        result = detector.detect("key1", current)

        assert result.drift_detected is True
        assert result.is_safe is False

    def test_trajectory_drift(self):
        """Trajectory drift is detected."""
        detector = SemanticDriftDetector(drift_threshold=0.25)

        # Gradually drifting trajectory
        trajectory = [
            [1.0, 0.0],
            [0.5, 0.5],
            [0.0, 1.0],  # Big drift here
        ]

        result = detector.detect_trajectory_drift("key1", trajectory)

        assert result.drift_detected is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
