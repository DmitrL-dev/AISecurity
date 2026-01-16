"""Tests for evaluation framework module."""

import pytest
from unittest.mock import MagicMock

from rlm_toolkit.evaluation.framework import (
    EvalTask,
    EvalResult,
    BenchmarkResult,
    Benchmark,
    Evaluator,
)
from rlm_toolkit.testing.mocks import MockProvider
from rlm_toolkit.core.engine import RLM


class TestEvalTask:
    """Tests for EvalTask."""
    
    def test_creation(self):
        """Test task creation."""
        task = EvalTask(
            id="task-001",
            context="Test context",
            query="What is the answer?",
            expected="42",
        )
        
        assert task.id == "task-001"
        assert task.expected == "42"
    
    def test_context_length(self):
        """Test context_length property."""
        task = EvalTask(
            id="t1",
            context="Hello world",
            query="q",
            expected="e",
        )
        
        assert task.context_length == 11
    
    def test_metadata(self):
        """Test task metadata."""
        task = EvalTask(
            id="t1",
            context="c",
            query="q",
            expected="e",
            metadata={"category": "test"},
        )
        
        assert task.metadata["category"] == "test"


class TestEvalResult:
    """Tests for EvalResult."""
    
    def test_creation(self):
        """Test result creation."""
        result = EvalResult(
            task_id="t1",
            predicted="42",
            expected="42",
            correct=True,
        )
        
        assert result.task_id == "t1"
        assert result.correct is True
    
    def test_with_metrics(self):
        """Test result with metrics."""
        result = EvalResult(
            task_id="t1",
            predicted="42",
            expected="42",
            correct=True,
            metrics={"exact_match": 1.0},
        )
        
        assert result.metrics["exact_match"] == 1.0
    
    def test_with_error(self):
        """Test result with error."""
        result = EvalResult(
            task_id="t1",
            predicted=None,
            expected="42",
            correct=False,
            error="Timeout",
        )
        
        assert result.error == "Timeout"
        assert result.predicted is None
    
    def test_to_dict(self):
        """Test result serialization."""
        result = EvalResult(
            task_id="t1",
            predicted="answer",
            expected="answer",
            correct=True,
        )
        
        data = result.to_dict()
        
        assert data["task_id"] == "t1"
        assert data["correct"] is True


class TestBenchmarkResult:
    """Tests for BenchmarkResult."""
    
    def test_creation(self):
        """Test result creation."""
        result = BenchmarkResult(
            benchmark_name="test-benchmark",
            total_tasks=100,
            completed=95,
            correct=80,
            accuracy=80.0,
            total_cost=1.5,
            avg_iterations=3.2,
            avg_time=2.1,
        )
        
        assert result.benchmark_name == "test-benchmark"
        assert result.accuracy == 80.0
    
    def test_summary(self):
        """Test summary generation."""
        result = BenchmarkResult(
            benchmark_name="test",
            total_tasks=10,
            completed=10,
            correct=8,
            accuracy=80.0,
            total_cost=0.5,
            avg_iterations=2.0,
            avg_time=1.5,
        )
        
        summary = result.summary()
        
        assert "test" in summary
        assert "80" in summary


class MockBenchmark(Benchmark):
    """Mock benchmark for testing."""
    
    @property
    def name(self):
        return "mock-benchmark"
    
    @property
    def description(self):
        return "Test benchmark"
    
    def load_tasks(self):
        return [
            EvalTask(id="t1", context="c1", query="q1", expected="42"),
            EvalTask(id="t2", context="c2", query="q2", expected="hello"),
        ]
    
    def evaluate_answer(self, predicted, expected):
        return predicted.strip().lower() == expected.strip().lower()


class TestEvaluator:
    """Tests for Evaluator."""
    
    def test_creation(self):
        """Test evaluator creation."""
        provider = MockProvider(responses=["FINAL(42)"])
        rlm = RLM(root=provider)
        
        evaluator = Evaluator(rlm)
        
        assert evaluator.rlm is rlm
    
    def test_evaluate_task(self):
        """Test evaluating single task."""
        provider = MockProvider(responses=["FINAL(42)"])
        rlm = RLM(root=provider)
        evaluator = Evaluator(rlm)
        
        task = EvalTask(id="t1", context="c", query="q", expected="42")
        benchmark = MockBenchmark()
        
        result = evaluator.evaluate_task(task, benchmark)
        
        assert result.task_id == "t1"
        assert result.predicted is not None
    
    def test_run_benchmark(self):
        """Test running full benchmark."""
        provider = MockProvider(responses=["FINAL(42)"])
        rlm = RLM(root=provider)
        evaluator = Evaluator(rlm)
        
        benchmark = MockBenchmark()
        
        result = evaluator.run(benchmark)
        
        assert result.benchmark_name == "mock-benchmark"
        assert result.total_tasks == 2
    
    def test_run_with_max_tasks(self):
        """Test run with max_tasks limit."""
        provider = MockProvider(responses=["FINAL(42)"])
        rlm = RLM(root=provider)
        evaluator = Evaluator(rlm)
        
        benchmark = MockBenchmark()
        
        result = evaluator.run(benchmark, max_tasks=1)
        
        assert len(result.results) == 1
    
    def test_run_with_progress_callback(self):
        """Test run with progress callback."""
        provider = MockProvider(responses=["FINAL(42)"])
        rlm = RLM(root=provider)
        evaluator = Evaluator(rlm)
        
        benchmark = MockBenchmark()
        progress_calls = []
        
        def callback(done, total):
            progress_calls.append((done, total))
        
        evaluator.run(benchmark, progress_callback=callback)
        
        assert len(progress_calls) == 2
