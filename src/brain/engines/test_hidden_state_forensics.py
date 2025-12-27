"""
Unit tests for Hidden State Forensics Engine.
"""

import pytest
import numpy as np
from hidden_state_forensics import (
    HiddenStateForensicsEngine,
    LayerAnalyzer,
    PatternDetector,
    ThreatType,
    ConfidenceLevel,
    LayerActivation
)


class TestLayerAnalyzer:
    """Tests for LayerAnalyzer."""

    def setup_method(self):
        self.analyzer = LayerAnalyzer(num_layers=32)

    def test_analyze_activations_basic(self):
        """Test basic activation analysis."""
        activations = {
            0: np.random.randn(1, 100),
            1: np.random.randn(1, 100),
            2: np.random.randn(1, 100),
        }

        stats = self.analyzer.analyze_activations(activations)

        assert len(stats) == 3
        for stat in stats:
            assert isinstance(stat, LayerActivation)
            assert stat.layer_id in [0, 1, 2]

    def test_compute_divergence(self):
        """Test divergence computation."""
        # Create baseline observations
        for _ in range(10):
            activations = {i: np.random.randn(1, 100) for i in range(5)}
            stats = self.analyzer.analyze_activations(activations)
            self.analyzer.update_baseline(stats)

        # Create anomalous observation (high values)
        anomalous_activations = {i: np.random.randn(
            1, 100) * 10 + 5 for i in range(5)}
        anomalous_stats = self.analyzer.analyze_activations(
            anomalous_activations)
        anomalous_divergences = self.analyzer.compute_divergence(
            anomalous_stats)

        # Should have some divergence values
        assert len(anomalous_divergences) > 0

    def test_identify_suspicious_layers(self):
        """Test suspicious layer identification."""
        divergences = {
            0: 1.0,
            1: 0.5,
            2: 3.0,  # Suspicious
            3: 0.8,
            4: 2.5,  # Suspicious
        }

        suspicious = self.analyzer.identify_suspicious_layers(
            divergences, threshold=2.0)

        assert 2 in suspicious
        assert 4 in suspicious
        assert len(suspicious) == 2


class TestPatternDetector:
    """Tests for PatternDetector."""

    def setup_method(self):
        self.detector = PatternDetector()

    def test_detect_normal(self):
        """Test detection of normal pattern."""
        # Low divergence across all layers
        divergences = {i: 0.5 for i in range(32)}
        layer_stats = [
            LayerActivation(i, 0.0, 1.0, 2.0, -2.0, 0.1, 5.0)
            for i in range(32)
        ]

        threat_type, confidence, reasons = self.detector.detect(
            layer_stats, divergences)

        assert threat_type == ThreatType.NORMAL

    def test_detect_jailbreak_pattern(self):
        """Test detection of jailbreak pattern."""
        # High divergence at decision layers (15-20)
        divergences = {i: 0.5 for i in range(32)}
        for layer in [15, 16, 17, 18, 19, 20]:
            divergences[layer] = 4.0  # High divergence

        layer_stats = [
            LayerActivation(i, 0.0 if i not in range(15, 21)
                            else 3.0, 1.0, 2.0, -2.0, 0.1, 5.0)
            for i in range(32)
        ]

        threat_type, confidence, reasons = self.detector.detect(
            layer_stats, divergences)

        assert threat_type == ThreatType.JAILBREAK
        assert len(reasons) > 0

    def test_generate_signature(self):
        """Test signature generation."""
        divergences = {0: 1.0, 1: 2.0, 2: 3.0}
        layer_stats = [
            LayerActivation(i, 0.0, 1.0, 2.0, -2.0, 0.1, 5.0)
            for i in range(3)
        ]

        sig1 = self.detector.generate_signature(layer_stats, divergences)
        sig2 = self.detector.generate_signature(layer_stats, divergences)

        # Same input should produce same signature
        assert sig1 == sig2
        assert len(sig1) == 16  # SHA256 truncated to 16 chars


class TestHiddenStateForensicsEngine:
    """Tests for main HSF engine."""

    def setup_method(self):
        self.engine = HiddenStateForensicsEngine()

    def test_analyze_empty_states(self):
        """Test analysis with empty hidden states."""
        result = self.engine.analyze({})

        assert result.threat_type == ThreatType.NORMAL
        assert "No hidden states provided" in result.reasons

    def test_analyze_returns_valid_result(self):
        """Test analysis returns valid result structure."""
        hidden_states = {i: np.random.randn(1, 768) for i in range(32)}
        result = self.engine.analyze(hidden_states)

        assert 0 <= result.anomaly_score <= 1.0
        assert result.threat_type in ThreatType
        assert isinstance(result.suspicious_layers, list)

    def test_analyze_anomalous_states(self):
        """Test analysis of anomalous hidden states."""
        # Build baseline with normal data
        for _ in range(20):
            hidden_states = {i: np.random.randn(1, 768) for i in range(32)}
            self.engine.analyze(hidden_states)

        # Create highly anomalous states at jailbreak layers
        anomalous_states = {i: np.random.randn(1, 768) for i in range(32)}
        for layer in [15, 16, 17, 18, 19, 20]:
            anomalous_states[layer] = np.random.randn(1, 768) * 20 + 10

        result = self.engine.analyze(anomalous_states)

        assert result.anomaly_score > 0.3
        assert len(result.suspicious_layers) > 0

    def test_result_to_dict(self):
        """Test result serialization."""
        hidden_states = {i: np.random.randn(1, 768) for i in range(5)}
        result = self.engine.analyze(hidden_states)

        result_dict = result.to_dict()

        assert "threat_type" in result_dict
        assert "confidence" in result_dict
        assert "anomaly_score" in result_dict
        assert "suspicious_layers" in result_dict
        assert "pattern_signature" in result_dict

    def test_get_stats(self):
        """Test statistics retrieval."""
        for _ in range(5):
            hidden_states = {i: np.random.randn(1, 768) for i in range(10)}
            self.engine.analyze(hidden_states)

        stats = self.engine.get_stats()

        assert stats["total_analyses"] == 5
        assert "threat_counts" in stats


class TestIntegration:
    """Integration tests."""

    def test_full_pipeline(self):
        """Test complete detection pipeline."""
        engine = HiddenStateForensicsEngine(config={"num_layers": 24})

        # Phase 1: Baseline learning
        for _ in range(50):
            states = {i: np.random.randn(1, 512) for i in range(24)}
            result = engine.analyze(states)
            assert result is not None

        # Phase 2: Simulated attack with extreme values
        attack_results = []
        for _ in range(5):
            states = {i: np.random.randn(1, 512) for i in range(24)}
            for layer in [15, 16, 17, 18]:
                states[layer] = np.ones((1, 512)) * 15
            result = engine.analyze(states)
            attack_results.append(result.anomaly_score)

        # Attack should have non-zero anomaly scores
        assert max(attack_results) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
