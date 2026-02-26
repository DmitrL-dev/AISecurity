"""Tests for ContinuousTrainer."""

from micro_swarm.trainer import ContinuousTrainer, TrainingBuffer, TrainingSample
from micro_swarm.model import MicroModel


class TestTrainingBuffer:
    def test_add_and_size(self):
        buf = TrainingBuffer(capacity=5)
        assert buf.size == 0
        buf.add(TrainingSample([0.5] * 8, 1.0))
        assert buf.size == 1

    def test_capacity(self):
        buf = TrainingBuffer(capacity=3)
        for i in range(5):
            buf.add(TrainingSample([float(i)] * 8, 1.0))
        assert buf.size == 3  # oldest dropped

    def test_get_batch(self):
        buf = TrainingBuffer(capacity=10)
        for i in range(5):
            buf.add(TrainingSample([float(i)] * 8, 1.0))
        batch = buf.get_batch(3)
        assert len(batch) == 3

    def test_clear(self):
        buf = TrainingBuffer()
        buf.add(TrainingSample([0.0] * 8, 1.0))
        buf.clear()
        assert buf.size == 0


class TestContinuousTrainer:
    def test_ingest_no_train(self):
        model = MicroModel()
        trainer = ContinuousTrainer(model, train_every=5)
        # First ingest should not trigger training
        result = trainer.ingest([0.5] * 8, 1.0)
        assert result is None
        assert trainer.ingest_count == 1

    def test_ingest_triggers_train(self):
        model = MicroModel()
        trainer = ContinuousTrainer(model, train_every=3)
        results = []
        for i in range(3):
            r = trainer.ingest([0.5] * 8, 1.0)
            results.append(r)
        # 3rd ingest should trigger training
        assert results[-1] is not None
        assert trainer.train_count == 1

    def test_drift_detection_no_data(self):
        model = MicroModel()
        trainer = ContinuousTrainer(model)
        drift = trainer.detect_drift()
        assert not drift.is_drifting

    def test_force_train(self):
        model = MicroModel()
        trainer = ContinuousTrainer(model, train_every=100)
        for _ in range(10):
            trainer.ingest([0.5] * 8, 1.0)
        loss = trainer.force_train(2)
        assert loss > 0
        assert trainer.train_count == 2

    def test_buffer_size(self):
        model = MicroModel()
        trainer = ContinuousTrainer(model, buffer_size=5, train_every=100)
        for i in range(10):
            trainer.ingest([float(i) / 10] * 8, 1.0)
        assert trainer.buffer_size == 5
