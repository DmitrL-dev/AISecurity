"""
RLM-Bench: Quality-Position Test
=================================

Measures context quality degradation based on information position.

Key Insight: Traditional LLMs lose quality at edges of context window.
RLM-Toolkit + InfiniRetri should maintain 100% regardless of position.
"""

import time
from dataclasses import dataclass
from typing import List, Optional, Callable
import json


@dataclass
class PositionTestResult:
    """Result of a single position test."""
    position: str  # "start", "middle", "end", "random"
    position_percent: float  # 0.0 = start, 1.0 = end
    accuracy: float  # 0.0 - 1.0
    latency_ms: float
    context_size_tokens: int
    needle: str
    found: bool
    answer: str


@dataclass 
class QualityPositionReport:
    """Full benchmark report."""
    model: str
    method: str  # "naive", "rlm", "infiniretri"
    results: List[PositionTestResult]
    avg_accuracy: float
    decay_coefficient: float  # λ in Q(c) = Q₀ × e^(-λc)
    positions_tested: int
    total_time_s: float
    
    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "method": self.method,
            "avg_accuracy": self.avg_accuracy,
            "decay_coefficient": self.decay_coefficient,
            "positions_tested": self.positions_tested,
            "total_time_s": self.total_time_s,
            "results": [
                {
                    "position": r.position,
                    "position_percent": r.position_percent,
                    "accuracy": r.accuracy,
                    "found": r.found,
                }
                for r in self.results
            ]
        }


class QualityPositionBench:
    """
    Benchmark for measuring quality decay across context positions.
    
    Needle-in-Haystack style test with position tracking.
    """
    
    # Default needles (facts to find)
    DEFAULT_NEEDLES = [
        ("The secret code is ALPHA-7749.", "What is the secret code?", "ALPHA-7749"),
        ("Project deadline is March 15, 2026.", "What is the project deadline?", "March 15, 2026"),
        ("The CEO's name is Alexandra Chen.", "What is the CEO's name?", "Alexandra Chen"),
        ("Budget allocation is $2.5 million.", "What is the budget allocation?", "$2.5 million"),
        ("Server IP address is 192.168.42.100.", "What is the server IP?", "192.168.42.100"),
    ]
    
    def __init__(
        self,
        generator: Callable[[str, str], str],
        context_generator: Optional[Callable[[int], str]] = None,
    ):
        """
        Args:
            generator: Function(context, query) -> answer
            context_generator: Function(size) -> filler text
        """
        self.generator = generator
        self.context_generator = context_generator or self._default_context
    
    def _default_context(self, size_tokens: int) -> str:
        """Generate filler context (Lorem ipsum style)."""
        base = """
        The quarterly report indicates steady growth across all market segments.
        Team performance metrics show improvement in key areas of development.
        Customer satisfaction scores remain high with positive feedback trends.
        Infrastructure upgrades continue to enhance system reliability.
        Strategic initiatives are progressing according to planned timelines.
        """
        # Repeat to reach target size (~4 chars per token)
        target_chars = size_tokens * 4
        repeated = base * (target_chars // len(base) + 1)
        return repeated[:target_chars]
    
    def _insert_needle(
        self,
        context: str,
        needle: str,
        position_percent: float
    ) -> str:
        """Insert needle at specified position (0.0 = start, 1.0 = end)."""
        insert_pos = int(len(context) * position_percent)
        # Find nearest paragraph break
        for offset in range(100):
            if insert_pos + offset < len(context) and context[insert_pos + offset] == '\n':
                insert_pos += offset
                break
            if insert_pos - offset >= 0 and context[insert_pos - offset] == '\n':
                insert_pos -= offset
                break
        
        return context[:insert_pos] + f"\n\n{needle}\n\n" + context[insert_pos:]
    
    def run_single(
        self,
        needle: str,
        query: str,
        expected: str,
        context_size: int = 100_000,
        position_percent: float = 0.5,
    ) -> PositionTestResult:
        """Run single position test."""
        # Generate context with needle
        filler = self.context_generator(context_size)
        full_context = self._insert_needle(filler, needle, position_percent)
        
        # Time the query
        start = time.perf_counter()
        answer = self.generator(full_context, query)
        latency = (time.perf_counter() - start) * 1000
        
        # Check accuracy
        found = expected.lower() in answer.lower()
        accuracy = 1.0 if found else 0.0
        
        # Determine position label
        if position_percent < 0.2:
            pos_label = "start"
        elif position_percent > 0.8:
            pos_label = "end"
        else:
            pos_label = "middle"
        
        return PositionTestResult(
            position=pos_label,
            position_percent=position_percent,
            accuracy=accuracy,
            latency_ms=latency,
            context_size_tokens=context_size,
            needle=needle,
            found=found,
            answer=answer[:200],
        )
    
    def run_full(
        self,
        context_sizes: List[int] = [10_000, 50_000, 100_000, 500_000],
        positions: List[float] = [0.0, 0.25, 0.5, 0.75, 1.0],
        model_name: str = "unknown",
        method: str = "naive",
    ) -> QualityPositionReport:
        """
        Run full benchmark across sizes and positions.
        """
        results = []
        start_time = time.perf_counter()
        
        for size in context_sizes:
            for pos in positions:
                for needle, query, expected in self.DEFAULT_NEEDLES[:2]:  # 2 needles for speed
                    result = self.run_single(
                        needle=needle,
                        query=query,
                        expected=expected,
                        context_size=size,
                        position_percent=pos,
                    )
                    results.append(result)
                    print(f"  Size={size:,} Pos={pos:.0%} Found={result.found}")
        
        # Calculate metrics
        avg_accuracy = sum(r.accuracy for r in results) / len(results) if results else 0
        
        # Estimate decay coefficient
        # Group by position and calculate average accuracy
        pos_acc = {}
        for r in results:
            pos_acc.setdefault(r.position_percent, []).append(r.accuracy)
        pos_avg = {p: sum(a)/len(a) for p, a in pos_acc.items()}
        
        # Simple decay estimation (difference between start and end)
        start_acc = pos_avg.get(0.0, 1.0)
        end_acc = pos_avg.get(1.0, 1.0)
        decay = max(0, start_acc - end_acc)  # Simplified
        
        return QualityPositionReport(
            model=model_name,
            method=method,
            results=results,
            avg_accuracy=avg_accuracy,
            decay_coefficient=decay,
            positions_tested=len(results),
            total_time_s=time.perf_counter() - start_time,
        )


def run_comparison(rlm_generator, naive_generator, model: str):
    """
    Compare RLM vs Naive approach.
    
    Returns comparison dict.
    """
    print("=" * 50)
    print(f"RLM-Bench: Quality-Position Test")
    print(f"Model: {model}")
    print("=" * 50)
    
    # Run naive
    print("\n[Naive Approach]")
    bench_naive = QualityPositionBench(naive_generator)
    naive_report = bench_naive.run_full(
        context_sizes=[10_000, 50_000],
        positions=[0.0, 0.5, 1.0],
        model_name=model,
        method="naive",
    )
    
    # Run RLM
    print("\n[RLM Approach]")
    bench_rlm = QualityPositionBench(rlm_generator)
    rlm_report = bench_rlm.run_full(
        context_sizes=[10_000, 50_000],
        positions=[0.0, 0.5, 1.0],
        model_name=model,
        method="rlm",
    )
    
    # Comparison
    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)
    print(f"Naive Accuracy: {naive_report.avg_accuracy:.1%}")
    print(f"RLM Accuracy:   {rlm_report.avg_accuracy:.1%}")
    print(f"Improvement:    {(rlm_report.avg_accuracy - naive_report.avg_accuracy):.1%}")
    print(f"Naive Decay:    {naive_report.decay_coefficient:.2f}")
    print(f"RLM Decay:      {rlm_report.decay_coefficient:.2f}")
    
    return {
        "naive": naive_report.to_dict(),
        "rlm": rlm_report.to_dict(),
        "improvement": rlm_report.avg_accuracy - naive_report.avg_accuracy,
    }


if __name__ == "__main__":
    # Demo with mock generators
    def mock_naive(context: str, query: str) -> str:
        # Simulates naive approach - worse at finding things at edges
        import random
        if random.random() < 0.6:
            return "I found the answer in the context."
        return "I could not find the relevant information."
    
    def mock_rlm(context: str, query: str) -> str:
        # Simulates RLM - consistent results
        return "The secret code is ALPHA-7749."
    
    result = run_comparison(mock_rlm, mock_naive, "mock-model")
    print("\nJSON Output:")
    print(json.dumps(result, indent=2))
