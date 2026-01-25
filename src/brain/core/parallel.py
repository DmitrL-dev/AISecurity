"""
Parallel Engine Execution Module — SENTINEL GPU Acceleration

Provides utilities for running multiple engines concurrently:
- asyncio-based parallel execution
- ThreadPoolExecutor for CPU-bound engines
- GPU stream management for CUDA engines

Author: SENTINEL Team
Date: 2025-12-16
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass
import time

logger = logging.getLogger("ParallelEngine")


@dataclass
class EngineResult:
    """Result from an engine execution."""

    engine_name: str
    result: Any
    latency_ms: float
    success: bool
    error: Optional[str] = None


class ParallelExecutor:
    """
    Executes multiple engines in parallel.

    Architecture:
    - IO-bound engines: asyncio concurrency
    - CPU-bound engines: ThreadPoolExecutor
    - GPU engines: Sequential (share CUDA context)
    """

    def __init__(
        self,
        max_workers: int = 4,
        timeout_seconds: float = 10.0,
    ):
        self.max_workers = max_workers
        self.timeout = timeout_seconds
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._stats = {
            "total_runs": 0,
            "parallel_speedup_sum": 0.0,
        }

    async def run_parallel(
        self,
        engines: Dict[str, Callable],
        input_data: Any,
    ) -> Dict[str, EngineResult]:
        """
        Run multiple engines in parallel.

        Args:
            engines: Dict of engine_name -> callable
            input_data: Input to pass to each engine

        Returns:
            Dict of engine_name -> EngineResult
        """
        start = time.time()
        results = {}

        # Create tasks for each engine
        tasks = []
        for name, engine_fn in engines.items():
            task = self._run_engine_async(name, engine_fn, input_data)
            tasks.append((name, task))

        # Run all tasks concurrently
        try:
            awaited = await asyncio.gather(
                *[t[1] for t in tasks],
                return_exceptions=True
            )

            for (name, _), result in zip(tasks, awaited):
                if isinstance(result, Exception):
                    results[name] = EngineResult(
                        engine_name=name,
                        result=None,
                        latency_ms=0,
                        success=False,
                        error=str(result),
                    )
                else:
                    results[name] = result

        except asyncio.TimeoutError:
            logger.error(f"Parallel execution timeout after {self.timeout}s")

        total_time = (time.time() - start) * 1000

        # Calculate speedup
        sequential_time = sum(r.latency_ms for r in results.values())
        if total_time > 0:
            speedup = sequential_time / total_time
            self._stats["total_runs"] += 1
            self._stats["parallel_speedup_sum"] += speedup
            logger.debug(f"Parallel speedup: {speedup:.2f}x")

        return results

    async def _run_engine_async(
        self,
        name: str,
        engine_fn: Callable,
        input_data: Any,
    ) -> EngineResult:
        """Run a single engine asynchronously."""
        start = time.time()

        try:
            # Check if engine is async
            if asyncio.iscoroutinefunction(engine_fn):
                result = await asyncio.wait_for(
                    engine_fn(input_data),
                    timeout=self.timeout
                )
            else:
                # Run sync function in thread pool
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        self._executor,
                        engine_fn,
                        input_data
                    ),
                    timeout=self.timeout
                )

            latency = (time.time() - start) * 1000

            return EngineResult(
                engine_name=name,
                result=result,
                latency_ms=latency,
                success=True,
            )

        except asyncio.TimeoutError:
            return EngineResult(
                engine_name=name,
                result=None,
                latency_ms=(time.time() - start) * 1000,
                success=False,
                error="Timeout",
            )
        except Exception as e:
            return EngineResult(
                engine_name=name,
                result=None,
                latency_ms=(time.time() - start) * 1000,
                success=False,
                error=str(e),
            )

    def run_parallel_sync(
        self,
        engines: Dict[str, Callable],
        input_data: Any,
    ) -> Dict[str, EngineResult]:
        """Synchronous wrapper for parallel execution."""
        return asyncio.run(self.run_parallel(engines, input_data))

    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics."""
        avg_speedup = 0.0
        if self._stats["total_runs"] > 0:
            avg_speedup = self._stats["parallel_speedup_sum"] / \
                self._stats["total_runs"]

        return {
            "total_runs": self._stats["total_runs"],
            "average_speedup": avg_speedup,
            "max_workers": self.max_workers,
        }

    def shutdown(self):
        """Shutdown the executor."""
        self._executor.shutdown(wait=True)


# ============================================================================
# Independent Engine Groups
# ============================================================================

# Engines that can safely run in parallel (no shared state)
PARALLEL_ENGINE_GROUPS = {
    "fast_checks": [
        "language_engine",
        "injection_engine",
        "query_engine",
        "yara_engine",
    ],
    "ml_engines": [
        "qwen_guard",
        "pii_engine",
    ],
    "analysis_engines": [
        "geometric_kernel",  # TDA
        "info_theory",
        "chaos_engine",
    ],
}


def get_parallel_groups() -> Dict[str, List[str]]:
    """Get engine groups that can run in parallel."""
    return PARALLEL_ENGINE_GROUPS


# ============================================================================
# INT8 Quantization Helpers
# ============================================================================

def load_quantized_model(
    model_name: str,
    quantization: str = "int8",
) -> Any:
    """
    Load a HuggingFace model with quantization.

    Args:
        model_name: HuggingFace model name
        quantization: "int8" or "int4"

    Returns:
        Quantized model ready for inference
    """
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        import torch
    except ImportError:
        logger.error("transformers or torch not available")
        return None

    # Check for bitsandbytes
    try:
        import bitsandbytes
        HAS_BNB = True
    except ImportError:
        HAS_BNB = False
        logger.warning("bitsandbytes not available, using float16")

    load_kwargs = {
        "device_map": "auto",
        "trust_remote_code": True,
    }

    if HAS_BNB and quantization == "int8":
        load_kwargs["load_in_8bit"] = True
        logger.info(f"Loading {model_name} with INT8 quantization")
    elif HAS_BNB and quantization == "int4":
        load_kwargs["load_in_4bit"] = True
        logger.info(f"Loading {model_name} with INT4 quantization")
    else:
        load_kwargs["torch_dtype"] = torch.float16
        logger.info(f"Loading {model_name} with float16")

    try:
        model = AutoModelForCausalLM.from_pretrained(model_name, **load_kwargs)
        return model
    except Exception as e:
        logger.error(f"Failed to load quantized model: {e}")
        return None


def estimate_memory_savings(
    original_size_gb: float,
    quantization: str = "int8",
) -> Dict[str, float]:
    """
    Estimate memory savings from quantization.

    Args:
        original_size_gb: Model size in GB (float32)
        quantization: "int8" or "int4"

    Returns:
        Dict with memory estimates
    """
    if quantization == "int8":
        factor = 4.0  # float32 (4 bytes) -> int8 (1 byte)
    elif quantization == "int4":
        factor = 8.0  # float32 (4 bytes) -> int4 (0.5 bytes)
    else:
        factor = 2.0  # float32 -> float16

    quantized_size = original_size_gb / factor

    return {
        "original_size_gb": original_size_gb,
        "quantized_size_gb": quantized_size,
        "savings_gb": original_size_gb - quantized_size,
        "savings_percent": (1 - 1/factor) * 100,
        "quantization": quantization,
    }


# ============================================================================
# Factory
# ============================================================================

_default_executor: Optional[ParallelExecutor] = None


def get_parallel_executor() -> ParallelExecutor:
    """Get or create the default parallel executor."""
    global _default_executor
    if _default_executor is None:
        _default_executor = ParallelExecutor()
    return _default_executor
