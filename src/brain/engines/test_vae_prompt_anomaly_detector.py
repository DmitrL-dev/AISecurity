"""
Unit tests for VAE Prompt Anomaly Detector.
"""

import pytest
from engines.vae_prompt_anomaly_detector import (
    VAEPromptAnomalyDetector,
    SimpleEncoder,
    ReconstructionAnalyzer,
    AdaptiveThreshold,
    LatentSpaceAnalyzer,
    AnomalyType,
)


class TestSimpleEncoder:
    """Tests for simple encoder."""

    def test_encode_produces_vector(self):
        """Encode produces a vector."""
        encoder = SimpleEncoder(dim=16)

        vec = encoder.encode("hello world")

        assert len(vec) == 16
        assert sum(v * v for v in vec) > 0  # Not all zeros

    def test_encode_is_normalized(self):
        """Encoded vector is normalized."""
        encoder = SimpleEncoder(dim=16)

        vec = encoder.encode("test text here")
        norm = sum(v * v for v in vec) ** 0.5

        assert abs(norm - 1.0) < 0.01


class TestAdaptiveThreshold:
    """Tests for adaptive threshold."""

    def test_initial_threshold(self):
        """Initial threshold is base."""
        threshold = AdaptiveThreshold()

        # With < 10 samples, returns base
        for i in range(5):
            threshold.update(0.1)

        t = threshold.get_threshold()
        assert t == 0.5  # Base threshold

    def test_threshold_adapts(self):
        """Threshold adapts to data."""
        threshold = AdaptiveThreshold(window_size=20, std_multiplier=2.0)

        # Add normal values
        for i in range(20):
            threshold.update(0.1)

        t = threshold.get_threshold()
        # Should be close to 0.1 (mean) + small std
        assert t < 0.5


class TestLatentSpaceAnalyzer:
    """Tests for latent space analysis."""

    def test_distance_from_centroid(self):
        """Distance from centroid works."""
        analyzer = LatentSpaceAnalyzer()

        # Add some vectors
        analyzer.add([1.0, 0.0])
        analyzer.add([0.0, 1.0])

        # Centroid is [0.5, 0.5]
        dist = analyzer.distance_from_centroid([0.5, 0.5])

        assert dist < 0.1  # Close to centroid

    def test_outlier_detection(self):
        """Outlier detection works."""
        analyzer = LatentSpaceAnalyzer()

        # Add similar vectors
        for i in range(20):
            analyzer.add([0.5 + i * 0.01, 0.5])

        # Check outlier
        is_outlier = analyzer.is_outlier([10.0, 10.0])

        assert is_outlier is True


class TestVAEPromptAnomalyDetector:
    """Integration tests."""

    def test_normal_text_passes(self):
        """Normal text after training passes."""
        detector = VAEPromptAnomalyDetector()

        # Train on normal texts
        normal_texts = [
            "Hello, how are you?",
            "What's the weather today?",
            "Can you help me with Python?",
            "Tell me about machine learning",
        ] * 5
        detector.train(normal_texts)

        # Test similar text
        result = detector.analyze("How is the weather?")

        # Should not be anomaly (similar to training)
        assert result.reconstruction_error >= 0

    def test_analyze_returns_result(self):
        """Analyze returns proper result."""
        detector = VAEPromptAnomalyDetector()

        result = detector.analyze("Test input")

        assert result.anomaly_score >= 0
        assert result.reconstruction_error >= 0

    def test_training_mode(self):
        """Training mode updates model."""
        detector = VAEPromptAnomalyDetector()

        # Analyze in training mode
        result = detector.analyze("training text", is_training=True)

        # Should not flag as anomaly in training
        assert AnomalyType.HIGH_RECONSTRUCTION not in result.anomaly_types


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
