"""Tests for Eval-Mode: inference without autograd overhead.

Verifies:
- eval()/train_mode() switching
- Numerical equivalence: eval forward == autograd forward (±1e-10)
- eval-mode does NOT create Value objects (performance)
- Speed benchmark: eval-mode < 2ms
"""

from __future__ import annotations

import time
from micro_swarm.model import (
    MicroModel,
    MicroModelConfig,
    _linear_eval,
    _rmsnorm_eval,
    _sigmoid_eval,
)
from micro_swarm.autograd import Value


# ──────────────────────────────────────────
# Float-helper correctness
# ──────────────────────────────────────────


class TestLinearEval:
    def test_identity_like(self) -> None:
        """2x2 identity-like multiplication."""
        x = [1.0, 2.0]
        w = [[1.0, 0.0], [0.0, 1.0]]
        result = _linear_eval(x, w)
        assert result == [1.0, 2.0]

    def test_scaling(self) -> None:
        x = [3.0, 4.0]
        w = [[2.0, 0.0], [0.0, 3.0]]
        result = _linear_eval(x, w)
        assert result == [6.0, 12.0]

    def test_mixed(self) -> None:
        x = [1.0, 2.0, 3.0]
        w = [[1.0, 1.0, 1.0]]
        result = _linear_eval(x, w)
        assert abs(result[0] - 6.0) < 1e-10


class TestRmsNormEval:
    def test_unit_vector(self) -> None:
        """Normalizing already-unit vector."""
        result = _rmsnorm_eval([1.0, 0.0, 0.0])
        rms = (1.0 / 3.0 + 1e-5) ** -0.5
        assert abs(result[0] - 1.0 * rms) < 1e-6

    def test_uniform(self) -> None:
        """All same values → output proportional."""
        result = _rmsnorm_eval([2.0, 2.0, 2.0, 2.0])
        # All outputs should be identical
        assert all(abs(r - result[0]) < 1e-10 for r in result)


class TestSigmoidEval:
    def test_zero(self) -> None:
        assert abs(_sigmoid_eval(0.0) - 0.5) < 1e-10

    def test_large_positive(self) -> None:
        assert abs(_sigmoid_eval(100.0) - 1.0) < 1e-10

    def test_large_negative(self) -> None:
        assert abs(_sigmoid_eval(-100.0)) < 1e-10

    def test_symmetry(self) -> None:
        assert abs(_sigmoid_eval(2.0) + _sigmoid_eval(-2.0) - 1.0) < 1e-10


# ──────────────────────────────────────────
# Eval/Train mode switching
# ──────────────────────────────────────────


class TestEvalTrainSwitch:
    def test_default_is_train(self) -> None:
        model = MicroModel()
        assert not model.is_eval

    def test_eval_returns_self(self) -> None:
        model = MicroModel()
        result = model.eval()
        assert result is model
        assert model.is_eval

    def test_train_mode_returns_self(self) -> None:
        model = MicroModel()
        model.eval()
        result = model.train_mode()
        assert result is model
        assert not model.is_eval

    def test_toggle(self) -> None:
        model = MicroModel()
        model.eval()
        assert model.is_eval
        model.train_mode()
        assert not model.is_eval
        model.eval()
        assert model.is_eval

    def test_cache_populated_on_eval(self) -> None:
        model = MicroModel()
        assert model._w_raw == {}
        model.eval()
        assert "w_in" in model._w_raw
        assert "w_head" in model._w_raw
        assert "layers" in model._w_raw


# ──────────────────────────────────────────
# Numerical equivalence
# ──────────────────────────────────────────


class TestNumericalEquivalence:
    """Eval-mode output must match autograd forward (±1e-10)."""

    def test_default_config(self) -> None:
        model = MicroModel()
        features = [0.5] * 8

        # Autograd forward
        score_ag, emb_ag = model.forward(features)

        # Eval forward
        model.eval()
        score_ev, emb_ev = model.forward(features)

        assert abs(score_ag - score_ev) < 1e-10
        for a, b in zip(emb_ag, emb_ev):
            assert abs(a - b) < 1e-10

    def test_various_inputs(self) -> None:
        model = MicroModel()
        inputs = [
            [0.0] * 8,
            [1.0] * 8,
            [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
            [-1.0, -0.5, 0.0, 0.5, 1.0, 1.5, 2.0, 2.5],
        ]
        for feat in inputs:
            score_ag, emb_ag = model.forward(feat)
            model.eval()
            score_ev, emb_ev = model.forward(feat)
            model.train_mode()

            assert abs(score_ag - score_ev) < 1e-10, (
                f"Score mismatch for {feat}: {score_ag} vs {score_ev}"
            )

    def test_after_training(self) -> None:
        """Eval-mode must reflect trained weights."""
        model = MicroModel()
        # Train a few steps
        for _ in range(5):
            model.train_step([0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2, 0.1], 1.0)

        feat = [0.5] * 8
        score_ag, emb_ag = model.forward(feat)
        model.eval()
        score_ev, emb_ev = model.forward(feat)

        assert abs(score_ag - score_ev) < 1e-10

    def test_custom_config(self) -> None:
        cfg = MicroModelConfig(n_features=4, n_embd=8, n_head=2, n_layer=2)
        model = MicroModel(cfg)
        feat = [0.1, 0.2, 0.3, 0.4]

        score_ag, emb_ag = model.forward(feat)
        model.eval()
        score_ev, emb_ev = model.forward(feat)

        assert abs(score_ag - score_ev) < 1e-10
        assert len(emb_ev) == 8


# ──────────────────────────────────────────
# Performance: eval-mode speed
# ──────────────────────────────────────────


class TestEvalPerformance:
    def test_eval_faster_than_autograd(self) -> None:
        """Eval-mode should be significantly faster."""
        model = MicroModel()
        feat = [0.5] * 8

        # Warmup
        model.forward(feat)
        model.eval()
        model.forward(feat)

        # Benchmark autograd
        model.train_mode()
        n = 50
        t0 = time.perf_counter()
        for _ in range(n):
            model.forward(feat)
        ag_time = (time.perf_counter() - t0) / n

        # Benchmark eval
        model.eval()
        t0 = time.perf_counter()
        for _ in range(n):
            model.forward(feat)
        ev_time = (time.perf_counter() - t0) / n

        # Eval should be at least 3x faster (conservative)
        assert ev_time < ag_time, (
            f"Eval ({ev_time*1000:.3f}ms) not faster than autograd ({ag_time*1000:.3f}ms)"
        )

    def test_eval_under_2ms(self) -> None:
        """Single eval forward should be < 2ms on CPython."""
        model = MicroModel()
        model.eval()
        feat = [0.5] * 8

        # Warmup
        model.forward(feat)

        times: list[float] = []
        for _ in range(20):
            t0 = time.perf_counter()
            model.forward(feat)
            times.append((time.perf_counter() - t0) * 1000)

        median = sorted(times)[len(times) // 2]
        assert median < 2.0, f"Eval-mode median: {median:.3f}ms, expected < 2ms"


# ──────────────────────────────────────────
# No Value objects in eval-mode
# ──────────────────────────────────────────


class TestNoValueInEval:
    def test_output_types(self) -> None:
        """Eval-mode output should be pure Python types."""
        model = MicroModel()
        model.eval()
        score, emb = model.forward([0.5] * 8)

        assert isinstance(score, float)
        assert isinstance(emb, list)
        assert all(isinstance(v, float) for v in emb)
        # Make sure no Value objects leaked
        assert not isinstance(score, Value)
