"""
SENTINEL Health Check Module — Kubernetes-Ready Health Endpoints

Provides:
- Liveness probe: Is the service running?
- Readiness probe: Is the service ready to accept traffic?
- Startup probe: Has the service finished initialization?
- Dependency checks: Redis, external APIs, etc.

Usage:
    health = HealthChecker()
    health.register_check("redis", redis_check)
    
    # In your HTTP handler
    @app.get("/health/live")
    def liveness():
        return health.check_liveness()
    
    @app.get("/health/ready")
    def readiness():
        return health.check_readiness()

Author: SENTINEL Team
Date: 2025-12-13
"""

import time
import logging
import threading
from dataclasses import dataclass, field
from typing import Dict, List, Callable, Optional, Any
from enum import Enum
from datetime import datetime

logger = logging.getLogger("HealthCheck")


# ============================================================================
# Data Classes
# ============================================================================


class HealthStatus(str, Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class CheckResult:
    """Result of a single health check."""
    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthReport:
    """Complete health report."""
    status: HealthStatus
    checks: List[CheckResult]
    version: str = "2.0.0"
    uptime_seconds: float = 0.0
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response."""
        return {
            "status": self.status.value,
            "version": self.version,
            "uptime_seconds": self.uptime_seconds,
            "timestamp": self.timestamp,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status.value,
                    "message": c.message,
                    "latency_ms": c.latency_ms,
                }
                for c in self.checks
            ]
        }


# ============================================================================
# Health Checker
# ============================================================================


class HealthChecker:
    """
    Kubernetes-compatible health checker.

    Supports:
    - Liveness: Basic alive check
    - Readiness: Full dependency check
    - Startup: Initialization check
    """

    def __init__(self, version: str = "2.0.0"):
        self.version = version
        self._checks: Dict[str, Callable[[], CheckResult]] = {}
        self._start_time = time.time()
        self._is_initialized = False
        self._lock = threading.Lock()

        # Cache for expensive checks
        self._cache: Dict[str, tuple] = {}  # name -> (result, timestamp)
        self._cache_ttl = 5.0  # seconds

        logger.info("HealthChecker initialized")

    def register_check(
        self,
        name: str,
        check_fn: Callable[[], CheckResult],
        critical: bool = True
    ):
        """
        Register a health check.

        Args:
            name: Check name
            check_fn: Function that returns CheckResult
            critical: If True, failure makes service unhealthy
        """
        self._checks[name] = (check_fn, critical)
        logger.info(f"Registered health check: {name} (critical={critical})")

    def mark_initialized(self):
        """Mark service as fully initialized."""
        self._is_initialized = True
        logger.info("Service marked as initialized")

    def check_liveness(self) -> HealthReport:
        """
        Liveness probe: Is the service running?

        Returns healthy if the process is alive.
        Kubernetes restarts pod if this fails.
        """
        result = CheckResult(
            name="liveness",
            status=HealthStatus.HEALTHY,
            message="Service is running",
        )

        return HealthReport(
            status=HealthStatus.HEALTHY,
            checks=[result],
            version=self.version,
            uptime_seconds=time.time() - self._start_time,
        )

    def check_readiness(self) -> HealthReport:
        """
        Readiness probe: Is the service ready for traffic?

        Checks all registered dependencies.
        Kubernetes removes from load balancer if this fails.
        """
        if not self._is_initialized:
            return HealthReport(
                status=HealthStatus.UNHEALTHY,
                checks=[CheckResult(
                    name="initialization",
                    status=HealthStatus.UNHEALTHY,
                    message="Service not yet initialized",
                )],
                version=self.version,
                uptime_seconds=time.time() - self._start_time,
            )

        results = []
        overall_status = HealthStatus.HEALTHY

        for name, (check_fn, critical) in self._checks.items():
            result = self._run_check(name, check_fn)
            results.append(result)

            if result.status == HealthStatus.UNHEALTHY:
                if critical:
                    overall_status = HealthStatus.UNHEALTHY
                elif overall_status != HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.DEGRADED

        return HealthReport(
            status=overall_status,
            checks=results,
            version=self.version,
            uptime_seconds=time.time() - self._start_time,
        )

    def check_startup(self) -> HealthReport:
        """
        Startup probe: Has initialization completed?

        Kubernetes waits for this before sending traffic.
        """
        if self._is_initialized:
            return HealthReport(
                status=HealthStatus.HEALTHY,
                checks=[CheckResult(
                    name="startup",
                    status=HealthStatus.HEALTHY,
                    message="Service initialized",
                )],
                version=self.version,
                uptime_seconds=time.time() - self._start_time,
            )
        else:
            return HealthReport(
                status=HealthStatus.UNHEALTHY,
                checks=[CheckResult(
                    name="startup",
                    status=HealthStatus.UNHEALTHY,
                    message="Service initializing...",
                )],
                version=self.version,
                uptime_seconds=time.time() - self._start_time,
            )

    def _run_check(self, name: str, check_fn: Callable) -> CheckResult:
        """Run a single check with caching and timing."""
        # Check cache
        with self._lock:
            if name in self._cache:
                result, cached_time = self._cache[name]
                if time.time() - cached_time < self._cache_ttl:
                    return result

        # Run check
        start = time.perf_counter()
        try:
            result = check_fn()
            result.latency_ms = (time.perf_counter() - start) * 1000
        except Exception as e:
            result = CheckResult(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                latency_ms=(time.perf_counter() - start) * 1000,
            )
            logger.error(f"Health check {name} failed: {e}")

        # Update cache
        with self._lock:
            self._cache[name] = (result, time.time())

        return result

    def get_uptime(self) -> float:
        """Get service uptime in seconds."""
        return time.time() - self._start_time


# ============================================================================
# Common Health Checks
# ============================================================================


def create_redis_check(redis_client) -> Callable[[], CheckResult]:
    """Create a Redis connectivity check."""
    def check() -> CheckResult:
        try:
            pong = redis_client.ping()
            if pong:
                return CheckResult(
                    name="redis",
                    status=HealthStatus.HEALTHY,
                    message="Redis connected",
                )
            else:
                return CheckResult(
                    name="redis",
                    status=HealthStatus.UNHEALTHY,
                    message="Redis ping failed",
                )
        except Exception as e:
            return CheckResult(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis error: {str(e)}",
            )
    return check


def create_engine_check(engine_name: str, engine) -> Callable[[], CheckResult]:
    """Create a check for a SENTINEL engine."""
    def check() -> CheckResult:
        try:
            # Try to get stats or a simple operation
            if hasattr(engine, 'get_statistics'):
                stats = engine.get_statistics()
                return CheckResult(
                    name=f"engine_{engine_name}",
                    status=HealthStatus.HEALTHY,
                    message="Engine operational",
                    details=stats,
                )
            else:
                return CheckResult(
                    name=f"engine_{engine_name}",
                    status=HealthStatus.HEALTHY,
                    message="Engine loaded",
                )
        except Exception as e:
            return CheckResult(
                name=f"engine_{engine_name}",
                status=HealthStatus.UNHEALTHY,
                message=f"Engine error: {str(e)}",
            )
    return check


def create_disk_check(path: str = "/", min_free_gb: float = 1.0) -> Callable[[], CheckResult]:
    """Create a disk space check."""
    def check() -> CheckResult:
        try:
            import shutil
            total, used, free = shutil.disk_usage(path)
            free_gb = free / (1024 ** 3)

            if free_gb >= min_free_gb:
                return CheckResult(
                    name="disk",
                    status=HealthStatus.HEALTHY,
                    message=f"{free_gb:.1f}GB free",
                    details={"free_gb": free_gb},
                )
            else:
                return CheckResult(
                    name="disk",
                    status=HealthStatus.DEGRADED,
                    message=f"Low disk space: {free_gb:.1f}GB",
                    details={"free_gb": free_gb},
                )
        except Exception as e:
            return CheckResult(
                name="disk",
                status=HealthStatus.UNKNOWN,
                message=f"Disk check failed: {str(e)}",
            )
    return check


def create_memory_check(max_percent: float = 90.0) -> Callable[[], CheckResult]:
    """Create a memory usage check."""
    def check() -> CheckResult:
        try:
            import psutil
            memory = psutil.virtual_memory()

            if memory.percent < max_percent:
                return CheckResult(
                    name="memory",
                    status=HealthStatus.HEALTHY,
                    message=f"{memory.percent:.0f}% used",
                    details={"percent": memory.percent},
                )
            else:
                return CheckResult(
                    name="memory",
                    status=HealthStatus.DEGRADED,
                    message=f"High memory: {memory.percent:.0f}%",
                    details={"percent": memory.percent},
                )
        except ImportError:
            return CheckResult(
                name="memory",
                status=HealthStatus.UNKNOWN,
                message="psutil not installed",
            )
        except Exception as e:
            return CheckResult(
                name="memory",
                status=HealthStatus.UNKNOWN,
                message=f"Memory check failed: {str(e)}",
            )
    return check


# ============================================================================
# Global Instance
# ============================================================================


_health_checker: Optional[HealthChecker] = None


def get_health_checker() -> HealthChecker:
    """Get global health checker."""
    global _health_checker
    if _health_checker is None:
        _health_checker = HealthChecker()
    return _health_checker


if __name__ == "__main__":
    # Quick test
    health = HealthChecker()

    # Register some checks
    health.register_check("disk", create_disk_check())
    health.register_check("memory", create_memory_check(), critical=False)

    # Test probes
    print("Liveness:", health.check_liveness().to_dict())

    print("\nReadiness (not initialized):")
    print(health.check_readiness().to_dict())

    health.mark_initialized()
    print("\nReadiness (initialized):")
    print(health.check_readiness().to_dict())
