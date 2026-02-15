"""Tests for CrossDomainMetaLearner — cross-domain attention on embeddings.

Verifies:
- Construction and is_ready property
- Fallback to weighted average when untrained
- Training and prediction with embeddings
- Padding for fewer domains / shorter embeddings
- Backward compatibility with MetaLearner
"""

from __future__ import annotations

from dataclasses import dataclass

from micro_swarm.meta_learner import MetaLearner, CrossDomainMetaLearner


@dataclass
class FakeDomainScore:
    """Minimal DomainScore-like object for testing."""

    domain: str
    score: float
    embedding: list[float]
    error: str | None = None


def _make_scores(n: int = 3, emb_dim: int = 16) -> list[FakeDomainScore]:
    """Create N fake domain scores with random-ish embeddings."""
    names = ["d0", "d1", "d2", "d3", "d4"]
    result = []
    for i in range(n):
        emb = [0.1 * (i + 1) * (j + 1) for j in range(emb_dim)]
        result.append(FakeDomainScore(
            domain=names[i], score=0.2 + 0.2 * i, embedding=emb
        ))
    return result


class TestCrossDomainConstruction:
    def test_inherits_meta_learner(self) -> None:
        cdml = CrossDomainMetaLearner(n_domains=3)
        assert isinstance(cdml, MetaLearner)

    def test_not_ready_initially(self) -> None:
        cdml = CrossDomainMetaLearner(n_domains=3)
        assert not cdml.is_ready

    def test_ready_after_min_steps(self) -> None:
        cdml = CrossDomainMetaLearner(n_domains=3, min_train_steps=2)
        scores = _make_scores(3)
        cdml.train_step(scores, 1.0)
        assert not cdml.is_ready
        cdml.train_step(scores, 0.0)
        assert cdml.is_ready


class TestCrossDomainFallback:
    def test_empty_scores(self) -> None:
        cdml = CrossDomainMetaLearner(n_domains=3)
        assert cdml.predict([]) == 0.5

    def test_fallback_average(self) -> None:
        cdml = CrossDomainMetaLearner(n_domains=3)
        scores = _make_scores(3)
        result = cdml.predict(scores)
        expected = sum(s.score for s in scores) / len(scores)
        assert abs(result - expected) < 1e-10


class TestCrossDomainTraining:
    def test_loss_decreases(self) -> None:
        cdml = CrossDomainMetaLearner(n_domains=3, min_train_steps=5)
        scores = _make_scores(3)
        losses = []
        for _ in range(20):
            loss = cdml.train_step(scores, 0.8, lr=0.01)
            losses.append(loss)
        # Loss should decrease over time
        assert losses[-1] < losses[0]

    def test_prediction_after_training(self) -> None:
        cdml = CrossDomainMetaLearner(n_domains=3, min_train_steps=5)
        scores = _make_scores(3)
        for _ in range(10):
            cdml.train_step(scores, 0.8, lr=0.01)
        result = cdml.predict(scores)
        assert 0.0 <= result <= 1.0


class TestCrossDomainPadding:
    def test_fewer_domains(self) -> None:
        """2 domains when 3 expected → padding."""
        cdml = CrossDomainMetaLearner(n_domains=3, min_train_steps=1)
        scores = _make_scores(2)
        cdml.train_step(scores, 0.5)
        result = cdml.predict(scores)
        assert 0.0 <= result <= 1.0

    def test_shorter_embeddings(self) -> None:
        """Embedding shorter than emb_dim → padding."""
        cdml = CrossDomainMetaLearner(
            n_domains=2, emb_dim=16, min_train_steps=1)
        scores = [
            FakeDomainScore(domain="a", score=0.5, embedding=[0.1] * 8),
            FakeDomainScore(domain="b", score=0.7, embedding=[0.2] * 8),
        ]
        cdml.train_step(scores, 0.6)
        result = cdml.predict(scores)
        assert 0.0 <= result <= 1.0


class TestCrossDomainPresets:
    """Presets should use CrossDomainMetaLearner by default."""

    def test_security_preset(self) -> None:
        from micro_swarm.presets import load_preset
        swarm = load_preset("security")
        assert isinstance(swarm.meta_learner, CrossDomainMetaLearner)

    def test_adtech_preset(self) -> None:
        from micro_swarm.presets import load_preset
        swarm = load_preset("adtech")
        assert isinstance(swarm.meta_learner, CrossDomainMetaLearner)

    def test_fraud_preset(self) -> None:
        from micro_swarm.presets import load_preset
        swarm = load_preset("fraud")
        assert isinstance(swarm.meta_learner, CrossDomainMetaLearner)

    def test_strike_preset(self) -> None:
        from micro_swarm.presets import load_preset
        swarm = load_preset("strike")
        assert isinstance(swarm.meta_learner, CrossDomainMetaLearner)
