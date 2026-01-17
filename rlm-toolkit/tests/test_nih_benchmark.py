"""
Tests for Needle-In-a-Haystack Benchmark
"""
import pytest
from rlm_toolkit.evaluation.nih_benchmark import (
    NeedleInHaystackBenchmark,
    NIHResult,
    NIHBenchmarkReport,
)


class TestNIHBenchmark:
    """Tests for NIH benchmark infrastructure."""
    
    def test_secret_generation(self):
        """Test secret code generation."""
        bench = NeedleInHaystackBenchmark(seed=42)
        secret1 = bench._generate_secret()
        secret2 = bench._generate_secret()
        
        assert len(secret1) == 8
        assert len(secret2) == 8
        assert secret1 != secret2  # Different secrets
        
        # Reproducibility
        bench2 = NeedleInHaystackBenchmark(seed=42)
        assert bench2._generate_secret() == NeedleInHaystackBenchmark(seed=42)._generate_secret()
    
    def test_haystack_generation(self):
        """Test filler text generation."""
        bench = NeedleInHaystackBenchmark()
        
        haystack = bench._generate_haystack(1000)
        assert len(haystack) == 1000
        
        haystack_large = bench._generate_haystack(10000)
        assert len(haystack_large) == 10000
    
    def test_context_creation_positions(self):
        """Test needle placement at different positions."""
        bench = NeedleInHaystackBenchmark(seed=42)
        
        # Start position
        ctx_start, secret_start = bench._create_context(10000, 0.0)
        assert secret_start in ctx_start
        assert ctx_start.find(secret_start) < 1000  # Near start
        
        # Middle position
        bench2 = NeedleInHaystackBenchmark(seed=43)  # Fresh seed
        ctx_mid, secret_mid = bench2._create_context(10000, 0.5)
        assert secret_mid in ctx_mid
        mid_pos = ctx_mid.find(secret_mid)
        assert 4000 < mid_pos < 6000  # Near middle
        
        # End position
        bench3 = NeedleInHaystackBenchmark(seed=44)
        ctx_end, secret_end = bench3._create_context(10000, 1.0)
        assert secret_end in ctx_end
        end_pos = ctx_end.find(secret_end)
        assert end_pos > 8000  # Near end
    
    def test_context_size(self):
        """Test context size is approximately correct."""
        bench = NeedleInHaystackBenchmark()
        
        for target_size in [1000, 10000, 100000]:
            ctx, _ = bench._create_context(target_size, 0.5)
            # Allow 5% tolerance
            assert abs(len(ctx) - target_size) < target_size * 0.05
    
    def test_nih_result_accuracy(self):
        """Test NIHResult accuracy calculation."""
        result_found = NIHResult(
            context_size=10000,
            estimated_tokens=2500,
            needle_position=0.5,
            found=True,
            retrieved_answer="ABC123",
            expected_answer="ABC123",
            latency_seconds=1.0,
        )
        assert result_found.accuracy == 1.0
        
        result_not_found = NIHResult(
            context_size=10000,
            estimated_tokens=2500,
            needle_position=0.5,
            found=False,
            retrieved_answer="wrong",
            expected_answer="ABC123",
            latency_seconds=1.0,
        )
        assert result_not_found.accuracy == 0.0


class MockRetriever:
    """Mock retriever that always returns the needle."""
    
    def __init__(self, find_needle: bool = True):
        self.find_needle = find_needle
        self.last_context = None
        self.last_question = None
    
    def retrieve(self, context: str, question: str) -> str:
        self.last_context = context
        self.last_question = question
        
        if self.find_needle:
            # Extract secret from context
            import re
            match = re.search(r'secret code is: ([A-Z0-9]+)', context)
            if match:
                return f"The secret code is {match.group(1)}"
        return "I don't know the secret code."


class TestNIHBenchmarkWithMock:
    """Integration tests with mock retriever."""
    
    def test_run_single_success(self):
        """Test single successful retrieval."""
        bench = NeedleInHaystackBenchmark(seed=42)
        retriever = MockRetriever(find_needle=True)
        
        result = bench.run_single(retriever, context_size=10000, needle_position=0.5)
        
        assert result.found
        assert result.accuracy == 1.0
        assert result.context_size > 9000
        assert 0 < result.latency_seconds < 10
    
    def test_run_single_failure(self):
        """Test single failed retrieval."""
        bench = NeedleInHaystackBenchmark(seed=42)
        retriever = MockRetriever(find_needle=False)
        
        result = bench.run_single(retriever, context_size=10000, needle_position=0.5)
        
        assert not result.found
        assert result.accuracy == 0.0
    
    def test_run_full_benchmark(self):
        """Test full benchmark run."""
        bench = NeedleInHaystackBenchmark(seed=42)
        retriever = MockRetriever(find_needle=True)
        
        report = bench.run(
            retriever,
            context_sizes=[1000, 5000],
            positions=[0.0, 0.5, 1.0],
            verbose=False,
        )
        
        assert report.total_tests == 6  # 2 sizes * 3 positions
        assert report.passed_tests == 6
        assert report.accuracy == 1.0
        assert len(report.results) == 6
    
    def test_run_partial_success(self):
        """Test benchmark with partial success rate."""
        bench = NeedleInHaystackBenchmark(seed=42)
        
        class PartialRetriever:
            """Retriever that fails at end positions."""
            def __init__(self):
                self.call_count = 0
            
            def retrieve(self, context: str, question: str) -> str:
                self.call_count += 1
                # Fail every 3rd call
                if self.call_count % 3 == 0:
                    return "Unknown"
                import re
                match = re.search(r'secret code is: ([A-Z0-9]+)', context)
                if match:
                    return f"The secret code is {match.group(1)}"
                return "Unknown"
        
        retriever = PartialRetriever()
        
        report = bench.run(
            retriever,
            context_sizes=[1000],
            positions=[0.0, 0.5, 1.0],
            verbose=False,
        )
        
        assert report.total_tests == 3
        assert report.passed_tests == 2  # 2/3 success
        assert 0.6 < report.accuracy < 0.7


@pytest.mark.skip(reason="Requires infini-retri package and model download")
class TestNIHBenchmarkReal:
    """Real benchmark tests - require infini-retri installed."""
    
    def test_real_infiniretri_small(self):
        """Test real InfiniRetri on small context."""
        from rlm_toolkit.evaluation.nih_benchmark import run_infiniretri_benchmark
        
        report = run_infiniretri_benchmark(
            context_sizes=[10000],  # 2.5K tokens
            verbose=True,
        )
        
        assert report.accuracy > 0.8  # Allow some error
