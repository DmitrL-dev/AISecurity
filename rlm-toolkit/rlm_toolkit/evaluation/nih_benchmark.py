"""
Needle-In-a-Haystack Benchmark for InfiniRetri
==============================================

Tests InfiniRetri's ability to retrieve specific information
("needle") from very large contexts ("haystack").

Based on the original NIH test methodology.
Target: 100% accuracy up to 1M+ tokens.
"""

import time
import random
import string
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class NIHResult:
    """Result of a single Needle-In-a-Haystack test."""
    context_size: int  # in chars
    estimated_tokens: int
    needle_position: float  # 0.0 = start, 1.0 = end
    found: bool
    retrieved_answer: str
    expected_answer: str
    latency_seconds: float
    
    @property
    def accuracy(self) -> float:
        """1.0 if needle found exactly, 0.0 otherwise."""
        return 1.0 if self.found else 0.0


@dataclass
class NIHBenchmarkReport:
    """Full benchmark report."""
    total_tests: int
    passed_tests: int
    accuracy: float
    results: List[NIHResult] = field(default_factory=list)
    avg_latency: float = 0.0
    
    def summary(self) -> str:
        """Generate human-readable summary."""
        return f"""
Needle-In-a-Haystack Benchmark Results
======================================
Total Tests: {self.total_tests}
Passed: {self.passed_tests}
Accuracy: {self.accuracy*100:.1f}%
Avg Latency: {self.avg_latency:.2f}s

By Context Size:
"""


class NeedleInHaystackBenchmark:
    """
    Benchmark for testing retrieval accuracy on large contexts.
    
    The test places a unique "needle" (secret phrase) at various
    positions within a large "haystack" (filler text), then asks
    the model to retrieve it.
    
    Example:
        >>> bench = NeedleInHaystackBenchmark()
        >>> report = bench.run(retriever, context_sizes=[100_000, 500_000, 1_000_000])
        >>> print(report.accuracy)
        1.0
    """
    
    # Default needle template
    NEEDLE_TEMPLATE = "The secret code is: {secret}"
    
    # Question to ask
    QUESTION = "What is the secret code mentioned in the document?"
    
    # Filler text patterns (generic lorem-ipsum style)
    FILLER_SENTENCES = [
        "The quarterly report showed significant growth in all major regions.",
        "According to the latest research, climate patterns are shifting rapidly.",
        "The committee will reconvene next Tuesday to discuss the proposal.",
        "Market analysts predict continued volatility in the coming months.",
        "The new policy framework aims to address emerging challenges.",
        "Historical data suggests a correlation between these variables.",
        "The project timeline was adjusted to accommodate new requirements.",
        "Stakeholder feedback has been incorporated into the final design.",
        "Regulatory compliance remains a top priority for the organization.",
        "The technology roadmap outlines key milestones for the next year.",
    ]
    
    def __init__(
        self,
        needle_template: Optional[str] = None,
        question: Optional[str] = None,
        seed: int = 42,
    ):
        """
        Initialize benchmark.
        
        Args:
            needle_template: Template for needle with {secret} placeholder
            question: Question to ask about the needle
            seed: Random seed for reproducibility
        """
        self.needle_template = needle_template or self.NEEDLE_TEMPLATE
        self.question = question or self.QUESTION
        self.rng = random.Random(seed)
    
    def _generate_secret(self, length: int = 8) -> str:
        """Generate unique secret code."""
        chars = string.ascii_uppercase + string.digits
        return ''.join(self.rng.choices(chars, k=length))
    
    def _generate_haystack(self, target_chars: int) -> str:
        """Generate filler text of approximately target size."""
        sentences = []
        current_len = 0
        
        while current_len < target_chars:
            sentence = self.rng.choice(self.FILLER_SENTENCES)
            sentences.append(sentence)
            current_len += len(sentence) + 1  # +1 for space
        
        return " ".join(sentences)[:target_chars]
    
    def _create_context(
        self,
        context_size: int,
        needle_position: float,
    ) -> Tuple[str, str]:
        """
        Create context with needle at specified position.
        
        Args:
            context_size: Target size in characters
            needle_position: 0.0 = start, 0.5 = middle, 1.0 = end
            
        Returns:
            (full_context, expected_secret)
        """
        secret = self._generate_secret()
        needle = self.needle_template.format(secret=secret)
        
        # Calculate position
        needle_len = len(needle)
        text_before_len = int((context_size - needle_len) * needle_position)
        text_after_len = context_size - needle_len - text_before_len
        
        # Generate filler
        text_before = self._generate_haystack(text_before_len)
        text_after = self._generate_haystack(text_after_len)
        
        # Combine
        context = f"{text_before} {needle} {text_after}"
        
        return context, secret
    
    def run_single(
        self,
        retriever,
        context_size: int,
        needle_position: float,
    ) -> NIHResult:
        """
        Run a single NIH test.
        
        Args:
            retriever: InfiniRetriever instance
            context_size: Target context size in chars
            needle_position: Position of needle (0.0-1.0)
            
        Returns:
            NIHResult with test details
        """
        # Create context
        context, expected_secret = self._create_context(context_size, needle_position)
        
        # Run retrieval
        start_time = time.perf_counter()
        try:
            retrieved = retriever.retrieve(context=context, question=self.question)
        except Exception as e:
            retrieved = f"ERROR: {e}"
        latency = time.perf_counter() - start_time
        
        # Check if secret found
        found = expected_secret in retrieved
        
        return NIHResult(
            context_size=len(context),
            estimated_tokens=len(context) // 4,
            needle_position=needle_position,
            found=found,
            retrieved_answer=retrieved[:200],
            expected_answer=expected_secret,
            latency_seconds=latency,
        )
    
    def run(
        self,
        retriever,
        context_sizes: List[int] = None,
        positions: List[float] = None,
        verbose: bool = True,
    ) -> NIHBenchmarkReport:
        """
        Run full benchmark suite.
        
        Args:
            retriever: InfiniRetriever instance
            context_sizes: List of context sizes to test (chars)
            positions: List of needle positions to test (0.0-1.0)
            verbose: Print progress
            
        Returns:
            NIHBenchmarkReport with all results
        """
        # Defaults
        if context_sizes is None:
            context_sizes = [
                10_000,      # 2.5K tokens
                50_000,      # 12.5K tokens
                100_000,     # 25K tokens
                500_000,     # 125K tokens
                1_000_000,   # 250K tokens
            ]
        
        if positions is None:
            positions = [0.0, 0.25, 0.5, 0.75, 1.0]
        
        results = []
        total_tests = len(context_sizes) * len(positions)
        
        if verbose:
            print(f"Running {total_tests} tests...")
        
        for size in context_sizes:
            for pos in positions:
                if verbose:
                    print(f"  Testing {size//1000}K chars @ position {pos:.2f}...", end=" ")
                
                result = self.run_single(retriever, size, pos)
                results.append(result)
                
                if verbose:
                    status = "✓" if result.found else "✗"
                    print(f"{status} ({result.latency_seconds:.2f}s)")
        
        # Compile report
        passed = sum(1 for r in results if r.found)
        accuracy = passed / len(results) if results else 0.0
        avg_latency = sum(r.latency_seconds for r in results) / len(results) if results else 0.0
        
        return NIHBenchmarkReport(
            total_tests=len(results),
            passed_tests=passed,
            accuracy=accuracy,
            results=results,
            avg_latency=avg_latency,
        )


def run_infiniretri_benchmark(
    model: str = "Qwen/Qwen2.5-0.5B-Instruct",
    context_sizes: List[int] = None,
    verbose: bool = True,
) -> NIHBenchmarkReport:
    """
    Convenience function to run NIH benchmark on InfiniRetri.
    
    Args:
        model: Model to use for InfiniRetri
        context_sizes: Sizes to test (default: 10K to 1M)
        verbose: Print progress
        
    Returns:
        NIHBenchmarkReport
    """
    from rlm_toolkit.retrieval import InfiniRetriever, INFINIRETRI_AVAILABLE
    
    if not INFINIRETRI_AVAILABLE:
        raise ImportError(
            "infini-retri not installed. Run: pip install infini-retri"
        )
    
    retriever = InfiniRetriever(model_name_or_path=model)
    benchmark = NeedleInHaystackBenchmark()
    
    return benchmark.run(retriever, context_sizes=context_sizes, verbose=verbose)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run NIH benchmark on InfiniRetri")
    parser.add_argument("--model", default="Qwen/Qwen2.5-0.5B-Instruct", help="Model to use")
    parser.add_argument("--sizes", nargs="+", type=int, default=[10000, 50000, 100000],
                        help="Context sizes to test")
    args = parser.parse_args()
    
    print("=" * 50)
    print("Needle-In-a-Haystack Benchmark for InfiniRetri")
    print("=" * 50)
    print()
    
    try:
        report = run_infiniretri_benchmark(
            model=args.model,
            context_sizes=args.sizes,
            verbose=True,
        )
        
        print()
        print("=" * 50)
        print(f"FINAL ACCURACY: {report.accuracy * 100:.1f}%")
        print(f"PASSED: {report.passed_tests}/{report.total_tests}")
        print(f"AVG LATENCY: {report.avg_latency:.2f}s")
        print("=" * 50)
        
    except ImportError as e:
        print(f"ERROR: {e}")
        print("Install infini-retri first: pip install infini-retri")
