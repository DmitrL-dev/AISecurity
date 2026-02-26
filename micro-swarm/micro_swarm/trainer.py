"""ContinuousTrainer — real-time learning loop for MicroModel Swarm.

Implements a ring buffer for session examples, auto-train triggers,
drift detection via rolling loss window, and weight checkpointing.
"""

from __future__ import annotations

import json
import logging
import time
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from micro_swarm.model import MicroModel

logger = logging.getLogger(__name__)


@dataclass
class TrainingSample:
    """Single training example."""

    features: list[float]
    target: float
    timestamp: float = 0.0


class TrainingBuffer:
    """Ring buffer for training samples.

    Fixed-capacity FIFO: oldest samples are dropped when full.
    """

    def __init__(self, capacity: int = 1000) -> None:
        self._capacity = capacity
        self._buffer: deque[TrainingSample] = deque(maxlen=capacity)

    @property
    def size(self) -> int:
        return len(self._buffer)

    @property
    def capacity(self) -> int:
        return self._capacity

    @property
    def is_full(self) -> bool:
        return len(self._buffer) >= self._capacity

    def add(self, sample: TrainingSample) -> None:
        self._buffer.append(sample)

    def get_batch(self, batch_size: int) -> list[TrainingSample]:
        """Get the last N samples (most recent)."""
        n = min(batch_size, len(self._buffer))
        return list(self._buffer)[-n:]

    def clear(self) -> None:
        self._buffer.clear()


@dataclass
class DriftStatus:
    """Drift detection result."""

    is_drifting: bool
    recent_loss: float
    baseline_loss: float
    drift_ratio: float


class ContinuousTrainer:
    """Continuous training loop for a MicroModel.

    Features:
    - Ring buffer for training examples
    - Auto-train trigger every N ingested examples
    - Drift detection via rolling loss window
    - Weight checkpointing
    """

    def __init__(
        self,
        model: MicroModel,
        buffer_size: int = 1000,
        train_every: int = 10,
        lr: float = 0.01,
        drift_window: int = 50,
        drift_threshold: float = 1.5,
        checkpoint_every: int = 100,
        checkpoint_dir: str | None = None,
        model_name: str = "model",
    ) -> None:
        self._model = model
        self._buffer = TrainingBuffer(capacity=buffer_size)
        self._train_every = train_every
        self._lr = lr
        self._drift_window = drift_window
        self._drift_threshold = drift_threshold
        self._checkpoint_every = checkpoint_every
        self._checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else None
        self._model_name = model_name

        self._ingest_count = 0
        self._train_count = 0
        self._loss_history: deque[float] = deque(maxlen=drift_window * 2)

    @property
    def ingest_count(self) -> int:
        return self._ingest_count

    @property
    def train_count(self) -> int:
        return self._train_count

    @property
    def buffer_size(self) -> int:
        return self._buffer.size

    def ingest(self, features: list[float], target: float) -> float | None:
        """Add a training example. Auto-trains if trigger threshold is reached.

        Returns loss if training happened, None otherwise.
        """
        sample = TrainingSample(
            features=features, target=target, timestamp=time.time()
        )
        self._buffer.add(sample)
        self._ingest_count += 1

        # Auto-train trigger
        if self._ingest_count % self._train_every == 0:
            return self._train_batch()

        return None

    def _train_batch(self) -> float:
        """Train on the most recent batch."""
        batch = self._buffer.get_batch(self._train_every)
        total_loss = 0.0
        for sample in batch:
            loss = self._model.train_step(
                sample.features, sample.target, self._lr)
            total_loss += loss
            self._loss_history.append(loss)

        avg_loss = total_loss / len(batch) if batch else 0.0
        self._train_count += 1

        # Checkpoint
        if (
            self._checkpoint_dir
            and self._train_count % self._checkpoint_every == 0
        ):
            self._save_checkpoint()

        return avg_loss

    def detect_drift(self) -> DriftStatus:
        """Detect concept drift by comparing recent vs baseline loss.

        Drift = recent_loss / baseline_loss > threshold
        """
        if len(self._loss_history) < self._drift_window * 2:
            return DriftStatus(
                is_drifting=False,
                recent_loss=0.0,
                baseline_loss=0.0,
                drift_ratio=0.0,
            )

        losses = list(self._loss_history)
        half = len(losses) // 2
        baseline = sum(losses[:half]) / half
        recent = sum(losses[half:]) / (len(losses) - half)

        ratio = recent / baseline if baseline > 0 else 0.0
        is_drifting = ratio > self._drift_threshold

        if is_drifting:
            logger.warning(
                "Drift detected in %s: ratio=%.2f (threshold=%.2f)",
                self._model_name,
                ratio,
                self._drift_threshold,
            )

        return DriftStatus(
            is_drifting=is_drifting,
            recent_loss=recent,
            baseline_loss=baseline,
            drift_ratio=ratio,
        )

    def _save_checkpoint(self) -> None:
        """Save model weights to checkpoint directory."""
        if self._checkpoint_dir is None:
            return
        self._checkpoint_dir.mkdir(parents=True, exist_ok=True)
        path = self._checkpoint_dir / \
            f"{self._model_name}_step{self._train_count}.json"
        self._model.save(str(path))
        logger.info("Checkpoint saved: %s", path)

    def force_train(self, n_steps: int = 1) -> float:
        """Force N training steps on the buffer."""
        total_loss = 0.0
        for _ in range(n_steps):
            loss = self._train_batch()
            total_loss += loss
        return total_loss / n_steps if n_steps > 0 else 0.0
