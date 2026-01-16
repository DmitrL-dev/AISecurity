"""
Evaluation Framework
====================

Core evaluation infrastructure for RLM benchmarking.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from rlm_toolkit.core.engine import RLM


@dataclass
class EvalTask:
    """Single evaluation task.
    
    Attributes:
        id: Unique task identifier
        context: Input context
        query: Query to evaluate
        expected: Expected answer (ground truth)
        metadata: Additional task metadata
    """
    id: str
    context: str
    query: str
    expected: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def context_length(self) -> int:
        return len(self.context)


@dataclass
class EvalResult:
    """Result of evaluating a single task.
    
    Attributes:
        task_id: Task identifier
        predicted: Model's predicted answer
        expected: Ground truth answer
        correct: Whether answer is correct
        metrics: Metric scores
        cost: Cost in USD
        iterations: Number of REPL iterations
        execution_time: Time in seconds
        error: Error message if failed
    """
    task_id: str
    predicted: Optional[str]
    expected: str
    correct: bool
    metrics: Dict[str, float] = field(default_factory=dict)
    cost: float = 0.0
    iterations: int = 0
    execution_time: float = 0.0
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'task_id': self.task_id,
            'predicted': self.predicted,
            'expected': self.expected,
            'correct': self.correct,
            'metrics': self.metrics,
            'cost': self.cost,
            'iterations': self.iterations,
            'execution_time': self.execution_time,
            'error': self.error,
        }


@dataclass
class BenchmarkResult:
    """Aggregated benchmark results.
    
    Attributes:
        benchmark_name: Name of benchmark
        total_tasks: Number of tasks
        completed: Successfully completed tasks
        correct: Number correct
        accuracy: Accuracy percentage
        total_cost: Total cost in USD
        avg_iterations: Average iterations per task
        avg_time: Average time per task
        results: Individual task results
    """
    benchmark_name: str
    total_tasks: int
    completed: int
    correct: int
    accuracy: float
    total_cost: float
    avg_iterations: float
    avg_time: float
    results: List[EvalResult] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        return (
            f"Benchmark: {self.benchmark_name}\n"
            f"Tasks: {self.total_tasks}\n"
            f"Completed: {self.completed} ({self.completed/self.total_tasks*100:.1f}%)\n"
            f"Correct: {self.correct} ({self.accuracy:.1f}%)\n"
            f"Total Cost: ${self.total_cost:.4f}\n"
            f"Avg Iterations: {self.avg_iterations:.1f}\n"
            f"Avg Time: {self.avg_time:.2f}s"
        )


class Benchmark(ABC):
    """Abstract benchmark definition.
    
    Subclasses implement specific benchmarks like OOLONG, CIRCLE.
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Benchmark name."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Benchmark description."""
        pass
    
    @abstractmethod
    def load_tasks(self) -> List[EvalTask]:
        """Load evaluation tasks."""
        pass
    
    @abstractmethod
    def evaluate_answer(self, predicted: str, expected: str) -> bool:
        """Evaluate if answer is correct."""
        pass


class Evaluator:
    """Evaluation engine for running benchmarks.
    
    Example:
        >>> evaluator = Evaluator(rlm)
        >>> result = evaluator.run(OOLONGBenchmark())
        >>> print(result.summary())
    """
    
    def __init__(
        self,
        rlm: "RLM",
        metrics: Optional[List["Metric"]] = None,
    ):
        """Initialize evaluator.
        
        Args:
            rlm: RLM instance to evaluate
            metrics: List of metrics to compute
        """
        self.rlm = rlm
        self.metrics = metrics or []
    
    def evaluate_task(self, task: EvalTask, benchmark: Benchmark) -> EvalResult:
        """Evaluate single task."""
        try:
            result = self.rlm.run(task.context, task.query)
            
            predicted = result.answer
            correct = benchmark.evaluate_answer(predicted or "", task.expected)
            
            # Compute metrics
            metric_scores = {}
            for metric in self.metrics:
                try:
                    score = metric.compute(predicted or "", task.expected)
                    metric_scores[metric.name] = score
                except Exception:
                    metric_scores[metric.name] = 0.0
            
            return EvalResult(
                task_id=task.id,
                predicted=predicted,
                expected=task.expected,
                correct=correct,
                metrics=metric_scores,
                cost=result.total_cost,
                iterations=result.iterations,
                execution_time=result.execution_time,
            )
        
        except Exception as e:
            return EvalResult(
                task_id=task.id,
                predicted=None,
                expected=task.expected,
                correct=False,
                error=str(e),
            )
    
    def run(
        self,
        benchmark: Benchmark,
        max_tasks: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> BenchmarkResult:
        """Run full benchmark evaluation.
        
        Args:
            benchmark: Benchmark to run
            max_tasks: Limit number of tasks (for testing)
            progress_callback: Called with (completed, total) after each task
        
        Returns:
            BenchmarkResult with aggregated results
        """
        tasks = benchmark.load_tasks()
        
        if max_tasks:
            tasks = tasks[:max_tasks]
        
        results: List[EvalResult] = []
        
        for i, task in enumerate(tasks):
            result = self.evaluate_task(task, benchmark)
            results.append(result)
            
            if progress_callback:
                progress_callback(i + 1, len(tasks))
        
        # Aggregate
        completed = [r for r in results if r.error is None]
        correct = [r for r in completed if r.correct]
        
        total_cost = sum(r.cost for r in results)
        total_iterations = sum(r.iterations for r in results)
        total_time = sum(r.execution_time for r in results)
        
        return BenchmarkResult(
            benchmark_name=benchmark.name,
            total_tasks=len(tasks),
            completed=len(completed),
            correct=len(correct),
            accuracy=len(correct) / len(tasks) * 100 if tasks else 0,
            total_cost=total_cost,
            avg_iterations=total_iterations / len(tasks) if tasks else 0,
            avg_time=total_time / len(tasks) if tasks else 0,
            results=results,
        )
