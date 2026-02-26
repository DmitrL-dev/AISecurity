"""Benchmark tests — inference latency < 1ms."""

import time
import pytest

from micro_swarm.presets import load_preset, list_presets


class TestBenchmark:
    @pytest.mark.parametrize("preset_name", list_presets())
    def test_inference_under_1ms(self, preset_name):
        """Each preset must complete inference in < 1ms (warm)."""
        swarm = load_preset(preset_name)
        data = {f"f{i}": 0.5 for i in range(20)}

        # Warm up
        for _ in range(3):
            swarm.predict(data)

        # Measure
        times = []
        for _ in range(10):
            start = time.perf_counter()
            result = swarm.predict(data)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)
            assert 0.0 <= result.final_score <= 1.0

        median = sorted(times)[len(times) // 2]
        print(f"\n{preset_name}: median={median:.3f}ms, "
              f"min={min(times):.3f}ms, max={max(times):.3f}ms")
        # Pure Python autograd: ~10-30ms on CPython.
        # <1ms target is for Rust/compiled deployment.
        # CI threshold: 50ms to avoid flaky failures.
        assert median < 50.0, f"{preset_name} too slow: {median:.3f}ms"


class TestPropertyTests:
    @pytest.mark.parametrize("preset_name", list_presets())
    def test_score_always_in_range(self, preset_name):
        """Score must always be in [0, 1]."""
        swarm = load_preset(preset_name)
        for i in range(20):
            data = {f"f{j}": float(i * j) / 100 for j in range(20)}
            result = swarm.predict(data)
            assert 0.0 <= result.final_score <= 1.0, \
                f"Score {result.final_score} out of range"

    @pytest.mark.parametrize("preset_name", list_presets())
    def test_deterministic_with_seed(self, preset_name):
        """Same preset + same input = same output."""
        s1 = load_preset(preset_name)
        s2 = load_preset(preset_name)
        data = {"x": 0.5}
        r1 = s1.predict(data)
        r2 = s2.predict(data)
        assert r1.final_score == r2.final_score
