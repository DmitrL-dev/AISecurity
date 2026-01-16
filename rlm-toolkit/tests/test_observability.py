"""Unit tests for observability module."""

import pytest
import time
from rlm_toolkit.observability.tracer import Tracer, Span
from rlm_toolkit.observability.cost_tracker import CostTracker, CostEntry, CostReport
from rlm_toolkit.observability.exporters import ConsoleExporter


class TestTracer:
    """Tests for Tracer."""
    
    def test_create_tracer(self):
        """Test tracer creation."""
        tracer = Tracer(name="test")
        assert tracer.name == "test"
    
    def test_start_span_context_manager(self):
        """Test span as context manager."""
        tracer = Tracer()
        
        with tracer.start_span("my-operation") as span:
            span.set_attribute("key", "value")
        
        assert span.end_time is not None
        assert span.attributes.get("key") == "value"
    
    def test_nested_spans(self):
        """Test nested span creation."""
        tracer = Tracer()
        
        with tracer.start_span("parent") as parent:
            with tracer.start_span("child") as child:
                pass
        
        assert len(tracer.spans) >= 2
    
    def test_span_attributes(self):
        """Test setting span attributes."""
        tracer = Tracer()
        
        with tracer.start_span("test") as span:
            span.set_attribute("model", "gpt-4")
            span.set_attribute("tokens", 100)
        
        assert span.attributes.get("model") == "gpt-4"
        assert span.attributes.get("tokens") == 100
    
    def test_trace_id_generation(self):
        """Test trace ID is generated."""
        tracer = Tracer()
        
        with tracer.start_span("test") as span:
            assert span.trace_id is not None
            assert len(span.trace_id) > 0
    
    def test_span_duration(self):
        """Test span duration calculation."""
        tracer = Tracer()
        
        with tracer.start_span("test") as span:
            time.sleep(0.01)
        
        assert span.duration_ms >= 10
    
    def test_export_spans(self):
        """Test exporting spans."""
        tracer = Tracer()
        
        with tracer.start_span("test"):
            pass
        
        exported = tracer.export()
        assert len(exported) == 1
        assert exported[0]["name"] == "test"
    
    def test_clear_spans(self):
        """Test clearing spans."""
        tracer = Tracer()
        
        with tracer.start_span("test"):
            pass
        
        tracer.clear()
        assert len(tracer.spans) == 0


class TestCostTracker:
    """Tests for CostTracker."""
    
    def test_record_cost(self):
        """Test recording costs."""
        tracker = CostTracker()
        tracker.record("openai", "gpt-4", 100, 50, 0.5)
        
        assert tracker.total_cost == 0.5
    
    def test_budget_check(self):
        """Test budget enforcement."""
        tracker = CostTracker(budget_usd=1.0)
        tracker.record("openai", "gpt-4", 100, 50, 0.5)
        
        assert tracker.budget_remaining == 0.5
        assert not tracker.is_over_budget
    
    def test_over_budget_detection(self):
        """Test over budget detection."""
        tracker = CostTracker(budget_usd=1.0)
        tracker.record("openai", "gpt-4", 100, 50, 1.5)
        
        assert tracker.is_over_budget
    
    def test_cost_by_provider(self):
        """Test cost aggregation by provider."""
        tracker = CostTracker()
        tracker.record("openai", "gpt-4", 100, 50, 0.5)
        tracker.record("openai", "gpt-4", 100, 50, 0.3)
        tracker.record("anthropic", "claude", 100, 50, 0.2)
        
        report = tracker.get_report()
        assert report.by_provider.get("openai") == 0.8
        assert report.by_provider.get("anthropic") == 0.2
    
    def test_reset(self):
        """Test cost reset."""
        tracker = CostTracker()
        tracker.record("openai", "gpt-4", 100, 50, 1.0)
        tracker.reset()
        
        assert tracker.total_cost == 0.0
    
    def test_report_summary(self):
        """Test report summary."""
        tracker = CostTracker()
        tracker.record("openai", "gpt-4", 100, 50, 2.5)
        
        summary = tracker.get_report().summary()
        assert "Total Cost" in summary
        assert "2.5" in summary


class TestCostReport:
    """Tests for CostReport."""
    
    def test_report_creation(self):
        """Test report creation."""
        report = CostReport()
        assert report.total_cost == 0.0
    
    def test_to_dict(self):
        """Test dictionary export."""
        report = CostReport()
        d = report.to_dict()
        
        assert "total_cost_usd" in d
        assert "by_provider" in d


class TestSpan:
    """Tests for Span dataclass."""
    
    def test_span_creation(self):
        """Test span creation."""
        span = Span(
            trace_id="abc123",
            span_id="def456",
            parent_id=None,
            name="test",
            start_time=time.time(),
        )
        
        assert span.name == "test"
        assert span.trace_id == "abc123"
    
    def test_span_to_dict(self):
        """Test span dictionary export."""
        span = Span(
            trace_id="abc",
            span_id="def",
            parent_id=None,
            name="test",
            start_time=time.time(),
        )
        span.end()
        
        d = span.to_dict()
        assert "name" in d
        assert "trace_id" in d
        assert "duration_ms" in d
