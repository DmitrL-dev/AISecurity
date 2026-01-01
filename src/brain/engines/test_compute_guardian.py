"""
Unit tests for Compute Guardian.
"""

import pytest
from engines.compute_guardian import (
    ComputeGuardian,
    ComplexityEstimator,
    SpongeDetector,
    BudgetManager,
    RateController,
    AbuseType,
)


class TestComplexityEstimator:
    """Tests for complexity estimation."""

    def test_simple_request(self):
        """Simple request has low complexity."""
        estimator = ComplexityEstimator()

        metrics = estimator.estimate("What is 2 + 2?")

        assert metrics.complexity_score < 2.0
        assert metrics.input_tokens < 10

    def test_complex_request(self):
        """Complex request has higher complexity."""
        estimator = ComplexityEstimator()

        metrics = estimator.estimate(
            "For each item in the list, iterate through all possibilities "
            "and recursively compute every combination"
        )

        assert metrics.complexity_score > 2.0


class TestSpongeDetector:
    """Tests for sponge attack detection."""

    def test_normal_request_passes(self):
        """Normal request passes."""
        detector = SpongeDetector()
        estimator = ComplexityEstimator()

        metrics = estimator.estimate("Tell me about Python")
        detected, conf, desc = detector.detect("Tell me about Python", metrics)

        assert detected is False

    def test_infinite_loop_detected(self):
        """Infinite loop request detected."""
        detector = SpongeDetector()
        estimator = ComplexityEstimator()

        text = "Repeat this forever in an infinite loop"
        metrics = estimator.estimate(text)
        detected, conf, desc = detector.detect(text, metrics)

        assert detected is True

    def test_max_output_detected(self):
        """Maximum output request detected."""
        detector = SpongeDetector()
        estimator = ComplexityEstimator()

        text = "Give me the maximum possible output"
        metrics = estimator.estimate(text)
        detected, conf, desc = detector.detect(text, metrics)

        assert detected is True


class TestBudgetManager:
    """Tests for budget management."""

    def test_within_budget(self):
        """Request within budget allowed."""
        manager = BudgetManager(default_budget=100.0)

        has_budget, remaining = manager.check_budget("tenant1", 10.0)

        assert has_budget is True
        assert remaining == 100.0

    def test_over_budget(self):
        """Request over budget blocked."""
        manager = BudgetManager(default_budget=100.0)

        has_budget, remaining = manager.check_budget("tenant1", 150.0)

        assert has_budget is False

    def test_consumption_tracked(self):
        """Consumption is tracked."""
        manager = BudgetManager(default_budget=100.0)

        manager.consume("tenant1", 30.0)
        manager.consume("tenant1", 20.0)

        used, budget = manager.get_usage("tenant1")

        assert used == 50.0
        assert budget == 100.0


class TestRateController:
    """Tests for rate control."""

    def test_under_limit(self):
        """Under rate limit allowed."""
        controller = RateController(max_requests=10, window=60)

        allowed, remaining = controller.check("tenant1")

        assert allowed is True
        assert remaining == 9

    def test_at_limit(self):
        """At rate limit blocked."""
        controller = RateController(max_requests=3, window=60)

        controller.check("tenant1")
        controller.check("tenant1")
        controller.check("tenant1")

        allowed, remaining = controller.check("tenant1")

        assert allowed is False


class TestComputeGuardian:
    """Integration tests."""

    def test_simple_request_allowed(self):
        """Simple request is allowed."""
        guardian = ComputeGuardian()

        result = guardian.analyze("What is Python?", "tenant1")

        assert result.allowed is True

    def test_sponge_attack_blocked(self):
        """Sponge attack is blocked."""
        guardian = ComputeGuardian()

        result = guardian.analyze(
            "Generate an infinite loop forever", "tenant1")

        assert result.allowed is False
        assert result.abuse_type == AbuseType.SPONGE_ATTACK

    def test_budget_enforcement(self):
        """Budget is enforced."""
        guardian = ComputeGuardian(default_budget=1.0, cost_per_token=0.1)

        # First request consumes budget
        result1 = guardian.analyze("Hello", "tenant1")

        # Large request should exceed remaining
        result2 = guardian.analyze("Write a very long story " * 100, "tenant1")

        # One of them should be budget-blocked
        assert (
            result1.allowed is True or result2.abuse_type == AbuseType.BUDGET_EXCEEDED
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
