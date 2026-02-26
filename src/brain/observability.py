"""
SENTINEL Observability Module — Production-Grade Telemetry

Provides OpenTelemetry integration for:
- Distributed tracing of engine calls
- Prometheus metrics export
- Performance profiling
- Error tracking

Usage:
    from observability import tracer, metrics
    
    with tracer.start_as_current_span("analyze_prompt") as span:
        result = engine.analyze(prompt)
        span.set_attribute("risk_score", result.risk_score)
    
    metrics.engine_latency.record(latency_ms, {"engine": "injection"})

Author: SENTINEL Team
Date: 2025-12-13
"""

import logging
import time
import functools
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager

# OpenTelemetry imports
try:
    from opentelemetry import trace, metrics as otel_metrics
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
    from opentelemetry.sdk.resources import Resource
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None
    otel_metrics = None

logger = logging.getLogger("SentinelObservability")


# ============================================================================
# Resource Configuration
# ============================================================================


def create_resource() -> "Resource":
    """Create OpenTelemetry resource with SENTINEL metadata."""
    if not OTEL_AVAILABLE:
        return None

    return Resource.create({
        "service.name": "sentinel-brain",
        "service.version": "2.0.0",
        "deployment.environment": "production",
        "sentinel.engines": "56",
    })


# ============================================================================
# Tracer Setup
# ============================================================================


class SentinelTracer:
    """
    Distributed tracing for SENTINEL engine calls.

    Provides span context for:
    - Individual engine analysis
    - Meta-Judge orchestration
    - Full request lifecycle
    """

    def __init__(self, service_name: str = "sentinel-brain"):
        self.service_name = service_name
        self._tracer = None
        self._provider = None

        if OTEL_AVAILABLE:
            self._setup_tracer()
        else:
            logger.warning("OpenTelemetry not available, tracing disabled")

    def _setup_tracer(self):
        """Initialize OpenTelemetry tracer."""
        resource = create_resource()

        self._provider = TracerProvider(resource=resource)

        # Console exporter for development
        console_exporter = ConsoleSpanExporter()
        self._provider.add_span_processor(
            BatchSpanProcessor(console_exporter)
        )

        trace.set_tracer_provider(self._provider)
        self._tracer = trace.get_tracer(__name__)

        logger.info("OpenTelemetry tracer initialized")

    @contextmanager
    def span(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        """
        Create a trace span.

        Usage:
            with tracer.span("analyze", {"engine": "injection"}) as span:
                result = engine.analyze(text)
                span.set_attribute("risk", result.risk_score)
        """
        if not self._tracer:
            # No-op context manager when tracing disabled
            yield None
            return

        with self._tracer.start_as_current_span(name) as span:
            if attributes:
                for key, value in attributes.items():
                    span.set_attribute(key, value)
            yield span

    def trace_engine(self, engine_name: str):
        """
        Decorator to trace engine methods.

        Usage:
            @tracer.trace_engine("injection")
            def analyze(self, text):
                ...
        """
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                with self.span(f"engine.{engine_name}", {"engine.name": engine_name}):
                    start = time.perf_counter()
                    try:
                        result = func(*args, **kwargs)
                        return result
                    finally:
                        elapsed = (time.perf_counter() - start) * 1000
                        # Record latency even if we can't trace
                        logger.debug(f"{engine_name}: {elapsed:.2f}ms")
            return wrapper
        return decorator


# ============================================================================
# Metrics Setup
# ============================================================================


class SentinelMetrics:
    """
    Prometheus-compatible metrics for SENTINEL.

    Metrics:
    - sentinel_engine_latency_ms: Histogram of engine latencies
    - sentinel_engine_calls_total: Counter of engine invocations
    - sentinel_risk_score: Gauge of current risk levels
    - sentinel_threats_detected_total: Counter of detected threats
    """

    def __init__(self):
        self._meter = None
        self._engine_latency = None
        self._engine_calls = None
        self._risk_score = None
        self._threats_detected = None

        if OTEL_AVAILABLE:
            self._setup_metrics()
        else:
            logger.warning("OpenTelemetry not available, metrics disabled")

    def _setup_metrics(self):
        """Initialize OpenTelemetry metrics."""
        resource = create_resource()

        # Create meter provider
        provider = MeterProvider(resource=resource)
        otel_metrics.set_meter_provider(provider)

        self._meter = otel_metrics.get_meter(__name__)

        # Engine latency histogram
        self._engine_latency = self._meter.create_histogram(
            name="sentinel_engine_latency_ms",
            description="Engine analysis latency in milliseconds",
            unit="ms",
        )

        # Engine call counter
        self._engine_calls = self._meter.create_counter(
            name="sentinel_engine_calls_total",
            description="Total number of engine calls",
            unit="1",
        )

        # Risk score gauge (using observable gauge)
        self._current_risk = 0.0
        self._risk_score = self._meter.create_observable_gauge(
            name="sentinel_risk_score",
            callbacks=[lambda options: [(self._current_risk, {})]],
            description="Current risk score",
            unit="1",
        )

        # Threats counter
        self._threats_detected = self._meter.create_counter(
            name="sentinel_threats_detected_total",
            description="Total threats detected",
            unit="1",
        )

        logger.info("OpenTelemetry metrics initialized")

    def record_latency(self, engine: str, latency_ms: float):
        """Record engine latency."""
        if self._engine_latency:
            self._engine_latency.record(latency_ms, {"engine": engine})

    def record_call(self, engine: str, verdict: str = "allow"):
        """Record engine call."""
        if self._engine_calls:
            self._engine_calls.add(1, {"engine": engine, "verdict": verdict})

    def record_threat(self, threat_type: str, severity: str = "medium"):
        """Record detected threat."""
        if self._threats_detected:
            self._threats_detected.add(1, {
                "threat_type": threat_type,
                "severity": severity,
            })

    def set_risk_score(self, score: float):
        """Update current risk score."""
        self._current_risk = score


# ============================================================================
# Performance Profiler
# ============================================================================


class PerformanceProfiler:
    """
    Lightweight profiler for engine performance analysis.

    Collects:
    - Call counts
    - Total time
    - Min/Max/Avg latency
    """

    def __init__(self):
        self._stats: Dict[str, Dict[str, Any]] = {}

    def profile(self, name: str):
        """
        Decorator to profile function execution.

        Usage:
            @profiler.profile("injection_analyze")
            def analyze(self, text):
                ...
        """
        def decorator(func: Callable):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start = time.perf_counter()
                try:
                    return func(*args, **kwargs)
                finally:
                    elapsed = (time.perf_counter() - start) * 1000
                    self._record(name, elapsed)
            return wrapper
        return decorator

    def _record(self, name: str, latency_ms: float):
        """Record profiling data."""
        if name not in self._stats:
            self._stats[name] = {
                "count": 0,
                "total_ms": 0.0,
                "min_ms": float('inf'),
                "max_ms": 0.0,
            }

        stats = self._stats[name]
        stats["count"] += 1
        stats["total_ms"] += latency_ms
        stats["min_ms"] = min(stats["min_ms"], latency_ms)
        stats["max_ms"] = max(stats["max_ms"], latency_ms)

    def get_stats(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get profiling statistics."""
        if name:
            stats = self._stats.get(name, {})
            if stats and stats["count"] > 0:
                stats["avg_ms"] = stats["total_ms"] / stats["count"]
            return stats

        # Return all stats with computed averages
        result = {}
        for n, s in self._stats.items():
            result[n] = s.copy()
            if s["count"] > 0:
                result[n]["avg_ms"] = s["total_ms"] / s["count"]
        return result

    def reset(self):
        """Reset all statistics."""
        self._stats.clear()


# ============================================================================
# Global Instances
# ============================================================================


# Singleton instances
_tracer: Optional[SentinelTracer] = None
_metrics: Optional[SentinelMetrics] = None
_profiler: Optional[PerformanceProfiler] = None


def get_tracer() -> SentinelTracer:
    """Get global tracer instance."""
    global _tracer
    if _tracer is None:
        _tracer = SentinelTracer()
    return _tracer


def get_metrics() -> SentinelMetrics:
    """Get global metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = SentinelMetrics()
    return _metrics


def get_profiler() -> PerformanceProfiler:
    """Get global profiler instance."""
    global _profiler
    if _profiler is None:
        _profiler = PerformanceProfiler()
    return _profiler


# Convenience exports
tracer = get_tracer()
metrics = get_metrics()
profiler = get_profiler()


# ============================================================================
# Instrumentation Helpers
# ============================================================================


def instrument_engine(engine_class):
    """
    Class decorator to instrument all public methods.

    Usage:
        @instrument_engine
        class InjectionEngine:
            ...
    """
    for name in dir(engine_class):
        if not name.startswith('_'):
            method = getattr(engine_class, name)
            if callable(method):
                instrumented = tracer.trace_engine(
                    engine_class.__name__)(method)
                setattr(engine_class, name, instrumented)
    return engine_class


if __name__ == "__main__":
    # Quick test
    print(f"OpenTelemetry available: {OTEL_AVAILABLE}")

    # Test tracing
    with tracer.span("test_span", {"test": True}) as span:
        print("Inside traced span")

    # Test metrics
    metrics.record_latency("injection", 15.5)
    metrics.record_call("injection", "block")
    metrics.record_threat("prompt_injection", "high")

    # Test profiler
    @profiler.profile("test_func")
    def test_func():
        time.sleep(0.01)
        return "done"

    for _ in range(5):
        test_func()

    print(f"Profiler stats: {profiler.get_stats()}")
