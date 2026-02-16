"""Tests for all presets."""

import pytest

from micro_swarm.presets import load_preset, list_presets
from micro_swarm.orchestrator import SwarmResult


class TestPresetRegistry:
    def test_list_presets(self):
        presets = list_presets()
        assert "adtech" in presets
        assert "security" in presets
        assert "fraud" in presets
        assert "strike" in presets

    def test_unknown_preset(self):
        with pytest.raises(ValueError, match="Unknown preset"):
            load_preset("nonexistent")


class TestAdTechPreset:
    def test_load(self):
        swarm = load_preset("adtech")
        assert swarm.model_count == 3
        assert set(swarm.domain_names) == {"timing", "geo", "device"}

    def test_predict(self):
        swarm = load_preset("adtech")
        result = swarm.predict({})
        assert isinstance(result, SwarmResult)
        assert 0.0 <= result.final_score <= 1.0


class TestSecurityPreset:
    def test_load(self):
        swarm = load_preset("security")
        assert swarm.model_count == 3
        assert set(swarm.domain_names) == {
            "token_pattern", "semantic_shift", "behavioral"
        }

    def test_predict(self):
        swarm = load_preset("security")
        data = {"entropy": 0.9, "special_char_ratio": 0.3}
        result = swarm.predict(data)
        assert 0.0 <= result.final_score <= 1.0

    def test_all_domains_scored(self):
        swarm = load_preset("security")
        result = swarm.predict({})
        assert len(result.domain_scores) == 3
        for ds in result.domain_scores.values():
            assert 0.0 <= ds.score <= 1.0


class TestFraudPreset:
    def test_load(self):
        swarm = load_preset("fraud")
        assert swarm.model_count == 3
        assert set(swarm.domain_names) == {"velocity", "amount", "pattern"}

    def test_predict(self):
        swarm = load_preset("fraud")
        data = {"tx_per_hour": 50, "amount_deviation": 500}
        result = swarm.predict(data)
        assert 0.0 <= result.final_score <= 1.0


class TestStrikePreset:
    def test_load(self):
        swarm = load_preset("strike")
        assert swarm.model_count == 3
        assert set(swarm.domain_names) == {
            "stealth_timing", "fingerprint", "behavioral_mimicry"
        }

    def test_predict(self):
        swarm = load_preset("strike")
        data = {"jitter_ms": 500, "tls_version": 3}
        result = swarm.predict(data)
        assert 0.0 <= result.final_score <= 1.0

    def test_all_domains_have_8_features(self):
        swarm = load_preset("strike")
        for name in swarm.domain_names:
            domain = swarm._domains[name]
            assert domain.n_features == 8, f"{name} has {domain.n_features} features"


class TestAllPresetsProperties:
    """Property tests across all presets."""

    @pytest.mark.parametrize("preset_name", list_presets())
    def test_score_in_range(self, preset_name):
        swarm = load_preset(preset_name)
        result = swarm.predict({})
        assert 0.0 <= result.final_score <= 1.0

    @pytest.mark.parametrize("preset_name", list_presets())
    def test_three_domains(self, preset_name):
        swarm = load_preset(preset_name)
        assert swarm.model_count >= 3

    @pytest.mark.parametrize("preset_name", list_presets())
    def test_param_count_positive(self, preset_name):
        swarm = load_preset(preset_name)
        for name in swarm.domain_names:
            assert swarm._models[name].param_count > 0

    @pytest.mark.parametrize("preset_name", list_presets())
    def test_each_domain_has_description(self, preset_name):
        swarm = load_preset(preset_name)
        for name in swarm.domain_names:
            domain = swarm._domains[name]
            assert domain.description, f"{preset_name}/{name} missing description"
