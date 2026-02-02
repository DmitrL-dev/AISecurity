"""
Tests for Cost Tracker v2.5 Observability Metrics.
"""

import pytest
from datetime import datetime

from rlm_toolkit.observability.cost_tracker import (
    CostTracker,
    CostEntry,
    CostReport,
)


class TestCostEntryV25:
    """Tests for CostEntry with latency_ms."""

    def test_latency_ms_field(self):
        """CostEntry should support latency_ms."""
        entry = CostEntry(
            timestamp=datetime.now(),
            provider="openai",
            model="gpt-5",
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.01,
            latency_ms=450.5,
        )

        assert entry.latency_ms == 450.5


class TestLatencyPercentiles:
    """Tests for latency_percentiles() method."""

    def test_empty_report(self):
        """Empty report should return None for all percentiles."""
        report = CostReport()
        percentiles = report.latency_percentiles()

        assert percentiles["p50"] is None
        assert percentiles["p90"] is None
        assert percentiles["p99"] is None
        assert percentiles["mean"] is None

    def test_single_entry(self):
        """Single entry should return same value for all percentiles."""
        report = CostReport()
        report.add_entry(CostEntry(
            timestamp=datetime.now(),
            provider="openai",
            model="gpt-5",
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.01,
            latency_ms=500,
        ))

        percentiles = report.latency_percentiles()

        assert percentiles["p50"] == 500
        assert percentiles["mean"] == 500

    def test_multiple_entries(self):
        """Multiple entries should calculate correct percentiles."""
        report = CostReport()

        # Add 10 entries with latencies 100-1000ms
        for i in range(1, 11):
            report.add_entry(CostEntry(
                timestamp=datetime.now(),
                provider="openai",
                model="gpt-5",
                tokens_in=100,
                tokens_out=50,
                cost_usd=0.01,
                latency_ms=i * 100,  # 100, 200, ..., 1000
            ))

        percentiles = report.latency_percentiles()

        # p50 should be around 500-550
        assert 500 <= percentiles["p50"] <= 600
        # p90 should be high
        assert percentiles["p90"] >= 900
        # Mean should be 550
        assert percentiles["mean"] == 550

    def test_entries_without_latency_ignored(self):
        """Entries without latency should be ignored."""
        report = CostReport()

        # One with latency
        report.add_entry(CostEntry(
            timestamp=datetime.now(),
            provider="openai",
            model="gpt-5",
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.01,
            latency_ms=500,
        ))

        # One without
        report.add_entry(CostEntry(
            timestamp=datetime.now(),
            provider="openai",
            model="gpt-5",
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.01,
            latency_ms=None,
        ))

        percentiles = report.latency_percentiles()

        assert percentiles["mean"] == 500


class TestCompressionRatio:
    """Tests for compression_ratio() method."""

    def test_empty_report(self):
        """Empty report should return None."""
        report = CostReport()
        assert report.compression_ratio() is None

    def test_basic_ratio(self):
        """Basic ratio calculation."""
        report = CostReport()
        report.add_entry(CostEntry(
            timestamp=datetime.now(),
            provider="openai",
            model="gpt-5",
            tokens_in=1000,
            tokens_out=500,
            cost_usd=0.01,
        ))

        # 500 / 1000 = 0.5
        assert report.compression_ratio() == 0.5

    def test_verbose_output(self):
        """Verbose output should have ratio > 1."""
        report = CostReport()
        report.add_entry(CostEntry(
            timestamp=datetime.now(),
            provider="openai",
            model="gpt-5",
            tokens_in=100,
            tokens_out=500,
            cost_usd=0.01,
        ))

        # 500 / 100 = 5.0
        assert report.compression_ratio() == 5.0


class TestTokensPerDollar:
    """Tests for tokens_per_dollar() method."""

    def test_empty_report(self):
        """Empty report should return None."""
        report = CostReport()
        assert report.tokens_per_dollar() is None

    def test_calculation(self):
        """Should calculate tokens per dollar."""
        report = CostReport()
        report.add_entry(CostEntry(
            timestamp=datetime.now(),
            provider="openai",
            model="gpt-5",
            tokens_in=10000,
            tokens_out=5000,
            cost_usd=0.10,
        ))

        # 15000 / 0.10 = 150000
        assert report.tokens_per_dollar() == 150000.0


class TestCostTrackerV25:
    """Tests for CostTracker with v2.5 metrics."""

    def test_record_with_latency(self):
        """record() should accept latency_ms."""
        tracker = CostTracker()

        tracker.record(
            provider="openai",
            model="gpt-5",
            tokens_in=100,
            tokens_out=50,
            cost_usd=0.01,
            latency_ms=450,
        )

        report = tracker.get_report()
        percentiles = report.latency_percentiles()

        assert percentiles["p50"] == 450

    def test_to_dict_includes_v25_metrics(self):
        """to_dict() should include v2.5 metrics."""
        tracker = CostTracker()

        tracker.record(
            provider="openai",
            model="gpt-5",
            tokens_in=1000,
            tokens_out=500,
            cost_usd=0.10,
            latency_ms=450,
        )

        data = tracker.get_report().to_dict()

        assert "latency_percentiles" in data
        assert "compression_ratio" in data
        assert "tokens_per_dollar" in data
        assert data["compression_ratio"] == 0.5

    def test_summary_includes_latency(self):
        """summary() should include latency stats."""
        tracker = CostTracker()

        tracker.record(
            provider="openai",
            model="gpt-5",
            tokens_in=1000,
            tokens_out=500,
            cost_usd=0.10,
            latency_ms=450,
        )

        summary = tracker.get_report().summary()

        assert "Latency:" in summary
        assert "p50:" in summary
        assert "Compression Ratio:" in summary
