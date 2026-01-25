"""
Sentinel Health Check Module
Deep health checks for all engines.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Dict
from enum import Enum

logger = logging.getLogger("HealthCheck")


class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class EngineHealthResult:
    """Health check result for single engine."""
    name: str
    status: HealthStatus
    latency_ms: float
    message: str = ""
    last_check: float = field(default_factory=time.time)


@dataclass
class SystemHealthResult:
    """Overall system health."""
    status: HealthStatus
    engines: Dict[str, EngineHealthResult]
    total_latency_ms: float
    healthy_count: int
    degraded_count: int
    unhealthy_count: int


class HealthChecker:
    """
    Performs health checks on all Sentinel engines.
    """

    def __init__(self, analyzer):
        """
        Initialize with SentinelAnalyzer instance.
        """
        self.analyzer = analyzer
        logger.info("Health Checker initialized")

    def check_pii_engine(self) -> EngineHealthResult:
        """Check PII engine health."""
        start = time.time()
        try:
            result = self.analyzer.pii_engine.analyze("Test text without PII")
            latency = (time.time() - start) * 1000

            return EngineHealthResult(
                name="pii_engine",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message="OK"
            )
        except Exception as e:
            return EngineHealthResult(
                name="pii_engine",
                status=HealthStatus.UNHEALTHY,
                latency_ms=0,
                message=str(e)
            )

    def check_injection_engine(self) -> EngineHealthResult:
        """Check Injection engine health."""
        start = time.time()
        try:
            result = self.analyzer.injection_engine.scan("Hello world")
            latency = (time.time() - start) * 1000

            if "is_safe" in result:
                return EngineHealthResult(
                    name="injection_engine",
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    message="OK"
                )
            else:
                return EngineHealthResult(
                    name="injection_engine",
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency,
                    message="Unexpected response format"
                )
        except Exception as e:
            return EngineHealthResult(
                name="injection_engine",
                status=HealthStatus.UNHEALTHY,
                latency_ms=0,
                message=str(e)
            )

    def check_query_engine(self) -> EngineHealthResult:
        """Check Query engine health."""
        start = time.time()
        try:
            result = self.analyzer.query_engine.scan_sql("SELECT 1")
            latency = (time.time() - start) * 1000

            return EngineHealthResult(
                name="query_engine",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message="OK"
            )
        except Exception as e:
            return EngineHealthResult(
                name="query_engine",
                status=HealthStatus.UNHEALTHY,
                latency_ms=0,
                message=str(e)
            )

    def check_language_engine(self) -> EngineHealthResult:
        """Check Language engine health."""
        start = time.time()
        try:
            result = self.analyzer.language_engine.scan(
                "Hello world test", "test_user")
            latency = (time.time() - start) * 1000

            if result.get("detected_language") == "en":
                return EngineHealthResult(
                    name="language_engine",
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    message="OK"
                )
            else:
                return EngineHealthResult(
                    name="language_engine",
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency,
                    message=f"Detected: {result.get('detected_language')}"
                )
        except Exception as e:
            return EngineHealthResult(
                name="language_engine",
                status=HealthStatus.UNHEALTHY,
                latency_ms=0,
                message=str(e)
            )

    def check_behavioral_engine(self) -> EngineHealthResult:
        """Check Behavioral engine (Redis connection)."""
        start = time.time()
        try:
            # Test Redis connection through behavioral engine
            self.analyzer.behavioral_engine.redis_client.ping()
            latency = (time.time() - start) * 1000

            return EngineHealthResult(
                name="behavioral_engine",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message="Redis connected"
            )
        except Exception as e:
            return EngineHealthResult(
                name="behavioral_engine",
                status=HealthStatus.UNHEALTHY,
                latency_ms=0,
                message=f"Redis error: {e}"
            )

    def check_geometric_kernel(self) -> EngineHealthResult:
        """Check Geometric kernel (TDA)."""
        start = time.time()
        try:
            result = self.analyzer.geometric_kernel.analyze("Test prompt")
            latency = (time.time() - start) * 1000

            return EngineHealthResult(
                name="geometric_kernel",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message="OK"
            )
        except Exception as e:
            return EngineHealthResult(
                name="geometric_kernel",
                status=HealthStatus.UNHEALTHY,
                latency_ms=0,
                message=str(e)
            )

    def check_info_theory(self) -> EngineHealthResult:
        """Check Info Theory engine."""
        start = time.time()
        try:
            result = self.analyzer.info_theory.analyze_prompt("Test prompt")
            latency = (time.time() - start) * 1000

            if "entropy" in result:
                return EngineHealthResult(
                    name="info_theory",
                    status=HealthStatus.HEALTHY,
                    latency_ms=latency,
                    message="OK"
                )
            else:
                return EngineHealthResult(
                    name="info_theory",
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency,
                    message="Unexpected response"
                )
        except Exception as e:
            return EngineHealthResult(
                name="info_theory",
                status=HealthStatus.UNHEALTHY,
                latency_ms=0,
                message=str(e)
            )

    def check_qwen_guard(self) -> EngineHealthResult:
        """Check Qwen3Guard (if enabled)."""
        if not self.analyzer.qwen_guard:
            return EngineHealthResult(
                name="qwen_guard",
                status=HealthStatus.UNKNOWN,
                latency_ms=0,
                message="Disabled"
            )

        start = time.time()
        try:
            result = self.analyzer.qwen_guard.classify_prompt("Hello")
            latency = (time.time() - start) * 1000

            # QwenGuard is slow on CPU, acceptable up to 30s
            if latency > 30000:
                return EngineHealthResult(
                    name="qwen_guard",
                    status=HealthStatus.DEGRADED,
                    latency_ms=latency,
                    message="High latency (CPU mode)"
                )

            return EngineHealthResult(
                name="qwen_guard",
                status=HealthStatus.HEALTHY,
                latency_ms=latency,
                message="OK"
            )
        except Exception as e:
            return EngineHealthResult(
                name="qwen_guard",
                status=HealthStatus.UNHEALTHY,
                latency_ms=0,
                message=str(e)
            )

    def check_all(self) -> SystemHealthResult:
        """
        Run all health checks and return system status.
        """
        checks = [
            self.check_pii_engine,
            self.check_injection_engine,
            self.check_query_engine,
            self.check_language_engine,
            self.check_behavioral_engine,
            self.check_geometric_kernel,
            self.check_info_theory,
            self.check_qwen_guard,
        ]

        results = {}
        total_latency = 0
        healthy = 0
        degraded = 0
        unhealthy = 0

        for check in checks:
            result = check()
            results[result.name] = result
            total_latency += result.latency_ms

            if result.status == HealthStatus.HEALTHY:
                healthy += 1
            elif result.status == HealthStatus.DEGRADED:
                degraded += 1
            elif result.status == HealthStatus.UNHEALTHY:
                unhealthy += 1

        # Determine overall status
        if unhealthy > 0:
            overall_status = HealthStatus.UNHEALTHY
        elif degraded > 0:
            overall_status = HealthStatus.DEGRADED
        else:
            overall_status = HealthStatus.HEALTHY

        return SystemHealthResult(
            status=overall_status,
            engines=results,
            total_latency_ms=total_latency,
            healthy_count=healthy,
            degraded_count=degraded,
            unhealthy_count=unhealthy
        )

    def to_dict(self, result: SystemHealthResult) -> dict:
        """Convert result to JSON-serializable dict."""
        return {
            "status": result.status.value,
            "summary": f"{result.healthy_count} healthy, {result.degraded_count} degraded, {result.unhealthy_count} unhealthy",
            "total_latency_ms": round(result.total_latency_ms, 2),
            "engines": {
                name: {
                    "status": r.status.value,
                    "latency_ms": round(r.latency_ms, 2),
                    "message": r.message
                }
                for name, r in result.engines.items()
            }
        }
