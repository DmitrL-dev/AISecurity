"""MetaLearner — combines domain scores into final prediction.

Uses a MicroModel that takes concatenated domain outputs as input.
Falls back to weighted average if not enough training data.
"""

from __future__ import annotations

from micro_swarm.model import MicroModel, MicroModelConfig


class MetaLearner:
    """Meta-Learner: combines domain scores + embeddings into final score.

    Uses a MicroModel that takes concatenated domain outputs as input.
    Falls back to weighted average if not enough training data.
    """

    def __init__(
        self,
        n_domains: int,
        embd_dim: int = 16,
        min_train_steps: int = 50,
    ) -> None:
        self._n_domains = n_domains
        self._embd_dim = embd_dim
        self._min_train_steps = min_train_steps

        # Input: per-domain (1 score + embd_dim embedding) × n_domains
        n_features = n_domains * (1 + embd_dim)
        self._model = MicroModel(
            MicroModelConfig(n_features=n_features,
                             n_embd=16, n_head=4, n_layer=1)
        )
        self._trained = False
        self._train_count = 0

    @property
    def is_ready(self) -> bool:
        return self._trained

    def predict(self, domain_scores: list) -> float:
        """Combine domain outputs into final score.

        Uses Meta-Learner model if trained, weighted average otherwise.

        Args:
            domain_scores: list of DomainScore objects
        """
        if not domain_scores:
            return 0.5

        if self._trained:
            features = self._build_features(domain_scores)
            score, _ = self._model.forward(features)
            return score

        # Fallback: simple average
        return self._weighted_average(domain_scores)

    def train_step(
        self, domain_scores: list, target: float, lr: float = 0.01
    ) -> float:
        """Train Meta-Learner on actual outcome."""
        features = self._build_features(domain_scores)
        loss = self._model.train_step(features, target, lr)
        self._train_count += 1
        if self._train_count >= self._min_train_steps:
            self._trained = True
        return loss

    def _build_features(self, domain_scores: list) -> list[float]:
        """Build feature vector from domain outputs."""
        features: list[float] = []
        for ds in domain_scores:
            features.append(ds.score)
            features.extend(ds.embedding)

        # Pad if fewer domains than expected
        expected = self._n_domains * (1 + self._embd_dim)
        while len(features) < expected:
            features.append(0.0)

        return features[:expected]

    @staticmethod
    def _weighted_average(domain_scores: list) -> float:
        """Simple average of domain scores."""
        valid = [ds for ds in domain_scores if ds.error is None]
        if not valid:
            return 0.5
        return sum(ds.score for ds in valid) / len(valid)


class CrossDomainMetaLearner(MetaLearner):
    """MetaLearner with cross-domain attention on embeddings.

    Instead of using score + embedding per domain, this learner
    uses only concatenated embeddings from all domains. The internal
    MicroModel's attention mechanism naturally learns cross-domain
    interaction effects (e.g., high entropy + high request rate =
    injection probing).

    Falls back to weighted average if not trained.
    """

    def __init__(
        self,
        n_domains: int,
        emb_dim: int = 16,
        min_train_steps: int = 10,
    ) -> None:
        # Skip MetaLearner.__init__ — we configure differently
        self._n_domains = n_domains
        self._emb_dim = emb_dim
        self._min_train_steps = min_train_steps

        # Input: n_domains embeddings concatenated → n_domains * emb_dim
        total_features = n_domains * emb_dim
        self._embd_dim = emb_dim  # compatibility with parent
        self._model = MicroModel(
            MicroModelConfig(
                n_features=total_features,
                n_embd=16,
                n_head=4,
                n_layer=1,
            )
        )
        self._trained = False
        self._train_count = 0

    def predict(self, domain_scores: list) -> float:
        """Combine domain embeddings via cross-domain attention.

        Uses the internal MicroModel on concatenated embeddings.
        Falls back to weighted average if not trained.
        """
        if not domain_scores:
            return 0.5

        if self._trained:
            features = self._concat_embeddings(domain_scores)
            score, _ = self._model.forward(features)
            return score

        return self._weighted_average(domain_scores)

    def train_step(
        self, domain_scores: list, target: float, lr: float = 0.01
    ) -> float:
        """Train on concatenated embeddings."""
        features = self._concat_embeddings(domain_scores)
        loss = self._model.train_step(features, target, lr)
        self._train_count += 1
        if self._train_count >= self._min_train_steps:
            self._trained = True
        return loss

    def _concat_embeddings(self, domain_scores: list) -> list[float]:
        """Concatenate embeddings from all domains with padding."""
        result: list[float] = []
        for ds in domain_scores:
            emb = list(ds.embedding[:self._emb_dim])
            # Pad if embedding shorter than expected
            emb += [0.0] * (self._emb_dim - len(emb))
            result.extend(emb)

        # Pad if fewer domains than expected
        expected = self._n_domains * self._emb_dim
        result += [0.0] * (expected - len(result))
        return result[:expected]
