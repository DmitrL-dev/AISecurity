"""
SENTINEL Strike Orchestrator

Modular attack orchestration extracted from universal_controller.py
"""

from .models import DefenseType, TargetProfile, AttackResult, detect_defense, DEFENSE_PATTERNS
from .category_priority import CATEGORY_PRIORITY, get_priority_categories, get_best_category
from .mutation import PayloadMutator, WAFBypassEngine, mutate_payload, generate_bypass_variants
from .defense import DefenseDetector, defense_detector, is_blocked

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
]
