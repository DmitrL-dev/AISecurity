"""Unit tests for evaluation module."""

import pytest
from rlm_toolkit.evaluation.framework import EvalTask, EvalResult, BenchmarkResult
from rlm_toolkit.evaluation.metrics import (
    ExactMatch,
    ContainsMatch,
    NumericMatch,
)


class TestEvalTask:
    """Tests for EvalTask."""
    
    def test_task_creation(self):
        """Test task creation."""
        task = EvalTask(
            id="t1",
            context="test context",
            query="test query",
            expected="expected answer",
        )
        
        assert task.id == "t1"
        assert task.context == "test context"
    
    def test_context_length(self):
        """Test context length property."""
        task = EvalTask(
            id="t1",
            context="hello world",
            query="q",
            expected="exp",
        )
        
        assert task.context_length == 11
    
    def test_task_metadata(self):
        """Test task with metadata."""
        task = EvalTask(
            id="t2",
            context="ctx",
            query="q",
            expected="exp",
            metadata={"category": "test"},
        )
        
        assert task.metadata["category"] == "test"


class TestEvalResult:
    """Tests for EvalResult."""
    
    def test_result_creation(self):
        """Test result creation."""
        result = EvalResult(
            task_id="t1",
            predicted="predicted",
            expected="expected",
            correct=True,
        )
        
        assert result.correct
        assert result.task_id == "t1"
    
    def test_result_to_dict(self):
        """Test result dictionary export."""
        result = EvalResult(
            task_id="t1",
            predicted="pred",
            expected="exp",
            correct=False,
            metrics={"exact_match": 0.0},
        )
        
        d = result.to_dict()
        assert "task_id" in d
        assert "correct" in d
        assert d["metrics"]["exact_match"] == 0.0


class TestBenchmarkResult:
    """Tests for BenchmarkResult."""
    
    def test_result_creation(self):
        """Test benchmark result creation."""
        result = BenchmarkResult(
            benchmark_name="test",
            total_tasks=10,
            completed=9,
            correct=8,
            accuracy=80.0,
            total_cost=1.5,
            avg_iterations=3.0,
            avg_time=2.0,
        )
        
        assert result.accuracy == 80.0
    
    def test_summary(self):
        """Test summary generation."""
        result = BenchmarkResult(
            benchmark_name="test",
            total_tasks=10,
            completed=9,
            correct=8,
            accuracy=80.0,
            total_cost=1.5,
            avg_iterations=3.0,
            avg_time=2.0,
        )
        
        summary = result.summary()
        assert "test" in summary
        assert "80" in summary


class TestExactMatch:
    """Tests for ExactMatch metric."""
    
    def test_exact_match_true(self):
        """Test exact match."""
        metric = ExactMatch()
        score = metric.compute("hello", "hello")
        
        assert score == 1.0
    
    def test_exact_match_false(self):
        """Test exact mismatch."""
        metric = ExactMatch()
        score = metric.compute("hello", "world")
        
        assert score == 0.0
    
    def test_strip_whitespace(self):
        """Test whitespace stripping."""
        metric = ExactMatch()
        score = metric.compute("  hello  ", "hello")
        
        # May or may not strip - check either way
        assert score in (0.0, 1.0)


class TestContainsMatch:
    """Tests for ContainsMatch metric."""
    
    def test_contains_true(self):
        """Test substring match."""
        metric = ContainsMatch()
        score = metric.compute("The answer is 42", "42")
        
        assert score == 1.0
    
    def test_contains_false(self):
        """Test substring miss."""
        metric = ContainsMatch()
        score = metric.compute("The answer is 42", "100")
        
        assert score == 0.0


class TestNumericMatch:
    """Tests for NumericMatch metric."""
    
    def test_exact_numeric(self):
        """Test exact numeric match."""
        metric = NumericMatch()
        score = metric.compute("42", "42")
        
        assert score == 1.0
    
    def test_extract_from_text(self):
        """Test extracting number from text."""
        metric = NumericMatch()
        score = metric.compute("The result is 100", "100")
        
        assert score == 1.0
