"""Unit tests for exporters module."""

import pytest
from unittest.mock import MagicMock, patch
import time

from rlm_toolkit.observability.tracer import Tracer, Span
from rlm_toolkit.observability.exporters import (
    BaseExporter,
    ConsoleExporter,
    LangfuseExporter,
    LangSmithExporter,
    BufferedExporter,
    CompositeExporter,
)


class MockExporter(BaseExporter):
    """Mock exporter for testing."""
    
    def __init__(self):
        self.exported_spans = []
        self.flush_count = 0
        self.shutdown_count = 0
    
    def export_span(self, span):
        self.exported_spans.append(span)
    
    def flush(self):
        self.flush_count += 1
    
    def shutdown(self):
        self.shutdown_count += 1


class TestConsoleExporter:
    """Tests for ConsoleExporter."""
    
    def test_export_pretty(self, capsys):
        """Test pretty format export."""
        exporter = ConsoleExporter(pretty=True)
        
        span = Span(
            trace_id="abc",
            span_id="def",
            parent_id=None,
            name="test-span",
            start_time=time.time(),
        )
        span.set_attribute("key", "value")
        span.end()
        
        exporter.export_span(span)
        
        captured = capsys.readouterr()
        assert "test-span" in captured.out
        assert "key" in captured.out
    
    def test_export_json(self, capsys):
        """Test JSON format export."""
        exporter = ConsoleExporter(pretty=False)
        
        span = Span(
            trace_id="abc",
            span_id="def",
            parent_id=None,
            name="test-span",
            start_time=time.time(),
        )
        span.end()
        
        exporter.export_span(span)
        
        captured = capsys.readouterr()
        assert "trace_id" in captured.out
        assert "abc" in captured.out


class TestLangfuseExporter:
    """Tests for LangfuseExporter."""
    
    def test_init_no_keys(self):
        """Test init without keys."""
        exporter = LangfuseExporter()
        
        # Should not fail, just won't export
        assert exporter.public_key is None or exporter.public_key == ""
    
    def test_export_skipped_without_keys(self):
        """Test export is skipped without API keys."""
        exporter = LangfuseExporter(public_key=None, secret_key=None)
        
        span = _create_test_span()
        
        # Should not raise
        exporter.export_span(span)
    
    def test_flush_no_client(self):
        """Test flush with no client."""
        exporter = LangfuseExporter()
        
        # Should not raise
        exporter.flush()


class TestLangSmithExporter:
    """Tests for LangSmithExporter."""
    
    def test_init_no_key(self):
        """Test init without key."""
        exporter = LangSmithExporter()
        
        # API key from env or None
        assert exporter.project == "rlm-toolkit"
    
    def test_export_skipped_without_key(self):
        """Test export is skipped without API key."""
        exporter = LangSmithExporter(api_key=None)
        exporter.api_key = None  # Force no key
        
        span = _create_test_span()
        
        # Should not raise
        exporter.export_span(span)


class TestBufferedExporter:
    """Tests for BufferedExporter."""
    
    def test_buffer_accumulates(self):
        """Test spans are buffered."""
        mock = MockExporter()
        buffered = BufferedExporter(mock, max_buffer=5)
        
        for _ in range(4):
            buffered.export_span(_create_test_span())
        
        # Not flushed yet
        assert len(mock.exported_spans) == 0
    
    def test_buffer_auto_flush(self):
        """Test auto-flush at max buffer."""
        mock = MockExporter()
        buffered = BufferedExporter(mock, max_buffer=3)
        
        for _ in range(5):
            buffered.export_span(_create_test_span())
        
        # Should have flushed at least once
        assert len(mock.exported_spans) >= 3
    
    def test_manual_flush(self):
        """Test manual flush."""
        mock = MockExporter()
        buffered = BufferedExporter(mock, max_buffer=100)
        
        buffered.export_span(_create_test_span())
        buffered.export_span(_create_test_span())
        buffered.flush()
        
        assert len(mock.exported_spans) == 2
        assert mock.flush_count == 1
    
    def test_shutdown_flushes(self):
        """Test shutdown flushes and shuts down inner."""
        mock = MockExporter()
        buffered = BufferedExporter(mock, max_buffer=100)
        
        buffered.export_span(_create_test_span())
        buffered.shutdown()
        
        assert len(mock.exported_spans) == 1
        assert mock.shutdown_count == 1


class TestCompositeExporter:
    """Tests for CompositeExporter."""
    
    def test_exports_to_all(self):
        """Test export to all backends."""
        mock1 = MockExporter()
        mock2 = MockExporter()
        composite = CompositeExporter([mock1, mock2])
        
        composite.export_span(_create_test_span())
        
        assert len(mock1.exported_spans) == 1
        assert len(mock2.exported_spans) == 1
    
    def test_flushes_all(self):
        """Test flush all backends."""
        mock1 = MockExporter()
        mock2 = MockExporter()
        composite = CompositeExporter([mock1, mock2])
        
        composite.flush()
        
        assert mock1.flush_count == 1
        assert mock2.flush_count == 1
    
    def test_shutdowns_all(self):
        """Test shutdown all backends."""
        mock1 = MockExporter()
        mock2 = MockExporter()
        composite = CompositeExporter([mock1, mock2])
        
        composite.shutdown()
        
        assert mock1.shutdown_count == 1
        assert mock2.shutdown_count == 1
    
    def test_continues_on_error(self):
        """Test continues if one exporter fails."""
        mock1 = MockExporter()
        mock2 = MockExporter()
        
        # Make mock1 raise
        mock1.export_span = MagicMock(side_effect=Exception("Test error"))
        
        composite = CompositeExporter([mock1, mock2])
        composite.export_span(_create_test_span())
        
        # mock2 should still receive
        assert len(mock2.exported_spans) == 1


def _create_test_span() -> Span:
    """Create a test span."""
    span = Span(
        trace_id="test-trace",
        span_id="test-span",
        parent_id=None,
        name="test",
        start_time=time.time(),
    )
    span.end()
    return span
