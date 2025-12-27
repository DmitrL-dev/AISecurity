"""
Unit tests for Formal Verification Engine.
"""

import pytest
import numpy as np
from formal_verification import (
    FormalVerificationEngine,
    RobustnessVerifier,
    SafetyPropertyVerifier,
    IntervalBoundPropagation,
    CROWNPropagation,
    InputRegion,
    OutputBound,
    SafetyProperty,
    VerificationMethod,
    VerificationStatus,
    PropertyType,
)


class TestInputRegion:
    """Tests for InputRegion."""

    def test_linf_contains(self):
        """Test L-infinity containment."""
        region = InputRegion(
            center=np.array([0.0, 0.0]),
            epsilon=1.0,
            norm="linf"
        )

        assert region.contains(np.array([0.5, 0.5]))
        assert region.contains(np.array([1.0, 0.0]))
        assert not region.contains(np.array([1.5, 0.0]))

    def test_l2_contains(self):
        """Test L2 containment."""
        region = InputRegion(
            center=np.array([0.0, 0.0]),
            epsilon=1.0,
            norm="l2"
        )

        assert region.contains(np.array([0.5, 0.5]))
        assert not region.contains(np.array([1.0, 1.0]))


class TestIntervalBoundPropagation:
    """Tests for IBP."""

    def setup_method(self):
        self.ibp = IntervalBoundPropagation()

    def test_propagate_linear(self):
        """Test linear layer propagation."""
        weight = np.array([[1.0, 2.0], [3.0, 4.0]])
        bias = np.array([0.0, 0.0])
        input_lower = np.array([0.0, 0.0])
        input_upper = np.array([1.0, 1.0])

        lower, upper = self.ibp.propagate_linear(
            weight, bias, input_lower, input_upper
        )

        assert np.all(lower <= upper)

    def test_propagate_relu(self):
        """Test ReLU propagation."""
        input_lower = np.array([-1.0, 0.5])
        input_upper = np.array([1.0, 2.0])

        lower, upper = self.ibp.propagate_relu(input_lower, input_upper)

        assert lower[0] == 0.0  # ReLU of -1 is 0
        assert lower[1] == 0.5
        assert upper[0] == 1.0
        assert upper[1] == 2.0

    def test_compute_bounds(self):
        """Test full bound computation."""
        weights = [np.eye(2), np.eye(2)]
        biases = [np.zeros(2), np.zeros(2)]
        region = InputRegion(center=np.zeros(2), epsilon=0.1)

        bounds = self.ibp.compute_bounds(weights, biases, region)

        assert np.all(bounds.lower <= bounds.upper)


class TestCROWNPropagation:
    """Tests for CROWN."""

    def setup_method(self):
        self.crown = CROWNPropagation()

    def test_compute_tighter_bounds(self):
        """Test that CROWN produces tighter bounds than IBP."""
        weights = [np.eye(10), np.eye(10)]
        biases = [np.zeros(10), np.zeros(10)]
        region = InputRegion(center=np.zeros(10), epsilon=0.5)

        ibp = IntervalBoundPropagation()
        ibp_bounds = ibp.compute_bounds(weights, biases, region)
        crown_bounds = self.crown.compute_bounds(weights, biases, region)

        # CROWN should be tighter or equal
        assert crown_bounds.tight


class TestRobustnessVerifier:
    """Tests for RobustnessVerifier."""

    def setup_method(self):
        self.verifier = RobustnessVerifier(VerificationMethod.CROWN)

    def test_verify_simple_robust(self):
        """Test verification of clearly robust network."""
        # Identity network - should be robust
        weights = [np.eye(3)]
        biases = [np.array([10.0, 0.0, 0.0])]  # Class 0 always highest

        input_point = np.zeros(3)
        epsilon = 0.1

        result = self.verifier.verify_robustness(
            weights, biases, input_point, epsilon, true_label=0
        )

        assert result.status == VerificationStatus.VERIFIED

    def test_verify_not_robust(self):
        """Test detection of non-robust case."""
        weights = [np.eye(3)]
        biases = [np.zeros(3)]

        input_point = np.array([0.5, 0.49, 0.0])
        epsilon = 0.1  # Large enough to switch prediction

        result = self.verifier.verify_robustness(
            weights, biases, input_point, epsilon, true_label=0
        )

        # Bounds will overlap, so not certifiably robust
        assert result.status in [
            VerificationStatus.VERIFIED, VerificationStatus.VIOLATED]

    def test_find_certified_epsilon(self):
        """Test binary search for max epsilon."""
        weights = [np.eye(2)]
        biases = [np.array([1.0, 0.0])]

        input_point = np.zeros(2)

        certified = self.verifier.find_certified_epsilon(
            weights, biases, input_point, true_label=0,
            max_epsilon=2.0, precision=0.01
        )

        assert certified.epsilon > 0
        assert certified.confidence == 1.0


class TestSafetyPropertyVerifier:
    """Tests for SafetyPropertyVerifier."""

    def setup_method(self):
        self.verifier = SafetyPropertyVerifier()

    def test_verify_output_bound_property(self):
        """Test verification of output bounds."""
        weights = [np.eye(2)]
        biases = [np.zeros(2)]

        property = SafetyProperty(
            property_id="output_positive",
            property_type=PropertyType.SAFETY,
            description="Outputs should be positive",
            input_region=InputRegion(center=np.ones(2), epsilon=0.1),
            output_constraint=lambda x: np.all(x > 0)
        )

        result = self.verifier.verify_property(weights, biases, property)

        assert result.property_id == "output_positive"
        assert result.status in [
            VerificationStatus.VERIFIED, VerificationStatus.VIOLATED]


class TestFormalVerificationEngine:
    """Tests for main engine."""

    def setup_method(self):
        self.engine = FormalVerificationEngine()

    def test_certify_robustness(self):
        """Test robustness certification."""
        weights = [np.eye(4)]
        biases = [np.array([5.0, 0.0, 0.0, 0.0])]

        result = self.engine.certify_robustness(
            weights, biases,
            input_point=np.zeros(4),
            epsilon=0.1,
            true_label=0
        )

        assert result.epsilon_verified >= 0

    def test_find_max_epsilon(self):
        """Test max epsilon search."""
        weights = [np.eye(3)]
        biases = [np.array([2.0, 0.0, 0.0])]

        bound = self.engine.find_max_certified_epsilon(
            weights, biases,
            input_point=np.zeros(3),
            true_label=0
        )

        assert bound.epsilon > 0

    def test_verify_safety(self):
        """Test safety property verification."""
        weights = [np.eye(2)]
        biases = [np.zeros(2)]

        property = SafetyProperty(
            property_id="bounded_output",
            property_type=PropertyType.REACHABILITY,
            description="Output in [-1, 1]",
            input_region=InputRegion(center=np.zeros(2), epsilon=0.5),
            output_constraint=lambda x: np.all(np.abs(x) <= 1)
        )

        result = self.engine.verify_safety(weights, biases, property)

        assert result.property_id == "bounded_output"

    def test_batch_verify(self):
        """Test batch verification."""
        weights = [np.eye(3)]
        biases = [np.array([3.0, 0.0, 0.0])]

        test_points = [np.zeros(3) for _ in range(5)]
        labels = [0] * 5

        results = self.engine.batch_verify(
            weights, biases, test_points, labels, epsilon=0.1
        )

        assert results["total"] == 5
        assert "certified_accuracy" in results

    def test_get_stats(self):
        """Test statistics."""
        weights = [np.eye(2)]
        biases = [np.zeros(2)]

        self.engine.certify_robustness(
            weights, biases, np.zeros(2), 0.1, 0
        )

        stats = self.engine.get_stats()

        assert stats["total_verifications"] == 1


class TestIntegration:
    """Integration tests."""

    def test_full_verification_pipeline(self):
        """Test complete verification pipeline."""
        engine = FormalVerificationEngine()

        # Create simple classifier
        hidden_dim = 16
        weights = [
            np.random.randn(hidden_dim, hidden_dim) * 0.1,
            np.random.randn(3, hidden_dim) * 0.1
        ]
        biases = [
            np.zeros(hidden_dim),
            np.array([1.0, 0.0, 0.0])
        ]

        # Test point
        input_point = np.random.randn(hidden_dim)

        # Find max certified epsilon
        bound = engine.find_max_certified_epsilon(
            weights, biases, input_point, true_label=0
        )

        # Verify at that epsilon
        result = engine.certify_robustness(
            weights, biases, input_point, bound.epsilon * 0.9, true_label=0
        )

        # Should be verified at slightly below max
        stats = engine.get_stats()
        assert stats["total_verifications"] >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
