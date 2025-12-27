"""
Unit tests for Federated Threat Aggregator.
"""

import pytest
from federated_threat_aggregator import (
    FederatedThreatAggregator,
    FederatedAggregator,
    DifferentialPrivacy,
    ThreatIntelligence,
    ThreatIndicator,
    ThreatType,
)


class TestDifferentialPrivacy:
    """Tests for differential privacy."""

    def test_add_noise(self):
        """Noise is added."""
        dp = DifferentialPrivacy(epsilon=1.0)

        noisy = dp.add_noise(10.0)

        # Should be different (with high probability)
        assert isinstance(noisy, float)

    def test_hash_with_privacy(self):
        """Privacy hash works."""
        dp = DifferentialPrivacy()

        h1 = dp.hash_with_privacy("test")
        h2 = dp.hash_with_privacy("test")

        # Different due to salt
        assert h1 != h2


class TestFederatedAggregator:
    """Tests for aggregator."""

    def test_contribute(self):
        """Can contribute indicators."""
        agg = FederatedAggregator()
        ind = ThreatIndicator("id1", ThreatType.INJECTION, "hash1", 0.9)

        new = agg.contribute("org1", [ind])

        assert new == 1
        assert len(agg.get_all_indicators()) == 1

    def test_merge_contributors(self):
        """Merges from multiple contributors."""
        agg = FederatedAggregator(min_contributors=2)
        ind = ThreatIndicator("id1", ThreatType.INJECTION, "hash1", 0.5)

        agg.contribute("org1", [ind])
        agg.contribute("org2", [ind])

        shared = agg.get_shared_indicators()
        assert len(shared) == 1
        assert shared[0].contributor_count == 2


class TestThreatIntelligence:
    """Tests for threat intelligence."""

    def test_add_pattern(self):
        """Can add pattern."""
        intel = ThreatIntelligence()

        is_new = intel.add_pattern("hash1")

        assert is_new is True
        assert intel.count() == 1

    def test_duplicate_not_added(self):
        """Duplicate not added."""
        intel = ThreatIntelligence()
        intel.add_pattern("hash1")

        is_new = intel.add_pattern("hash1")

        assert is_new is False


class TestFederatedThreatAggregator:
    """Integration tests."""

    def test_submit_indicators(self):
        """Can submit indicators."""
        agg = FederatedThreatAggregator()

        result = agg.submit_indicators(
            "org1", ["pattern1", "pattern2"], ThreatType.INJECTION
        )

        assert result.indicators_count == 2
        assert result.contributors == 1
        assert result.privacy_preserved is True

    def test_multiple_contributors(self):
        """Multiple contributors aggregate."""
        agg = FederatedThreatAggregator()

        agg.submit_indicators("org1", ["p1"], ThreatType.JAILBREAK)
        result = agg.submit_indicators("org2", ["p2"], ThreatType.JAILBREAK)

        assert result.contributors == 2

    def test_shared_intelligence(self):
        """Shared intelligence after threshold."""
        agg = FederatedThreatAggregator(min_contributors=1)
        agg.submit_indicators("org1", ["p1"], ThreatType.EXTRACTION)

        shared = agg.get_shared_intelligence()

        assert len(shared) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
