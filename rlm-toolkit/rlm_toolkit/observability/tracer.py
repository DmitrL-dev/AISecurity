"""
Tracer
======

OpenTelemetry-compatible tracing for RLM execution (ADR-004).
"""

from __future__ import annotations

import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from rlm_toolkit.observability.exporters import BaseExporter


@dataclass
class Span:
    """A trace span representing a unit of work.
    
    Attributes:
        trace_id: Root trace identifier
        span_id: This span's identifier
        parent_id: Parent span identifier (None for root)
        name: Span name
        start_time: Start timestamp (Unix seconds)
        end_time: End timestamp (None if still running)
        attributes: Key-value metadata
        events: List of events within span
        status: 'ok', 'error', or None
    """
    trace_id: str
    span_id: str
    parent_id: Optional[str]
    name: str
    start_time: float
    end_time: Optional[float] = None
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    status: Optional[str] = None
    
    @property
    def duration_ms(self) -> Optional[float]:
        """Duration in milliseconds."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time) * 1000
        return None
    
    def set_attribute(self, key: str, value: Any) -> None:
        """Set span attribute."""
        self.attributes[key] = value
    
    def add_event(self, name: str, attributes: Optional[Dict] = None) -> None:
        """Add event to span."""
        self.events.append({
            'name': name,
            'timestamp': time.time(),
            'attributes': attributes or {},
        })
    
    def set_status(self, status: str, message: Optional[str] = None) -> None:
        """Set span status."""
        self.status = status
        if message:
            self.attributes['status_message'] = message
    
    def end(self) -> None:
        """Mark span as ended."""
        self.end_time = time.time()
    
    def to_dict(self) -> Dict[str, Any]:
        """Export to dictionary."""
        return {
            'trace_id': self.trace_id,
            'span_id': self.span_id,
            'parent_id': self.parent_id,
            'name': self.name,
            'start_time': self.start_time,
            'end_time': self.end_time,
            'duration_ms': self.duration_ms,
            'attributes': self.attributes,
            'events': self.events,
            'status': self.status,
        }


class Tracer:
    """OpenTelemetry-compatible tracer.
    
    Provides distributed tracing for RLM execution.
    
    Example:
        >>> tracer = Tracer(name="rlm-toolkit")
        >>> with tracer.start_span("run") as span:
        ...     span.set_attribute("context_length", 1000000)
        ...     # do work
        >>> tracer.export()
    
    Attributes:
        name: Tracer/service name
        spans: List of completed spans
        exporters: List of exporters
    """
    
    def __init__(
        self,
        name: str = "rlm-toolkit",
        exporters: Optional[List["BaseExporter"]] = None,
    ):
        """Initialize tracer.
        
        Args:
            name: Service/tracer name
            exporters: List of exporters for span data
        """
        self.name = name
        self.exporters = exporters or []
        self.spans: List[Span] = []
        self._current_trace_id: Optional[str] = None
        self._span_stack: List[Span] = []
    
    def _generate_id(self) -> str:
        """Generate unique ID."""
        return uuid.uuid4().hex[:16]
    
    @contextmanager
    def start_span(self, name: str, attributes: Optional[Dict] = None):
        """Start a new span.
        
        Args:
            name: Span name
            attributes: Initial attributes
        
        Yields:
            Span object
        """
        # Create trace ID if this is root span
        if not self._current_trace_id:
            self._current_trace_id = self._generate_id()
        
        # Get parent ID from stack
        parent_id = self._span_stack[-1].span_id if self._span_stack else None
        
        # Create span
        span = Span(
            trace_id=self._current_trace_id,
            span_id=self._generate_id(),
            parent_id=parent_id,
            name=name,
            start_time=time.time(),
            attributes=attributes or {},
        )
        
        self._span_stack.append(span)
        
        try:
            yield span
            if span.status is None:
                span.set_status('ok')
        except Exception as e:
            span.set_status('error', str(e))
            raise
        finally:
            span.end()
            self._span_stack.pop()
            self.spans.append(span)
            
            # Export span
            for exporter in self.exporters:
                try:
                    exporter.export_span(span)
                except Exception:
                    pass  # Don't let exporters break execution
            
            # Clear trace ID if root span ended
            if not self._span_stack:
                self._current_trace_id = None
    
    def start_as_current_span(self, name: str, **kwargs):
        """Decorator for tracing functions."""
        def decorator(func):
            def wrapper(*args, **kw):
                with self.start_span(name, **kwargs) as span:
                    return func(*args, **kw)
            return wrapper
        return decorator
    
    @property
    def current_span(self) -> Optional[Span]:
        """Get current span."""
        return self._span_stack[-1] if self._span_stack else None
    
    @property
    def current_trace_id(self) -> Optional[str]:
        """Get current trace ID."""
        return self._current_trace_id
    
    def export(self) -> List[Dict]:
        """Export all spans to dictionaries."""
        return [span.to_dict() for span in self.spans]
    
    def clear(self) -> None:
        """Clear collected spans."""
        self.spans.clear()
    
    def add_exporter(self, exporter: "BaseExporter") -> None:
        """Add an exporter."""
        self.exporters.append(exporter)


def create_tracer(
    name: str = "rlm-toolkit",
    console: bool = False,
    langfuse: bool = False,
    langsmith: bool = False,
) -> Tracer:
    """Factory function to create tracer with exporters.
    
    Args:
        name: Service name
        console: Enable console exporter
        langfuse: Enable Langfuse exporter
        langsmith: Enable LangSmith exporter
    
    Returns:
        Configured Tracer instance
    """
    from rlm_toolkit.observability.exporters import (
        ConsoleExporter,
        LangfuseExporter,
        LangSmithExporter,
    )
    
    exporters = []
    
    if console:
        exporters.append(ConsoleExporter())
    if langfuse:
        exporters.append(LangfuseExporter())
    if langsmith:
        exporters.append(LangSmithExporter())
    
    return Tracer(name=name, exporters=exporters)
