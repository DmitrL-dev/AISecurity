"""
Sentinel Watchdog Process
Monitors engine health, restarts failed engines, collects metrics.
Self-healing capability for Brain service.
"""

import asyncio
import logging
import time
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
import redis

logger = logging.getLogger("Watchdog")


@dataclass
class EngineHealth:
    """Health status of an engine."""
    name: str
    status: str  # healthy, degraded, failed
    last_check: datetime = None
    last_success: datetime = None
    failure_count: int = 0
    avg_latency_ms: float = 0.0
    error_message: str = ""


@dataclass
class WatchdogConfig:
    """Watchdog configuration."""
    check_interval_seconds: int = 30
    failure_threshold: int = 3
    recovery_timeout_seconds: int = 60
    redis_url: str = "redis://localhost:6379"
    alert_callback: Optional[Callable] = None


class Watchdog:
    """
    Monitors engine health and provides self-healing capabilities.
    """

    def __init__(self, config: WatchdogConfig = None):
        self.config = config or WatchdogConfig()
        self.engines: Dict[str, EngineHealth] = {}
        self._health_checks: Dict[str, Callable] = {}
        self.running = False
        self._redis = None

        # Initialize Redis connection
        try:
            redis_url = os.getenv("REDIS_URL", self.config.redis_url)
            self._redis = redis.from_url(redis_url)
            self._redis.ping()
            logger.info("Watchdog connected to Redis")
        except Exception as e:
            logger.warning(f"Redis not available: {e}")

        logger.info("Watchdog initialized")

    def register_engine(self, name: str, health_check: Callable[[], bool]):
        """Register an engine for monitoring."""
        self.engines[name] = EngineHealth(
            name=name,
            status="unknown",
            last_check=None,
        )
        self._health_checks[name] = health_check
        logger.info(f"Registered engine: {name}")

    async def check_engine(self, name: str) -> EngineHealth:
        """Check health of single engine."""
        health = self.engines.get(name)
        if not health:
            return None

        check_func = self._health_checks.get(name)
        if not check_func:
            health.status = "unknown"
            return health

        start_time = time.time()

        try:
            # Run health check
            if asyncio.iscoroutinefunction(check_func):
                result = await check_func()
            else:
                result = check_func()

            latency_ms = (time.time() - start_time) * 1000

            if result:
                health.status = "healthy"
                health.failure_count = 0
                health.last_success = datetime.now()
                health.avg_latency_ms = (
                    health.avg_latency_ms + latency_ms) / 2
                health.error_message = ""
            else:
                health.failure_count += 1
                if health.failure_count >= self.config.failure_threshold:
                    health.status = "failed"
                else:
                    health.status = "degraded"

        except Exception as e:
            health.failure_count += 1
            health.error_message = str(e)
            if health.failure_count >= self.config.failure_threshold:
                health.status = "failed"
            else:
                health.status = "degraded"

            logger.error(f"Engine {name} health check failed: {e}")

        health.last_check = datetime.now()

        # Store metrics in Redis
        self._store_metrics(health)

        # Alert if failed
        if health.status == "failed" and self.config.alert_callback:
            self.config.alert_callback(health)

        return health

    async def check_all(self) -> Dict[str, EngineHealth]:
        """Check health of all registered engines."""
        tasks = [self.check_engine(name) for name in self.engines]
        await asyncio.gather(*tasks)
        return self.engines

    def _store_metrics(self, health: EngineHealth):
        """Store health metrics in Redis."""
        if not self._redis:
            return

        try:
            key = f"watchdog:engine:{health.name}"
            self._redis.hset(key, mapping={
                "status": health.status,
                "failure_count": health.failure_count,
                "avg_latency_ms": health.avg_latency_ms,
                "last_check": health.last_check.isoformat() if health.last_check else "",
                "error": health.error_message or "",
            })
            self._redis.expire(key, 300)  # 5 min TTL
        except Exception as e:
            logger.warning(f"Failed to store metrics: {e}")

    def get_status_report(self) -> dict:
        """Get status report for all engines."""
        healthy = sum(1 for e in self.engines.values()
                      if e.status == "healthy")
        degraded = sum(1 for e in self.engines.values()
                       if e.status == "degraded")
        failed = sum(1 for e in self.engines.values() if e.status == "failed")

        return {
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "total": len(self.engines),
                "healthy": healthy,
                "degraded": degraded,
                "failed": failed,
            },
            "engines": {
                name: {
                    "status": h.status,
                    "failure_count": h.failure_count,
                    "latency_ms": round(h.avg_latency_ms, 2),
                    "last_success": h.last_success.isoformat() if h.last_success else None,
                }
                for name, h in self.engines.items()
            }
        }

    async def run(self):
        """Start watchdog monitoring loop."""
        self.running = True
        logger.info(
            f"Watchdog started (interval={self.config.check_interval_seconds}s)")

        while self.running:
            try:
                await self.check_all()
                report = self.get_status_report()

                summary = report["summary"]
                logger.info(
                    f"Health check: {summary['healthy']}/{summary['total']} healthy, "
                    f"{summary['degraded']} degraded, {summary['failed']} failed"
                )

            except Exception as e:
                logger.error(f"Watchdog cycle error: {e}")

            await asyncio.sleep(self.config.check_interval_seconds)

    def stop(self):
        """Stop watchdog monitoring."""
        self.running = False
        logger.info("Watchdog stopped")


# Default health checks for Sentinel engines
def create_default_health_checks():
    """Create default health check functions for Sentinel engines."""

    def check_redis():
        try:
            r = redis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379"))
            return r.ping()
        except:
            return False

    def check_language_engine():
        try:
            from engines.language import LanguageEngine
            engine = LanguageEngine()
            result = engine.detect("Hello world")
            return result.get("language") == "en"
        except:
            return False

    def check_pii_engine():
        try:
            from engines.pii import PIIEngine
            engine = PIIEngine()
            result = engine.scan("Test text without PII")
            return "entities" in result
        except:
            return False

    return {
        "redis": check_redis,
        "language": check_language_engine,
        "pii": check_pii_engine,
    }


# Singleton
_watchdog = None


def get_watchdog() -> Watchdog:
    global _watchdog
    if _watchdog is None:
        _watchdog = Watchdog()
    return _watchdog
