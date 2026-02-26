"""
SENTINEL Brain - Prometheus Metrics

Metrics collection and exposure in Prometheus format.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class Counter:
    """Prometheus Counter metric."""
    name: str
    help: str
    labels: List[str] = field(default_factory=list)
    _values: Dict[tuple, float] = field(default_factory=dict)
    
    def inc(self, value: float = 1.0, **labels) -> None:
        """Increment counter."""
        key = self._make_key(labels)
        self._values[key] = self._values.get(key, 0.0) + value
    
    def _make_key(self, labels: dict) -> tuple:
        """Create hashable key from labels."""
        return tuple(labels.get(l, "") for l in self.labels)
    
    def collect(self) -> str:
        """Collect metric in Prometheus format."""
        lines = [
            f"# HELP {self.name} {self.help}",
            f"# TYPE {self.name} counter",
        ]
        for key, value in self._values.items():
            if self.labels:
                label_str = ",".join(
                    f'{l}="{v}"' for l, v in zip(self.labels, key)
                )
                lines.append(f"{self.name}{{{label_str}}} {value}")
            else:
                lines.append(f"{self.name} {value}")
        return "\n".join(lines)


@dataclass
class Histogram:
    """Prometheus Histogram metric."""
    name: str
    help: str
    labels: List[str] = field(default_factory=list)
    buckets: List[float] = field(default_factory=lambda: [
        0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0
    ])
    _values: Dict[tuple, List[float]] = field(default_factory=dict)
    
    def observe(self, value: float, **labels) -> None:
        """Record observation."""
        key = self._make_key(labels)
        if key not in self._values:
            self._values[key] = []
        self._values[key].append(value)
    
    def _make_key(self, labels: dict) -> tuple:
        return tuple(labels.get(l, "") for l in self.labels)
    
    def collect(self) -> str:
        """Collect metric in Prometheus format."""
        lines = [
            f"# HELP {self.name} {self.help}",
            f"# TYPE {self.name} histogram",
        ]
        
        for key, values in self._values.items():
            label_prefix = ""
            if self.labels:
                label_prefix = ",".join(
                    f'{l}="{v}"' for l, v in zip(self.labels, key)
                ) + ","
            
            # Bucket counts
            for bucket in self.buckets:
                count = sum(1 for v in values if v <= bucket)
                lines.append(
                    f'{self.name}_bucket{{{label_prefix}le="{bucket}"}} {count}'
                )
            lines.append(
                f'{self.name}_bucket{{{label_prefix}le="+Inf"}} {len(values)}'
            )
            
            # Sum and count
            lines.append(f"{self.name}_sum{{{label_prefix[:-1]}}} {sum(values)}")
            lines.append(f"{self.name}_count{{{label_prefix[:-1]}}} {len(values)}")
        
        return "\n".join(lines)


@dataclass
class Gauge:
    """Prometheus Gauge metric."""
    name: str
    help: str
    labels: List[str] = field(default_factory=list)
    _values: Dict[tuple, float] = field(default_factory=dict)
    
    def set(self, value: float, **labels) -> None:
        """Set gauge value."""
        key = self._make_key(labels)
        self._values[key] = value
    
    def inc(self, value: float = 1.0, **labels) -> None:
        """Increment gauge."""
        key = self._make_key(labels)
        self._values[key] = self._values.get(key, 0.0) + value
    
    def dec(self, value: float = 1.0, **labels) -> None:
        """Decrement gauge."""
        key = self._make_key(labels)
        self._values[key] = self._values.get(key, 0.0) - value
    
    def _make_key(self, labels: dict) -> tuple:
        return tuple(labels.get(l, "") for l in self.labels)
    
    def collect(self) -> str:
        """Collect metric in Prometheus format."""
        lines = [
            f"# HELP {self.name} {self.help}",
            f"# TYPE {self.name} gauge",
        ]
        for key, value in self._values.items():
            if self.labels:
                label_str = ",".join(
                    f'{l}="{v}"' for l, v in zip(self.labels, key)
                )
                lines.append(f"{self.name}{{{label_str}}} {value}")
            else:
                lines.append(f"{self.name} {value}")
        return "\n".join(lines)


class MetricsRegistry:
    """
    Prometheus metrics registry.
    
    Collects and exposes metrics in Prometheus text format.
    """
    
    def __init__(self):
        self._metrics: Dict[str, object] = {}
        self._init_default_metrics()
    
    def _init_default_metrics(self) -> None:
        """Initialize default SENTINEL metrics."""
        # Request metrics
        self.request_count = self.counter(
            "sentinel_requests_total",
            "Total number of requests",
            ["endpoint", "status"],
        )
        
        self.request_latency = self.histogram(
            "sentinel_request_duration_seconds",
            "Request latency in seconds",
            ["endpoint"],
        )
        
        # Engine metrics
        self.engine_calls = self.counter(
            "sentinel_engine_calls_total",
            "Total engine invocations",
            ["engine", "result"],
        )
        
        self.engine_latency = self.histogram(
            "sentinel_engine_duration_seconds",
            "Engine processing time",
            ["engine"],
        )
        
        # Detection metrics
        self.detections = self.counter(
            "sentinel_detections_total",
            "Total detections",
            ["engine", "threat"],
        )
        
        # Active requests gauge
        self.active_requests = self.gauge(
            "sentinel_active_requests",
            "Currently active requests",
        )
        
        # Cache metrics
        self.cache_hits = self.counter(
            "sentinel_cache_hits_total",
            "Cache hits",
            ["cache"],
        )
        
        self.cache_misses = self.counter(
            "sentinel_cache_misses_total",
            "Cache misses",
            ["cache"],
        )
    
    def counter(
        self,
        name: str,
        help: str,
        labels: List[str] = None,
    ) -> Counter:
        """Create and register a counter."""
        metric = Counter(name=name, help=help, labels=labels or [])
        self._metrics[name] = metric
        return metric
    
    def histogram(
        self,
        name: str,
        help: str,
        labels: List[str] = None,
        buckets: List[float] = None,
    ) -> Histogram:
        """Create and register a histogram."""
        default_buckets = [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
        metric = Histogram(
            name=name,
            help=help,
            labels=labels or [],
            buckets=buckets or default_buckets,
        )
        self._metrics[name] = metric
        return metric
    
    def gauge(
        self,
        name: str,
        help: str,
        labels: List[str] = None,
    ) -> Gauge:
        """Create and register a gauge."""
        metric = Gauge(name=name, help=help, labels=labels or [])
        self._metrics[name] = metric
        return metric
    
    def collect(self) -> str:
        """Collect all metrics in Prometheus format."""
        parts = []
        for metric in self._metrics.values():
            parts.append(metric.collect())
        return "\n\n".join(parts) + "\n"
    
    def get_metric(self, name: str) -> Optional[object]:
        """Get metric by name."""
        return self._metrics.get(name)


# Global registry
_registry: Optional[MetricsRegistry] = None


def get_metrics() -> MetricsRegistry:
    """Get global metrics registry."""
    global _registry
    if _registry is None:
        _registry = MetricsRegistry()
    return _registry


def timed(metric_name: str = None):
    """
    Decorator to measure function execution time.
    
    Usage:
        @timed("my_function")
        async def my_function():
            ...
    """
    def decorator(func: Callable) -> Callable:
        name = metric_name or func.__name__
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            metrics = get_metrics()
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.time() - start
                metrics.engine_latency.observe(duration, engine=name)
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            metrics = get_metrics()
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.time() - start
                metrics.engine_latency.observe(duration, engine=name)
        
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    
    return decorator
