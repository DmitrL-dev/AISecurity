"""SwarmOrchestrator — multi-model ensemble coordinator.

Orchestrates N domain-specialized MicroModels and combines their outputs
via a Meta-Learner (Shared Signal architecture).
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass
from typing import Any

from micro_swarm.model import MicroModel, MicroModelConfig
from micro_swarm.config import DomainConfig
from micro_swarm.meta_learner import MetaLearner

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────
# Data classes
# ──────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class DomainScore:
    """Score from a single domain model."""

    domain: str
    score: float
    embedding: list[float]
    latency_ms: float
    error: str | None = None


@dataclass(frozen=True, slots=True)
class SwarmResult:
    """Result from the full Swarm prediction."""

    final_score: float
    domain_scores: dict[str, DomainScore]
    meta_used: bool
    latency_ms: float
    active_models: int
    failed_models: int = 0
    confidence: float = 0.5

    def explain(self) -> dict[str, Any]:
        """Explain prediction with domain contributions and confidence.

        Returns dict with:
        - final_score, confidence, meta_used
        - domains: {name: {score, latency_ms, error}}
        - confidence_reasoning: why confidence is high/low
        """
        domains_info: dict[str, dict[str, Any]] = {}
        for name, ds in self.domain_scores.items():
            domains_info[name] = {
                "score": ds.score,
                "latency_ms": ds.latency_ms,
                "error": ds.error,
            }

        # Confidence reasoning
        if self.active_models <= 1:
            reasoning = "Single domain — confidence undefined (0.5)"
        elif self.confidence >= 0.8:
            reasoning = "High agreement across domains"
        elif self.confidence >= 0.5:
            reasoning = "Moderate agreement across domains"
        else:
            reasoning = "High disagreement — consider human review"

        return {
            "final_score": self.final_score,
            "confidence": self.confidence,
            "confidence_reasoning": reasoning,
            "meta_used": self.meta_used,
            "active_models": self.active_models,
            "failed_models": self.failed_models,
            "latency_ms": self.latency_ms,
            "domains": domains_info,
        }


# ──────────────────────────────────────────
# SwarmOrchestrator
# ──────────────────────────────────────────


class SwarmOrchestrator:
    """Orchestrates N domain-specialized MicroModels.

    Routes session features to the appropriate domain model,
    collects scores/embeddings, and passes them to the MetaLearner.
    """

    def __init__(
        self,
        models: dict[str, MicroModel],
        domains: dict[str, DomainConfig],
        meta_learner: MetaLearner | None = None,
    ) -> None:
        if set(models.keys()) != set(domains.keys()):
            raise ValueError(
                f"Models and domains must have same keys. "
                f"Models: {set(models.keys())}, Domains: {set(domains.keys())}"
            )
        self._models = models
        self._domains = domains
        self._meta = meta_learner or MetaLearner(n_domains=len(models))

    @property
    def model_count(self) -> int:
        return len(self._models)

    @property
    def domain_names(self) -> list[str]:
        return list(self._models.keys())

    @property
    def meta_learner(self) -> MetaLearner:
        return self._meta

    def predict(self, session_data: dict[str, Any]) -> SwarmResult:
        """Route session data to domain models and aggregate.

        Graceful degradation: if a model fails, skip it and use remaining.
        """
        start = time.perf_counter()

        domain_scores: dict[str, DomainScore] = {}
        failed = 0

        for name in self._models:
            ds = self._score_domain(name, session_data)
            domain_scores[name] = ds
            if ds.error is not None:
                failed += 1

        # Meta-Learner combines
        valid_scores = [ds for ds in domain_scores.values()
                        if ds.error is None]
        final_score = self._meta.predict(valid_scores)

        # Confidence from domain agreement
        confidence = self._compute_confidence(valid_scores)

        elapsed_ms = (time.perf_counter() - start) * 1000

        return SwarmResult(
            final_score=final_score,
            domain_scores=domain_scores,
            meta_used=self._meta.is_ready,
            latency_ms=elapsed_ms,
            active_models=len(valid_scores),
            failed_models=failed,
            confidence=confidence,
        )

    def train_step(
        self,
        session_data: dict[str, Any],
        target: float,
        lr: float = 0.01,
    ) -> dict[str, float]:
        """Train all domain models + meta-learner on one example.

        Returns dict of {domain_name: loss, "meta": loss}.
        """
        losses: dict[str, float] = {}

        # Train each domain model
        domain_scores: list[DomainScore] = []
        for name, model in self._models.items():
            domain = self._domains[name]
            features = domain.extract(session_data)
            loss = model.train_step(features, target, lr)
            losses[name] = loss

            score, emb = model.forward(features)
            domain_scores.append(
                DomainScore(domain=name, score=score,
                            embedding=emb, latency_ms=0)
            )

        # Train meta-learner
        if domain_scores:
            meta_loss = self._meta.train_step(domain_scores, target, lr)
            losses["meta"] = meta_loss

        return losses

    def _score_domain(
        self, name: str, session_data: dict[str, Any]
    ) -> DomainScore:
        """Score a single domain, catching errors gracefully."""
        start = time.perf_counter()
        try:
            domain = self._domains[name]
            features = domain.extract(session_data)
            score, embedding = self._models[name].forward(features)
            elapsed = (time.perf_counter() - start) * 1000
            return DomainScore(
                domain=name, score=score,
                embedding=embedding, latency_ms=elapsed
            )
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.warning("Domain %s failed: %s", name, e)
            return DomainScore(
                domain=name,
                score=0.5,
                embedding=[0.0] * self._domains[name].n_features,
                latency_ms=elapsed,
                error=str(e),
            )

    @staticmethod
    def _compute_confidence(valid_scores: list[DomainScore]) -> float:
        """Compute confidence from domain agreement.

        confidence = 1.0 - normalized_std(scores)
        - 1 domain → 0.5 (undefined)
        - All same scores → 1.0
        - [0.0, 1.0] → ≈ 0.0
        """
        if len(valid_scores) <= 1:
            return 0.5

        scores = [ds.score for ds in valid_scores]
        n = len(scores)
        mean = sum(scores) / n
        variance = sum((s - mean) ** 2 for s in scores) / n
        std = math.sqrt(variance)

        # Normalize: max possible std for [0,1] scores with N values
        # is 0.5 (when half are 0 and half are 1)
        max_std = 0.5
        normalized = min(std / max_std, 1.0)

        return 1.0 - normalized
