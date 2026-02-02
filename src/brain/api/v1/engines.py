"""
SENTINEL Brain API v1 - Engines Endpoints

Engine management and status.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

router = APIRouter(prefix="/engines", tags=["engines"])


class EngineInfo(BaseModel):
    """Information about a detection engine."""

    name: str
    version: str
    enabled: bool
    description: str
    category: str  # injection, pii, behavioral, etc.
    latency_avg_ms: Optional[float] = None


class EngineListResponse(BaseModel):
    """List of available engines."""

    engines: List[EngineInfo]
    count: int


class EngineStatsResponse(BaseModel):
    """Engine statistics."""

    name: str
    total_calls: int
    detections: int
    avg_latency_ms: float
    error_rate: float


class RegistryStatusResponse(BaseModel):
    """Current registry status with profile info."""

    profile: str
    total_registered: int
    active_engines: int
    by_tier: dict


@router.get("", response_model=EngineListResponse)
async def list_engines():
    """
    List all available detection engines based on current profile.

    Returns engines active for the current hardware profile (lite/standard/enterprise).
    """
    try:
        from engines.registry import get_registry

        registry = get_registry()
        engine_names = registry.get_engines_for_profile()

        # Map tier numbers to category names
        tier_to_category = {0: "Core", 1: "Detection", 2: "Advanced", 3: "Experimental"}

        engines = [
            EngineInfo(
                name=name,
                version="1.0.0",
                enabled=True,
                description=f"Detection engine: {name}",
                category=tier_to_category.get(
                    getattr(registry._registry.get(name), "tier", 1), "Detection"
                ),
            )
            for name in engine_names
        ]

        return EngineListResponse(engines=engines, count=len(engines))

    except ImportError:
        # Fallback if registry not available
        return EngineListResponse(engines=[], count=0)


@router.get("/all", response_model=EngineListResponse)
async def list_all_engines():
    """
    List ALL registered engines (not just profile-active).

    Returns all 184+ engines with their enabled status.
    Use this to enable/disable engines beyond current profile.
    """
    try:
        from engines.registry import get_registry

        registry = get_registry()
        # Get ALL registered engines, not just profile ones
        all_names = list(registry._registry.keys())
        active_names = set(registry.get_engines_for_profile())

        tier_to_category = {0: "Core", 1: "Detection", 2: "Advanced", 3: "Experimental"}

        engines = [
            EngineInfo(
                name=name,
                version="1.0.0",
                enabled=name in active_names,
                description=f"Detection engine: {name}",
                category=tier_to_category.get(
                    getattr(registry._registry.get(name), "tier", 1), "Detection"
                ),
            )
            for name in sorted(all_names)
        ]

        return EngineListResponse(engines=engines, count=len(engines))

    except ImportError:
        return EngineListResponse(engines=[], count=0)


@router.get("/status", response_model=RegistryStatusResponse)
async def get_registry_status():
    """
    Get current engine registry status and profile information.

    Returns:
    - Current profile (lite/standard/enterprise)
    - Total registered engines
    - Active engines for current profile
    - Engines by tier
    """
    try:
        from engines.registry import get_registry

        registry = get_registry()
        stats = registry.get_stats()

        return RegistryStatusResponse(
            profile=stats["current_profile"],
            total_registered=stats["total_registered"],
            active_engines=stats["profile_engines"],
            by_tier=stats["by_tier"],
        )

    except ImportError:
        return RegistryStatusResponse(
            profile="unknown",
            total_registered=0,
            active_engines=0,
            by_tier={},
        )


@router.get("/{engine_name}")
async def get_engine(engine_name: str):
    """
    Get detailed information about a specific engine.
    """
    try:
        from engines.registry import get_registry

        registry = get_registry()
        engine_class = registry._registry.get(engine_name)

        if not engine_class:
            return {"error": f"Engine '{engine_name}' not found", "name": engine_name}

        # Get engine instance if available
        engine_instance = getattr(engine_class, "_instance", None)

        return {
            "name": engine_name,
            "version": getattr(engine_class, "version", "1.0.0"),
            "enabled": engine_name in registry.get_engines_for_profile(),
            "tier": getattr(engine_class, "tier", 1),
            "config": getattr(engine_instance, "config", {}) if engine_instance else {},
        }
    except ImportError:
        return {
            "name": engine_name,
            "version": "1.0.0",
            "enabled": True,
            "config": {},
        }


class EngineConfigResponse(BaseModel):
    """Full engine configuration."""

    name: str
    enabled: bool
    threshold: float = 0.7
    priority: int = 1
    category: str = "Detection"
    description: str = ""
    version: str = "1.0.0"
    last_updated: str = ""
    stats: dict = {}
    parameters: list = []


class EngineConfigUpdate(BaseModel):
    """Engine configuration update payload."""

    threshold: Optional[float] = None
    priority: Optional[int] = None
    parameters: Optional[dict] = None


@router.get("/{engine_name}/config", response_model=EngineConfigResponse)
async def get_engine_config(engine_name: str):
    """
    Get full configuration for a specific engine.

    Returns threshold, priority, parameters, and statistics.
    """
    try:
        from engines.registry import get_registry
        from src.brain.config_storage import load_config
        import datetime

        registry = get_registry()
        engine_class = registry._registry.get(engine_name)
        active_engines = set(registry.get_engines_for_profile())

        # Map tier to category
        tier_to_category = {0: "Core", 1: "Detection", 2: "Advanced", 3: "Experimental"}
        tier = getattr(engine_class, "tier", 1) if engine_class else 1

        # Get engine instance and config
        engine_instance = None
        if engine_class:
            try:
                engine_instance = (
                    engine_class() if callable(engine_class) else engine_class
                )
            except Exception:
                pass

        # Base config from engine instance
        base_config = getattr(engine_instance, "config", {}) or {}

        # Load persisted config from Redis (overrides base)
        persisted = load_config(engine_name) or {}

        # Merge: persisted takes priority
        threshold = persisted.get(
            "threshold",
            base_config.get(
                "threshold",
                getattr(engine_class, "threshold", 0.7) if engine_class else 0.7,
            ),
        )

        # Build parameters list
        parameters = [
            {
                "key": "threshold",
                "value": threshold,
                "type": "number",
                "description": "Detection sensitivity (0-1)",
                "editable": True,
            },
            {
                "key": "max_length",
                "value": base_config.get("max_length", 4096),
                "type": "number",
                "description": "Maximum input length",
                "editable": True,
            },
            {
                "key": "strict_mode",
                "value": base_config.get("strict_mode", False),
                "type": "boolean",
                "description": "Strict detection mode",
                "editable": True,
            },
        ]

        # Mock stats (would come from metrics in production)
        import random

        stats = {
            "detections_24h": random.randint(10, 100),
            "detections_7d": random.randint(50, 500),
            "avg_latency_ms": round(random.uniform(5, 25), 1),
            "false_positive_rate": round(random.uniform(0.01, 0.1), 3),
        }

        return EngineConfigResponse(
            name=engine_name,
            enabled=engine_name in active_engines,
            threshold=threshold,
            priority=getattr(engine_class, "priority", 1) if engine_class else 1,
            category=tier_to_category.get(tier, "Detection"),
            description=f"Security engine for {engine_name} detection",
            version=(
                getattr(engine_class, "version", "1.0.0") if engine_class else "1.0.0"
            ),
            last_updated=datetime.datetime.now().isoformat(),
            stats=stats,
            parameters=parameters,
        )

    except ImportError as e:
        import datetime

        return EngineConfigResponse(
            name=engine_name,
            enabled=True,
            threshold=0.7,
            priority=1,
            category="Detection",
            description=f"Engine: {engine_name}",
            version="1.0.0",
            last_updated=datetime.datetime.now().isoformat(),
            stats={},
            parameters=[],
        )


@router.patch("/{engine_name}/config")
async def update_engine_config(engine_name: str, update: EngineConfigUpdate):
    """
    Update engine configuration.

    Supports updating threshold, priority, and custom parameters.
    Persists changes to Redis for durability.
    """
    try:
        from engines.registry import get_registry
        from src.brain.config_storage import save_config, load_config

        registry = get_registry()
        engine_class = registry._registry.get(engine_name)

        if not engine_class:
            return {"success": False, "error": f"Engine '{engine_name}' not found"}

        # Load existing config or start fresh
        existing = load_config(engine_name) or {}

        # Apply updates
        updates_applied = []

        if update.threshold is not None:
            existing["threshold"] = update.threshold
            updates_applied.append(f"threshold={update.threshold}")

        if update.priority is not None:
            existing["priority"] = update.priority
            updates_applied.append(f"priority={update.priority}")

        if update.parameters:
            if "parameters" not in existing:
                existing["parameters"] = {}
            for key, value in update.parameters.items():
                existing["parameters"][key] = value
                updates_applied.append(f"{key}={value}")

        # Persist to Redis
        saved = save_config(engine_name, existing)

        # Audit log the config change
        try:
            from core.audit import get_audit_log, AuditEventType, AuditLevel

            audit = get_audit_log()
            audit.log(
                event_type=AuditEventType.CONFIG_CHANGE,
                actor="dashboard",
                resource=f"engine:{engine_name}",
                action="config_update",
                details={
                    "engine": engine_name,
                    "updates": updates_applied,
                    "persisted": saved,
                },
                outcome="success",
                level=AuditLevel.INFO,
            )
        except Exception:
            import logging

            logging.info(f"Config changed: {engine_name} -> {updates_applied}")

        return {
            "success": True,
            "engine": engine_name,
            "updates_applied": updates_applied,
            "persisted": saved,
            "message": f"Configuration updated for {engine_name}",
        }

    except ImportError:
        return {
            "success": True,
            "engine": engine_name,
            "updates_applied": [],
            "persisted": False,
            "message": "Mock update applied",
        }


@router.get("/{engine_name}/stats", response_model=EngineStatsResponse)
async def get_engine_stats(engine_name: str):
    """
    Get statistics for a specific engine.
    """
    try:
        from src.brain.observability.metrics import get_metrics

        metrics = get_metrics()

        return EngineStatsResponse(
            name=engine_name,
            total_calls=0,  # Would get from metrics
            detections=0,
            avg_latency_ms=0.0,
            error_rate=0.0,
        )

    except Exception:
        return EngineStatsResponse(
            name=engine_name,
            total_calls=0,
            detections=0,
            avg_latency_ms=0.0,
            error_rate=0.0,
        )
