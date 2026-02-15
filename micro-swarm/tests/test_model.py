"""Tests for MicroModel."""

import json
import tempfile
from pathlib import Path

from micro_swarm.model import MicroModel, MicroModelConfig


class TestMicroModelForward:
    """Forward pass tests."""

    def test_forward_basic(self):
        model = MicroModel()
        features = [0.5] * 8
        score, embedding = model.forward(features)
        assert 0.0 <= score <= 1.0
        assert len(embedding) == 16  # n_embd default

    def test_forward_deterministic(self):
        m1 = MicroModel(MicroModelConfig(seed=42))
        m2 = MicroModel(MicroModelConfig(seed=42))
        features = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8]
        s1, _ = m1.forward(features)
        s2, _ = m2.forward(features)
        assert s1 == s2

    def test_forward_wrong_features(self):
        model = MicroModel()
        try:
            model.forward([0.5] * 5)
            assert False, "Should raise ValueError"
        except ValueError:
            pass

    def test_param_count(self):
        model = MicroModel()
        assert model.param_count > 0
        # Default: 8 features, 16 embd, 4 heads, 1 layer
        # Expected: 8*16 + 6*(16*16) + 1*16 = 128 + 1536 + 16 = 1680
        assert model.param_count > 100

    def test_memory_bytes(self):
        model = MicroModel()
        assert model.memory_bytes == model.param_count * 4

    def test_config_access(self):
        config = MicroModelConfig(n_features=4)
        model = MicroModel(config)
        assert model.config.n_features == 4


class TestMicroModelTraining:
    """Training tests."""

    def test_train_step(self):
        model = MicroModel()
        features = [0.5] * 8
        loss = model.train_step(features, 1.0)
        assert loss > 0

    def test_train_reduces_loss(self):
        model = MicroModel()
        features = [0.5] * 8
        loss1 = model.train_step(features, 1.0)
        for _ in range(10):
            model.train_step(features, 1.0)
        loss2 = model.train_step(features, 1.0)
        assert loss2 < loss1

    def test_forward_train(self):
        model = MicroModel()
        features = [0.5] * 8
        score, loss = model.forward_train(features, 1.0)
        assert 0.0 <= score <= 1.0
        assert loss.data > 0


class TestMicroModelSaveLoad:
    """Save/load tests."""

    def test_export_import(self):
        model = MicroModel(MicroModelConfig(seed=42))
        features = [0.5] * 8
        score1, _ = model.forward(features)

        state = model.export_weights()
        model2 = MicroModel(MicroModelConfig(seed=99))  # different seed
        model2.load_weights(state)
        score2, _ = model2.forward(features)

        assert abs(score1 - score2) < 1e-10

    def test_save_load_file(self):
        model = MicroModel(MicroModelConfig(seed=42))
        features = [0.5] * 8
        score1, _ = model.forward(features)

        with tempfile.TemporaryDirectory() as td:
            path = str(Path(td) / "model.json")
            model.save(path)
            model2 = MicroModel.load(path)
            score2, _ = model2.forward(features)

        assert abs(score1 - score2) < 1e-10

    def test_weight_count_mismatch(self):
        model = MicroModel()
        state = model.export_weights()
        state["weights"] = [0.0]  # wrong count
        try:
            model.load_weights(state)
            assert False, "Should raise ValueError"
        except ValueError:
            pass
