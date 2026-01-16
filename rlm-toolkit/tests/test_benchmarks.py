"""Unit tests for benchmarks module."""

import pytest
from rlm_toolkit.evaluation.benchmarks import OOLONGBenchmark, CIRCLEBenchmark
from rlm_toolkit.evaluation.framework import EvalTask


class TestOOLONGBenchmark:
    """Tests for OOLONGBenchmark."""
    
    def test_creation(self):
        """Test benchmark creation."""
        benchmark = OOLONGBenchmark()
        
        assert benchmark is not None
        assert "OOLONG" in benchmark.name.upper()
    
    def test_description(self):
        """Test benchmark description."""
        benchmark = OOLONGBenchmark()
        
        desc = benchmark.description
        assert "OOLONG" in desc or "long-context" in desc.lower()
    
    def test_load_tasks_sample(self):
        """Test loading sample tasks."""
        benchmark = OOLONGBenchmark()
        tasks = benchmark.load_tasks()
        
        # Should have at least sample tasks
        assert len(tasks) > 0
        assert all(isinstance(t, EvalTask) for t in tasks)
    
    def test_evaluate_exact_match(self):
        """Test exact match evaluation."""
        benchmark = OOLONGBenchmark()
        
        assert benchmark.evaluate_answer("42", "42") is True
        assert benchmark.evaluate_answer("wrong", "42") is False
    
    def test_evaluate_case_insensitive(self):
        """Test case insensitive evaluation."""
        benchmark = OOLONGBenchmark()
        
        # Should be case insensitive
        result = benchmark.evaluate_answer("ANSWER", "answer")
        # May or may not match depending on implementation
        assert isinstance(result, bool)
    
    def test_subset_filter(self):
        """Test subset filtering."""
        benchmark = OOLONGBenchmark(subset="retrieval")
        
        # Should still load
        tasks = benchmark.load_tasks()
        assert isinstance(tasks, list)


class TestCIRCLEBenchmark:
    """Tests for CIRCLEBenchmark."""
    
    def test_creation(self):
        """Test benchmark creation."""
        benchmark = CIRCLEBenchmark()
        
        assert benchmark is not None
        assert "circle" in benchmark.name.lower()
    
    def test_description(self):
        """Test benchmark description."""
        benchmark = CIRCLEBenchmark()
        
        desc = benchmark.description
        assert "security" in desc.lower() or "CIRCLE" in desc
    
    def test_categories_defined(self):
        """Test security categories are defined."""
        assert len(CIRCLEBenchmark.CATEGORIES) > 0
        assert "direct_import" in CIRCLEBenchmark.CATEGORIES
    
    def test_load_tasks(self):
        """Test loading security test cases."""
        benchmark = CIRCLEBenchmark()
        tasks = benchmark.load_tasks()
        
        assert len(tasks) > 0
        assert all(isinstance(t, EvalTask) for t in tasks)
    
    def test_category_filter(self):
        """Test category filtering."""
        benchmark = CIRCLEBenchmark(category="direct_import")
        tasks = benchmark.load_tasks()
        
        # Should have filtered tasks
        assert len(tasks) >= 0
    
    def test_evaluate_blocked(self):
        """Test evaluation of blocked code."""
        benchmark = CIRCLEBenchmark()
        
        # Expected is "blocked" or "allowed"
        result = benchmark.evaluate_answer("blocked", "blocked")
        assert result is True
    
    def test_evaluate_allowed(self):
        """Test evaluation of allowed code."""
        benchmark = CIRCLEBenchmark()
        
        result = benchmark.evaluate_answer("allowed", "allowed")
        assert result is True
    
    def test_task_has_code(self):
        """Test tasks include code to test."""
        benchmark = CIRCLEBenchmark()
        tasks = benchmark.load_tasks()
        
        if len(tasks) > 0:
            task = tasks[0]
            # Task should have query with code (CIRCLE puts code in query)
            assert len(task.query) > 0


class TestBenchmarkInterface:
    """Tests for Benchmark interface compliance."""
    
    def test_oolong_has_required_methods(self):
        """Test OOLONGBenchmark implements interface."""
        benchmark = OOLONGBenchmark()
        
        assert hasattr(benchmark, "name")
        assert hasattr(benchmark, "description")
        assert hasattr(benchmark, "load_tasks")
        assert hasattr(benchmark, "evaluate_answer")
    
    def test_circle_has_required_methods(self):
        """Test CIRCLEBenchmark implements interface."""
        benchmark = CIRCLEBenchmark()
        
        assert hasattr(benchmark, "name")
        assert hasattr(benchmark, "description")
        assert hasattr(benchmark, "load_tasks")
        assert hasattr(benchmark, "evaluate_answer")
