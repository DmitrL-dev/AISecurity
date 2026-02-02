"""
Cost Tracker
============

Track and report LLM costs per run, provider, model.
Includes latency percentiles and token efficiency metrics (v2.5).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime
import statistics


@dataclass
class CostEntry:
    """Single cost entry."""
    timestamp: datetime
    provider: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: float
    is_subcall: bool = False
    trace_id: Optional[str] = None
    # v2.5: Latency tracking
    latency_ms: Optional[float] = None


@dataclass
class CostReport:
    """Cost report for a time period or run.

    Attributes:
        total_cost: Total cost in USD
        total_tokens: Total tokens used
        by_provider: Cost breakdown by provider
        by_model: Cost breakdown by model
        entries: Individual cost entries
    """
    total_cost: float = 0.0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    by_provider: Dict[str, float] = field(default_factory=dict)
    by_model: Dict[str, float] = field(default_factory=dict)
    entries: List[CostEntry] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.total_tokens_in + self.total_tokens_out

    def add_entry(self, entry: CostEntry) -> None:
        """Add cost entry."""
        self.entries.append(entry)
        self.total_cost += entry.cost_usd
        self.total_tokens_in += entry.tokens_in
        self.total_tokens_out += entry.tokens_out

        # Update by_provider
        self.by_provider[entry.provider] = (
            self.by_provider.get(entry.provider, 0.0) + entry.cost_usd
        )

        # Update by_model
        self.by_model[entry.model] = (
            self.by_model.get(entry.model, 0.0) + entry.cost_usd
        )

    # --- v2.5: Latency Percentiles ---

    def latency_percentiles(self) -> Dict[str, Optional[float]]:
        """Get latency percentiles (p50, p90, p99).

        Returns:
            Dict with p50, p90, p99 latency in ms
        """
        latencies = [
            e.latency_ms for e in self.entries if e.latency_ms is not None]

        if not latencies:
            return {"p50": None, "p90": None, "p99": None, "mean": None}

        latencies_sorted = sorted(latencies)
        n = len(latencies_sorted)

        def percentile(p: float) -> float:
            idx = (n - 1) * p / 100
            lower = int(idx)
            upper = min(lower + 1, n - 1)
            weight = idx - lower
            return latencies_sorted[lower] * (1 - weight) + latencies_sorted[upper] * weight

        return {
            "p50": round(percentile(50), 2),
            "p90": round(percentile(90), 2),
            "p99": round(percentile(99), 2),
            "mean": round(statistics.mean(latencies), 2),
        }

    # --- v2.5: Compression Ratio ---

    def compression_ratio(self) -> Optional[float]:
        """Calculate token efficiency (output/input ratio).

        A lower ratio means more concise outputs.
        Returns None if no input tokens.

        Returns:
            Output tokens / Input tokens ratio
        """
        if self.total_tokens_in == 0:
            return None
        return round(self.total_tokens_out / self.total_tokens_in, 3)

    def tokens_per_dollar(self) -> Optional[float]:
        """Calculate tokens per dollar spent.

        Returns:
            Total tokens / cost, or None if no cost
        """
        if self.total_cost == 0:
            return None
        return round(self.total_tokens / self.total_cost, 2)

    def to_dict(self) -> Dict:
        """Export to dictionary."""
        return {
            'total_cost_usd': round(self.total_cost, 6),
            'total_tokens_in': self.total_tokens_in,
            'total_tokens_out': self.total_tokens_out,
            'by_provider': {k: round(v, 6) for k, v in self.by_provider.items()},
            'by_model': {k: round(v, 6) for k, v in self.by_model.items()},
            'entry_count': len(self.entries),
            # v2.5: Extended metrics
            'latency_percentiles': self.latency_percentiles(),
            'compression_ratio': self.compression_ratio(),
            'tokens_per_dollar': self.tokens_per_dollar(),
        }

    def summary(self) -> str:
        """Generate human-readable summary."""
        lines = [
            f"Total Cost: ${self.total_cost:.4f}",
            f"Total Tokens: {self.total_tokens:,} ({self.total_tokens_in:,} in, {self.total_tokens_out:,} out)",
            "",
            "By Provider:",
        ]
        for provider, cost in sorted(self.by_provider.items(), key=lambda x: -x[1]):
            lines.append(f"  {provider}: ${cost:.4f}")

        lines.append("")
        lines.append("By Model:")
        for model, cost in sorted(self.by_model.items(), key=lambda x: -x[1]):
            lines.append(f"  {model}: ${cost:.4f}")

        # v2.5: Add latency stats
        latency = self.latency_percentiles()
        if latency["p50"] is not None:
            lines.append("")
            lines.append("Latency:")
            lines.append(
                f"  p50: {latency['p50']}ms | p90: {latency['p90']}ms | p99: {latency['p99']}ms")

        # v2.5: Add efficiency
        ratio = self.compression_ratio()
        if ratio is not None:
            lines.append("")
            lines.append(f"Compression Ratio: {ratio:.3f} (output/input)")

        return "\n".join(lines)


class CostTracker:
    """Track costs across RLM runs.

    Example:
        >>> tracker = CostTracker()
        >>> tracker.record("openai", "gpt-5.2", 1000, 500, 0.025, latency_ms=450)
        >>> print(tracker.get_report().summary())
    """

    def __init__(self, budget_usd: Optional[float] = None):
        """Initialize tracker.

        Args:
            budget_usd: Optional budget limit
        """
        self.budget_usd = budget_usd
        self._current_report = CostReport()
        self._all_entries: List[CostEntry] = []

    def record(
        self,
        provider: str,
        model: str,
        tokens_in: int,
        tokens_out: int,
        cost_usd: float,
        is_subcall: bool = False,
        trace_id: Optional[str] = None,
        latency_ms: Optional[float] = None,  # v2.5
    ) -> None:
        """Record a cost entry.

        Args:
            provider: Provider name (e.g., "openai")
            model: Model name
            tokens_in: Input tokens
            tokens_out: Output tokens
            cost_usd: Cost in USD
            is_subcall: Whether this is a sub-call
            trace_id: Associated trace ID
            latency_ms: Response latency in milliseconds (v2.5)
        """
        entry = CostEntry(
            timestamp=datetime.now(),
            provider=provider,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            cost_usd=cost_usd,
            is_subcall=is_subcall,
            trace_id=trace_id,
            latency_ms=latency_ms,
        )

        self._current_report.add_entry(entry)
        self._all_entries.append(entry)

    def get_report(self) -> CostReport:
        """Get current cost report."""
        return self._current_report

    def reset(self) -> CostReport:
        """Reset current report and return it."""
        report = self._current_report
        self._current_report = CostReport()
        return report

    @property
    def total_cost(self) -> float:
        """Current total cost."""
        return self._current_report.total_cost

    @property
    def is_over_budget(self) -> bool:
        """Check if over budget."""
        if self.budget_usd is None:
            return False
        return self.total_cost > self.budget_usd

    @property
    def budget_remaining(self) -> Optional[float]:
        """Remaining budget."""
        if self.budget_usd is None:
            return None
        return max(0, self.budget_usd - self.total_cost)

    def get_all_time_report(self) -> CostReport:
        """Get report for all recorded entries."""
        report = CostReport()
        for entry in self._all_entries:
            report.add_entry(entry)
        return report
