"""
Exporters
=========

Export spans to various observability backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TYPE_CHECKING
import json
import sys

if TYPE_CHECKING:
    from rlm_toolkit.observability.tracer import Span


class BaseExporter(ABC):
    """Base class for trace exporters."""
    
    @abstractmethod
    def export_span(self, span: "Span") -> None:
        """Export a single span."""
        pass
    
    def flush(self) -> None:
        """Flush any buffered data."""
        pass
    
    def shutdown(self) -> None:
        """Shutdown exporter."""
        pass


class ConsoleExporter(BaseExporter):
    """Export spans to console/stdout.
    
    Useful for debugging and development.
    """
    
    def __init__(self, pretty: bool = True):
        self.pretty = pretty
    
    def export_span(self, span: "Span") -> None:
        data = span.to_dict()
        
        if self.pretty:
            duration = f"{data['duration_ms']:.1f}ms" if data['duration_ms'] else "?"
            status = data['status'] or 'unknown'
            print(f"[TRACE] {data['name']} | {duration} | {status}")
            if data['attributes']:
                for k, v in data['attributes'].items():
                    print(f"        {k}: {v}")
        else:
            print(json.dumps(data, default=str))


class LangfuseExporter(BaseExporter):
    """Export to Langfuse observability platform.
    
    Requires LANGFUSE_PUBLIC_KEY and LANGFUSE_SECRET_KEY env vars.
    """
    
    def __init__(
        self,
        public_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        host: str = "https://cloud.langfuse.com",
    ):
        import os
        self.public_key = public_key or os.environ.get("LANGFUSE_PUBLIC_KEY")
        self.secret_key = secret_key or os.environ.get("LANGFUSE_SECRET_KEY")
        self.host = host
        self._client = None
        self._buffer = []
    
    def _get_client(self):
        """Lazy load Langfuse client."""
        if self._client is None:
            try:
                from langfuse import Langfuse
                self._client = Langfuse(
                    public_key=self.public_key,
                    secret_key=self.secret_key,
                    host=self.host,
                )
            except ImportError:
                raise ImportError(
                    "langfuse package required. Install with: pip install langfuse"
                )
        return self._client
    
    def export_span(self, span: "Span") -> None:
        """Export span to Langfuse."""
        if not self.public_key or not self.secret_key:
            return  # Skip if not configured
        
        try:
            client = self._get_client()
            
            # Create trace or span
            if span.parent_id is None:
                # Root span = new trace
                client.trace(
                    id=span.trace_id,
                    name=span.name,
                    metadata=span.attributes,
                )
            else:
                # Child span
                client.span(
                    trace_id=span.trace_id,
                    id=span.span_id,
                    parent_observation_id=span.parent_id,
                    name=span.name,
                    start_time=span.start_time,
                    end_time=span.end_time,
                    metadata=span.attributes,
                    level="DEFAULT" if span.status == "ok" else "ERROR",
                )
        except Exception:
            pass  # Don't break on export errors
    
    def flush(self) -> None:
        if self._client:
            self._client.flush()


class LangSmithExporter(BaseExporter):
    """Export to LangSmith observability platform.
    
    Requires LANGCHAIN_API_KEY env var.
    """
    
    def __init__(self, api_key: Optional[str] = None, project: str = "rlm-toolkit"):
        import os
        self.api_key = api_key or os.environ.get("LANGCHAIN_API_KEY")
        self.project = project
        self._client = None
    
    def _get_client(self):
        """Lazy load LangSmith client."""
        if self._client is None:
            try:
                from langsmith import Client
                self._client = Client(api_key=self.api_key)
            except ImportError:
                raise ImportError(
                    "langsmith package required. Install with: pip install langsmith"
                )
        return self._client
    
    def export_span(self, span: "Span") -> None:
        """Export span to LangSmith."""
        if not self.api_key:
            return
        
        try:
            client = self._get_client()
            
            # LangSmith uses runs
            client.create_run(
                name=span.name,
                run_type="chain",
                inputs={"trace_id": span.trace_id},
                outputs={"status": span.status},
                extra=span.attributes,
                project_name=self.project,
            )
        except Exception:
            pass


class BufferedExporter(BaseExporter):
    """Buffer spans and export in batches."""
    
    def __init__(self, inner: BaseExporter, max_buffer: int = 100):
        self.inner = inner
        self.max_buffer = max_buffer
        self._buffer: list = []
    
    def export_span(self, span: "Span") -> None:
        self._buffer.append(span)
        
        if len(self._buffer) >= self.max_buffer:
            self.flush()
    
    def flush(self) -> None:
        for span in self._buffer:
            self.inner.export_span(span)
        self._buffer.clear()
        self.inner.flush()
    
    def shutdown(self) -> None:
        self.flush()
        self.inner.shutdown()


class CompositeExporter(BaseExporter):
    """Export to multiple backends."""
    
    def __init__(self, exporters: list[BaseExporter]):
        self.exporters = exporters
    
    def export_span(self, span: "Span") -> None:
        for exporter in self.exporters:
            try:
                exporter.export_span(span)
            except Exception:
                pass
    
    def flush(self) -> None:
        for exporter in self.exporters:
            exporter.flush()
    
    def shutdown(self) -> None:
        for exporter in self.exporters:
            exporter.shutdown()
