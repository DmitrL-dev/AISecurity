"""ShadowAdapter — shadow learning for Micro-Model Swarm.

Attaches a MicroModel as 'shadow' to any decision-maker (e.g. Rust engine).
The shadow model learns from the engine's decisions and can detect disagreements
where the engine might be wrong (blind spot detection).
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from micro_swarm.model import MicroModel
from micro_swarm.trainer import ContinuousTrainer


@dataclass
class DisagreementReport:
    """Result of shadow vs engine comparison."""

    features: list[float]
    engine_decision: float       # Rule-based engine output
    shadow_prediction: float     # MicroModel prediction
    disagreement_score: float    # abs(engine - shadow)
    timestamp: float


class ShadowAdapter:
    """Attaches a MicroModel as 'shadow' to any decision-maker.

    Use case: attach to a Rust engine, learn its patterns,
    and flag when the shadow disagrees (potential blind spots).
    """

    def __init__(
        self,
        model: MicroModel,
        trainer: ContinuousTrainer | None = None,
        disagreement_threshold: float = 0.3,
    ) -> None:
        self._model = model
        self._trainer = trainer or ContinuousTrainer(
            model=model,
            train_every=5,
            model_name="shadow",
        )
        self._threshold = disagreement_threshold
        self._history: list[DisagreementReport] = []

    def observe(
        self, features: list[float], engine_decision: float
    ) -> float | None:
        """Feed engine decision to shadow model for learning.

        The engine's decision becomes the training target.
        Returns loss if training happened, None otherwise.
        """
        return self._trainer.ingest(features, engine_decision)

    def predict(self, features: list[float]) -> float:
        """Shadow model's own prediction."""
        score, _ = self._model.forward(features)
        return score

    def disagreement(
        self, features: list[float], engine_decision: float
    ) -> DisagreementReport:
        """Compare shadow vs engine, return disagreement report."""
        shadow_pred = self.predict(features)
        dis_score = abs(engine_decision - shadow_pred)

        report = DisagreementReport(
            features=features,
            engine_decision=engine_decision,
            shadow_prediction=shadow_pred,
            disagreement_score=dis_score,
            timestamp=time.time(),
        )

        if dis_score > self._threshold:
            self._history.append(report)

        return report

    @property
    def disagreement_history(self) -> list[DisagreementReport]:
        """Recent disagreements above threshold."""
        return list(self._history)

    @property
    def disagreement_count(self) -> int:
        return len(self._history)
