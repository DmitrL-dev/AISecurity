"""Tests for SwarmOrchestrator."""

from micro_swarm.orchestrator import SwarmOrchestrator, DomainScore, SwarmResult
from micro_swarm.model import MicroModel, MicroModelConfig
from micro_swarm.config import DomainConfig, FeatureSpec, NormMethod
from micro_swarm.meta_learner import MetaLearner


def _make_domain(name: str, n_features: int = 8) -> DomainConfig:
    features = tuple(
        FeatureSpec(f"f{i}", NormMethod.MIN_MAX, 0, 1, 0.5, 0.3)
        for i in range(n_features)
    )
    return DomainConfig(name=name, features=features)


def _make_swarm(n_domains: int = 3) -> SwarmOrchestrator:
    names = [f"domain_{i}" for i in range(n_domains)]
    models = {n: MicroModel(MicroModelConfig(seed=i))
              for i, n in enumerate(names)}
    domains = {n: _make_domain(n) for n in names}
    return SwarmOrchestrator(models=models, domains=domains)


class TestSwarmOrchestrator:
    def test_predict(self):
        swarm = _make_swarm()
        data = {f"f{i}": 0.5 for i in range(8)}
        result = swarm.predict(data)
        assert isinstance(result, SwarmResult)
        assert 0.0 <= result.final_score <= 1.0
        assert result.active_models == 3
        assert result.failed_models == 0

    def test_model_count(self):
        swarm = _make_swarm(2)
        assert swarm.model_count == 2

    def test_domain_names(self):
        swarm = _make_swarm(3)
        assert len(swarm.domain_names) == 3

    def test_train_step(self):
        swarm = _make_swarm()
        data = {f"f{i}": 0.5 for i in range(8)}
        losses = swarm.train_step(data, 1.0)
        assert "meta" in losses
        assert all(v > 0 for v in losses.values())

    def test_graceful_degradation(self):
        """Model should handle missing features gracefully."""
        swarm = _make_swarm()
        # No data — all features get default values
        result = swarm.predict({})
        assert 0.0 <= result.final_score <= 1.0

    def test_mismatched_keys_raises(self):
        try:
            SwarmOrchestrator(
                models={"a": MicroModel()},
                domains={"b": _make_domain("b")},
            )
            assert False, "Should raise ValueError"
        except ValueError:
            pass


class TestMetaLearner:
    def test_fallback_average(self):
        meta = MetaLearner(n_domains=2)
        scores = [
            DomainScore("d1", 0.8, [0.0] * 16, 0.1),
            DomainScore("d2", 0.6, [0.0] * 16, 0.1),
        ]
        result = meta.predict(scores)
        assert abs(result - 0.7) < 1e-6

    def test_empty_scores(self):
        meta = MetaLearner(n_domains=2)
        assert meta.predict([]) == 0.5

    def test_is_ready_after_training(self):
        meta = MetaLearner(n_domains=1, min_train_steps=5)
        assert not meta.is_ready
        scores = [DomainScore("d1", 0.5, [0.0] * 16, 0.1)]
        for _ in range(5):
            meta.train_step(scores, 1.0)
        assert meta.is_ready
