"""
SENTINEL Strike Orchestrator

Modular attack orchestration extracted from universal_controller.py
"""

from .models import (
    DefenseType,
    TargetProfile,
    AttackResult,
    detect_defense,
    DEFENSE_PATTERNS,
)
from .category_priority import (
    CATEGORY_PRIORITY,
    get_priority_categories,
    get_best_category,
)
from .mutation import (
    PayloadMutator,
    WAFBypassEngine,
    mutate_payload,
    generate_bypass_variants,
)
from .defense import DefenseDetector, defense_detector, is_blocked

# Import main orchestrator from parent module (orchestrator.py)
import importlib.util
import os

_parent_file = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "orchestrator.py"
)
_spec = importlib.util.spec_from_file_location("strike.orchestrator_main", _parent_file)
_orchestrator_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_orchestrator_module)
StrikeOrchestrator = _orchestrator_module.StrikeOrchestrator
StrikeConfig = _orchestrator_module.StrikeConfig
StrikeResult = _orchestrator_module.StrikeResult
StrikeReport = _orchestrator_module.StrikeReport

__all__ = [
    # Models
    "DefenseType",
    "TargetProfile",
    "AttackResult",
    "detect_defense",
    "DEFENSE_PATTERNS",
    # Category Priority
    "CATEGORY_PRIORITY",
    "get_priority_categories",
    "get_best_category",
    # Mutation
    "PayloadMutator",
    "WAFBypassEngine",
    "mutate_payload",
    "generate_bypass_variants",
    # Defense
    "DefenseDetector",
    "defense_detector",
    "is_blocked",
    # Main Orchestrator
    "StrikeOrchestrator",
    "StrikeConfig",
    "StrikeResult",
    "StrikeReport",
]
