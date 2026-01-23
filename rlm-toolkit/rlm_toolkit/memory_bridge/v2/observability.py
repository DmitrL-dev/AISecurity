"""
Observability Module for Memory Bridge v2.1

Provides metrics, health checks, and telemetry for production monitoring.
"""

import time
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class MetricPoint:
    """Single metric data point."""

    name: str
    value: float
    timestamp: datetime = field(default_factory=datetime.now)
    tags: Dict[str, str] = field(default_factory=dict)


@dataclass
class LatencyStats:
    """Latency statistics."""

    count: int = 0
    total_ms: float = 0.0
    min_ms: float = float("inf")
    max_ms: float = 0.0

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.count if self.count > 0 else 0.0

    def record(self, duration_ms: float) -> None:
        self.count += 1
        self.total_ms += duration_ms
        self.min_ms = min(self.min_ms, duration_ms)
        self.max_ms = max(self.max_ms, duration_ms)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "avg_ms": round(self.avg_ms, 2),
            "min_ms": round(self.min_ms, 2) if self.count > 0 else 0,
            "max_ms": round(self.max_ms, 2),
            "total_ms": round(self.total_ms, 2),
        }


class MemoryBridgeMetrics:
    """
    Metrics collector for Memory Bridge.

    Tracks:
    - Query latencies
    - Facts count and operations
    - Cache performance
    - Error rates
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._start_time = datetime.now()

        # Latency tracking
        self._route_latency = LatencyStats()
        self._discovery_latency = LatencyStats()
        self._extract_latency = LatencyStats()

        # Counters
        self._facts_added = 0
        self._facts_deleted = 0
        self._queries_total = 0
        self._discoveries_total = 0
        self._errors_total = 0

        # Cache stats
        self._cache_hits = 0
        self._cache_misses = 0

    def record_route_latency(self, duration_ms: float) -> None:
        """Record routing query latency."""
        with self._lock:
            self._route_latency.record(duration_ms)
            self._queries_total += 1

    def record_discovery_latency(self, duration_ms: float) -> None:
        """Record discovery latency."""
        with self._lock:
            self._discovery_latency.record(duration_ms)
            self._discoveries_total += 1

    def record_extract_latency(self, duration_ms: float) -> None:
        """Record extraction latency."""
        with self._lock:
            self._extract_latency.record(duration_ms)

    def record_fact_added(self) -> None:
        """Record fact addition."""
        with self._lock:
            self._facts_added += 1

    def record_fact_deleted(self) -> None:
        """Record fact deletion."""
        with self._lock:
            self._facts_deleted += 1

    def record_error(self) -> None:
        """Record error occurrence."""
        with self._lock:
            self._errors_total += 1

    def record_cache_hit(self) -> None:
        """Record cache hit."""
        with self._lock:
            self._cache_hits += 1

    def record_cache_miss(self) -> None:
        """Record cache miss."""
        with self._lock:
            self._cache_misses += 1

    @property
    def cache_hit_rate(self) -> float:
        """Get cache hit rate percentage."""
        total = self._cache_hits + self._cache_misses
        return (self._cache_hits / total * 100) if total > 0 else 0.0

    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics as dictionary."""
        uptime = (datetime.now() - self._start_time).total_seconds()

        with self._lock:
            return {
                "uptime_seconds": round(uptime, 1),
                "latency": {
                    "route": self._route_latency.to_dict(),
                    "discovery": self._discovery_latency.to_dict(),
                    "extract": self._extract_latency.to_dict(),
                },
                "counters": {
                    "facts_added": self._facts_added,
                    "facts_deleted": self._facts_deleted,
                    "queries_total": self._queries_total,
                    "discoveries_total": self._discoveries_total,
                    "errors_total": self._errors_total,
                },
                "cache": {
                    "hits": self._cache_hits,
                    "misses": self._cache_misses,
                    "hit_rate_percent": round(self.cache_hit_rate, 1),
                },
            }

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._route_latency = LatencyStats()
            self._discovery_latency = LatencyStats()
            self._extract_latency = LatencyStats()
            self._facts_added = 0
            self._facts_deleted = 0
            self._queries_total = 0
            self._discoveries_total = 0
            self._errors_total = 0
            self._cache_hits = 0
            self._cache_misses = 0


class HealthChecker:
    """
    Health check system for Memory Bridge.

    Checks:
    - Database connectivity
    - Store availability
    - Component status
    """

    def __init__(
        self,
        store=None,
        router=None,
        causal_tracker=None,
    ):
        self.store = store
        self.router = router
        self.causal_tracker = causal_tracker

    def check_store(self) -> Dict[str, Any]:
        """Check store health."""
        try:
            if self.store is None:
                return {"status": "unknown", "message": "Store not configured"}

            # Try to get stats
            stats = self.store.get_stats()
            return {
                "status": "healthy",
                "facts_count": stats.get("total_facts", 0),
                "db_path": str(self.store.db_path),
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def check_router(self) -> Dict[str, Any]:
        """Check router health."""
        try:
            if self.router is None:
                return {"status": "unknown", "message": "Router not configured"}

            return {
                "status": "healthy",
                "embeddings_enabled": self.router.embeddings_enabled,
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def check_causal(self) -> Dict[str, Any]:
        """Check causal tracker health."""
        try:
            if self.causal_tracker is None:
                return {"status": "unknown", "message": "Causal not configured"}

            decisions = self.causal_tracker.get_all_decisions()
            return {
                "status": "healthy",
                "decisions_count": len(decisions),
            }
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}

    def full_health_check(self) -> Dict[str, Any]:
        """Perform full health check."""
        checks = {
            "store": self.check_store(),
            "router": self.check_router(),
            "causal": self.check_causal(),
        }

        # Overall status
        statuses = [c.get("status") for c in checks.values()]
        if all(s == "healthy" for s in statuses):
            overall = "healthy"
        elif any(s == "unhealthy" for s in statuses):
            overall = "unhealthy"
        else:
            overall = "degraded"

        return {
            "status": overall,
            "timestamp": datetime.now().isoformat(),
            "checks": checks,
        }


# Global metrics instance
_metrics = MemoryBridgeMetrics()


def get_metrics() -> MemoryBridgeMetrics:
    """Get global metrics instance."""
    return _metrics


class timed:
    """Context manager for timing operations."""

    def __init__(self, metric_type: str = "route"):
        self.metric_type = metric_type
        self.start_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.perf_counter() - self.start_time) * 1000

        if self.metric_type == "route":
            _metrics.record_route_latency(duration_ms)
        elif self.metric_type == "discovery":
            _metrics.record_discovery_latency(duration_ms)
        elif self.metric_type == "extract":
            _metrics.record_extract_latency(duration_ms)

        if exc_type is not None:
            _metrics.record_error()

        return False  # Don't suppress exceptions
