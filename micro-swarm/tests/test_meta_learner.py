"""Tests for MetaLearner (standalone)."""

from micro_swarm.meta_learner import MetaLearner
from micro_swarm.orchestrator import DomainScore


class TestMetaLearnerStandalone:
    def test_init(self):
        meta = MetaLearner(n_domains=3)
        assert not meta.is_ready

    def test_weighted_average_fallback(self):
        meta = MetaLearner(n_domains=2)
        scores = [
            DomainScore("a", 0.2, [0.0] * 16, 0.1),
            DomainScore("b", 0.8, [0.0] * 16, 0.1),
        ]
        result = meta.predict(scores)
        assert abs(result - 0.5) < 1e-6

    def test_handles_errors(self):
        meta = MetaLearner(n_domains=2)
        scores = [
            DomainScore("a", 0.8, [0.0] * 16, 0.1),
            DomainScore("b", 0.5, [0.0] * 16, 0.1, error="failed"),
        ]
        result = meta.predict(scores)
        # Only uses non-error scores
        assert abs(result - 0.8) < 1e-6

    def test_train_and_predict(self):
        meta = MetaLearner(n_domains=1, min_train_steps=3)
        scores = [DomainScore("d", 0.5, [0.0] * 16, 0.1)]
        for _ in range(3):
            meta.train_step(scores, 1.0)
        assert meta.is_ready
        result = meta.predict(scores)
        assert 0.0 <= result <= 1.0
