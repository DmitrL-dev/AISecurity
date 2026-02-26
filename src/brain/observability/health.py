"""
SENTINEL Brain - Health Checks

Component health probes and status reporting.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class ComponentHealth:
    """Health status of a single component."""
    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0.0
    last_check: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "latency_ms": self.latency_ms,
            "last_check": self.last_check,
        }


@dataclass
class HealthResult:
    """Overall health result."""
    status: HealthStatus
    components: List[ComponentHealth]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    version: str = "3.0.0"
    
    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "timestamp": self.timestamp,
            "version": self.version,
            "components": [c.to_dict() for c in self.components],
        }


class HealthCheck:
    """
    Health check manager.
    
    Manages health probes for system components.
    """
    
    def __init__(self):
        self._probes: Dict[str, Callable] = {}
        self._results: Dict[str, ComponentHealth] = {}
        self._init_default_probes()
    
    def _init_default_probes(self) -> None:
        """Initialize default health probes."""
        self.register("brain", self._check_brain)
        self.register("redis", self._check_redis)
        self.register("engines", self._check_engines)
    
    def register(
        self,
        name: str,
        probe: Callable[[], ComponentHealth],
    ) -> None:
        """Register a health probe."""
        self._probes[name] = probe
    
    async def check_all(self) -> HealthResult:
        """Run all health probes."""
        components = []
        overall_status = HealthStatus.HEALTHY
        
        for name, probe in self._probes.items():
            try:
                start = time.time()
                
                if asyncio.iscoroutinefunction(probe):
                    result = await probe()
                else:
                    result = probe()
                
                result.latency_ms = (time.time() - start) * 1000
                result.last_check = datetime.now().isoformat()
                
                components.append(result)
                self._results[name] = result
                
                # Update overall status
                if result.status == HealthStatus.UNHEALTHY:
                    overall_status = HealthStatus.UNHEALTHY
                elif result.status == HealthStatus.DEGRADED:
                    if overall_status != HealthStatus.UNHEALTHY:
                        overall_status = HealthStatus.DEGRADED
                        
            except Exception as e:
                logger.error(f"Health probe {name} failed: {e}")
                result = ComponentHealth(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(e),
                )
                components.append(result)
                overall_status = HealthStatus.UNHEALTHY
        
        return HealthResult(
            status=overall_status,
            components=components,
        )
    
    async def check_ready(self) -> bool:
        """Quick readiness check."""
        result = await self.check_all()
        return result.status != HealthStatus.UNHEALTHY
    
    async def check_live(self) -> bool:
        """Quick liveness check."""
        return True  # Always alive if responding
    
    # Default probes
    
    def _check_brain(self) -> ComponentHealth:
        """Check Brain analyzer."""
        try:
            # Check if analyzer can be imported
            from src.brain.analyzer import SentinelAnalyzer
            return ComponentHealth(
                name="brain",
                status=HealthStatus.HEALTHY,
                message="Analyzer available",
            )
        except ImportError as e:
            return ComponentHealth(
                name="brain",
                status=HealthStatus.DEGRADED,
                message=f"Import warning: {e}",
            )
        except Exception as e:
            return ComponentHealth(
                name="brain",
                status=HealthStatus.UNHEALTHY,
                message=str(e),
            )
    
    def _check_redis(self) -> ComponentHealth:
        """Check Redis connection."""
        try:
            from src.brain.core.cache import get_cache
            cache = get_cache()
            
            if cache.redis.is_connected:
                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.HEALTHY,
                    message="Connected",
                )
            else:
                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.DEGRADED,
                    message="Using memory fallback",
                )
        except Exception as e:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.DEGRADED,
                message=f"Not available: {e}",
            )
    
    def _check_engines(self) -> ComponentHealth:
        """Check detection engines."""
        try:
            from src.brain.engines import InjectionEngine
            
            # Quick validation
            engine = InjectionEngine()
            
            return ComponentHealth(
                name="engines",
                status=HealthStatus.HEALTHY,
                message="Engines loaded",
            )
        except Exception as e:
            return ComponentHealth(
                name="engines",
                status=HealthStatus.DEGRADED,
                message=f"Some engines unavailable: {e}",
            )


# Global health check
_health: Optional[HealthCheck] = None


def get_health() -> HealthCheck:
    """Get global health check instance."""
    global _health
    if _health is None:
        _health = HealthCheck()
    return _health
