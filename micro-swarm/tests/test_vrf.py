"""Tests for VRFFeatureSelector — cryptographic feature masking.

Verifies:
- Determinism: same (key, session, model) → same mask
- Unpredictability: different sessions → different masks
- Coverage: all features eventually selected across sessions
- Verification: valid masks pass, tampered fail
- Masking: features correctly zeroed
- Min/max bounds respected
- Security: HMAC-SHA256 collision resistance
"""

from __future__ import annotations

from micro_swarm.vrf import VRFFeatureSelector, FeatureMask


class TestDeterminism:
    """Same inputs → same output. This is the 'Verifiable' in VRF."""

    def test_same_key_session_model(self) -> None:
        vrf = VRFFeatureSelector(b"secret-sentinel-key")
        m1 = vrf.select("session-001", "model-a", 8)
        m2 = vrf.select("session-001", "model-a", 8)
        assert m1.selected_indices == m2.selected_indices
        assert m1.vrf_hash == m2.vrf_hash

    def test_reproducible_across_instances(self) -> None:
        vrf1 = VRFFeatureSelector(b"same-key")
        vrf2 = VRFFeatureSelector(b"same-key")
        m1 = vrf1.select("s1", "m1", 10)
        m2 = vrf2.select("s1", "m1", 10)
        assert m1.selected_indices == m2.selected_indices


class TestUnpredictability:
    """Different inputs → different (unpredictable) output."""

    def test_different_sessions(self) -> None:
        vrf = VRFFeatureSelector(b"key")
        m1 = vrf.select("session-001", "model-a", 8)
        m2 = vrf.select("session-002", "model-a", 8)
        # Masks SHOULD be different (astronomically unlikely to be same)
        assert m1.selected_indices != m2.selected_indices

    def test_different_models(self) -> None:
        vrf = VRFFeatureSelector(b"key")
        m1 = vrf.select("session-001", "model-a", 8)
        m2 = vrf.select("session-001", "model-b", 8)
        assert m1.selected_indices != m2.selected_indices

    def test_different_keys(self) -> None:
        vrf1 = VRFFeatureSelector(b"key-alpha")
        vrf2 = VRFFeatureSelector(b"key-beta")
        m1 = vrf1.select("s1", "m1", 8)
        m2 = vrf2.select("s1", "m1", 8)
        assert m1.selected_indices != m2.selected_indices


class TestCoverage:
    """Over many sessions, all features should be selected at least once."""

    def test_full_coverage_over_sessions(self) -> None:
        vrf = VRFFeatureSelector(b"coverage-key", selection_ratio=0.5)
        n_features = 8
        seen: set[int] = set()
        for i in range(100):
            mask = vrf.select(f"session-{i}", "model-x", n_features)
            seen.update(mask.selected_indices)
        # Over 100 sessions with 50% selection, all 8 features seen
        assert seen == set(range(n_features))

    def test_uniform_distribution(self) -> None:
        """Feature selection should be approximately uniform."""
        vrf = VRFFeatureSelector(b"uniform-key", selection_ratio=0.5)
        n_features = 8
        counts: dict[int, int] = {i: 0 for i in range(n_features)}
        n_sessions = 200
        for i in range(n_sessions):
            mask = vrf.select(f"s-{i}", "m", n_features)
            for idx in mask.selected_indices:
                counts[idx] += 1
        # Each feature should be selected ~50% of the time (±20%)
        for count in counts.values():
            ratio = count / n_sessions
            assert 0.2 < ratio < 0.8, f"Feature selection ratio {ratio} outside expected range"


class TestVerification:
    """Mask verification — detect tampering."""

    def test_valid_mask_verifies(self) -> None:
        vrf = VRFFeatureSelector(b"verify-key")
        mask = vrf.select("s1", "m1", 8)
        assert vrf.verify(mask) is True

    def test_tampered_hash_fails(self) -> None:
        vrf = VRFFeatureSelector(b"verify-key")
        mask = vrf.select("s1", "m1", 8)
        # Tamper with hash
        tampered = FeatureMask(
            session_id=mask.session_id,
            model_id=mask.model_id,
            selected_indices=mask.selected_indices,
            total_features=mask.total_features,
            selection_ratio=mask.selection_ratio,
            vrf_hash="0" * 64,  # fake hash
        )
        assert vrf.verify(tampered) is False

    def test_wrong_key_fails(self) -> None:
        vrf1 = VRFFeatureSelector(b"real-key")
        vrf2 = VRFFeatureSelector(b"wrong-key")
        mask = vrf1.select("s1", "m1", 8)
        assert vrf2.verify(mask) is False


class TestMasking:
    """Feature masking — applying VRF to actual data."""

    def test_mask_features_dict(self) -> None:
        vrf = VRFFeatureSelector(b"mask-key", selection_ratio=0.5)
        features = {"a": 1.0, "b": 2.0, "c": 3.0, "d": 4.0}
        mask = vrf.select("s1", "m1", len(features))
        result = vrf.mask_features(features, mask)
        # All keys present, but some zeroed
        assert len(result) == len(features)
        non_zero = sum(1 for v in result.values() if v != 0.0)
        assert non_zero == len(mask.selected_indices)

    def test_mask_vector(self) -> None:
        vrf = VRFFeatureSelector(b"vec-key", selection_ratio=0.5)
        vector = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        mask = vrf.select("s1", "m1", len(vector))
        result = vrf.mask_vector(vector, mask)
        assert len(result) == len(vector)
        for i, v in enumerate(result):
            if i in mask.selected_indices:
                assert v == vector[i]
            else:
                assert v == 0.0


class TestBounds:
    """Min/max feature selection bounds."""

    def test_min_features(self) -> None:
        vrf = VRFFeatureSelector(b"k", min_features=5, selection_ratio=0.1)
        mask = vrf.select("s1", "m1", 10)
        assert len(mask.selected_indices) >= 5

    def test_max_features(self) -> None:
        vrf = VRFFeatureSelector(b"k", max_features=3, selection_ratio=0.9)
        mask = vrf.select("s1", "m1", 10)
        assert len(mask.selected_indices) <= 3

    def test_all_features_when_n_small(self) -> None:
        vrf = VRFFeatureSelector(b"k", min_features=5)
        mask = vrf.select("s1", "m1", 3)  # fewer than min
        assert len(mask.selected_indices) == 3  # can't select more than exist

    def test_string_key(self) -> None:
        vrf = VRFFeatureSelector("string-key-also-works")
        mask = vrf.select("s1", "m1", 8)
        assert len(mask.selected_indices) > 0


class TestSecurity:
    """Security properties of HMAC-SHA256 VRF."""

    def test_hash_length(self) -> None:
        """SHA-256 produces 64 hex chars = 256 bits."""
        vrf = VRFFeatureSelector(b"k")
        mask = vrf.select("s1", "m1", 8)
        assert len(mask.vrf_hash) == 64

    def test_avalanche_effect(self) -> None:
        """Tiny input change → completely different hash (avalanche)."""
        vrf = VRFFeatureSelector(b"k")
        m1 = vrf.select("session-001", "m1", 20)
        m2 = vrf.select("session-002", "m1", 20)
        # Hashes should differ in roughly 50% of bits
        bits_differ = bin(
            int(m1.vrf_hash, 16) ^ int(m2.vrf_hash, 16)
        ).count("1")
        # Expect ~128 bits different out of 256 (±40)
        assert 80 < bits_differ < 180
