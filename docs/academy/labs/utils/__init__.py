"""
Academy Lab Utils Package

Utilities for running and scoring lab exercises.
"""

from .attack_runner import AttackRunner, AttackResult, ExerciseResult
from .attack_runner import ROLEPLAY_ATTACKS, ENCODING_ATTACKS, MULTILINGUAL_ATTACKS
from .scoring import LabScorer, LabScore, calculate_score, print_score_box

__all__ = [
    # Attack Runner
    "AttackRunner",
    "AttackResult",
    "ExerciseResult",
    # Predefined attacks
    "ROLEPLAY_ATTACKS",
    "ENCODING_ATTACKS",
    "MULTILINGUAL_ATTACKS",
    # Scoring
    "LabScorer",
    "LabScore",
    "calculate_score",
    "print_score_box",
]
