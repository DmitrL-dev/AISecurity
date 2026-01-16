"""Evaluation module - benchmarks, metrics, evaluation framework."""

from rlm_toolkit.evaluation.framework import (
    Evaluator,
    EvalResult,
    EvalTask,
    Benchmark,
)
from rlm_toolkit.evaluation.metrics import (
    Metric,
    ExactMatch,
    SemanticSimilarity,
    CostEffectiveness,
)
from rlm_toolkit.evaluation.benchmarks import (
    OOLONGBenchmark,
    CIRCLEBenchmark,
)

__all__ = [
    "Evaluator",
    "EvalResult",
    "EvalTask",
    "Benchmark",
    "Metric",
    "ExactMatch",
    "SemanticSimilarity",
    "CostEffectiveness",
    "OOLONGBenchmark",
    "CIRCLEBenchmark",
]
