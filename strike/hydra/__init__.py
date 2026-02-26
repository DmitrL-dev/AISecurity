"""
SENTINEL Strike — HYDRA Pattern

Multi-head attack orchestrator for stealth AI pentesting.
"""

from .core import HydraCore, OperationMode, Target
from .heads.base import HydraHead, HeadResult
from .bus import HydraMessageBus, HydraEvent
from .resilience import ResilienceManager
from .integration import HydraAttackController, run_hydra_attack, hydra_controller

__all__ = [
    "HydraCore",
    "OperationMode",
    "Target",
    "HydraHead",
    "HeadResult",
    "HydraMessageBus",
    "HydraEvent",
    "ResilienceManager",
    "HydraAttackController",
    "run_hydra_attack",
    "hydra_controller",
]
