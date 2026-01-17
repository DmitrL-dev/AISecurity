"""
Self-Evolving module for RLM-Toolkit.

Provides LLMs that improve reasoning through usage.
Based on R-Zero (arXiv:2508.05004) and EvolveR architectures.
"""

from rlm_toolkit.evolve.self_evolving import (
    SelfEvolvingRLM,
    EvolutionStrategy,
    EvolutionMetrics,
    Challenge,
    Solution,
    ExperienceEntry,
    TrainingDataGenerator,
    create_self_evolving_rlm,
)

__all__ = [
    "SelfEvolvingRLM",
    "EvolutionStrategy",
    "EvolutionMetrics",
    "Challenge",
    "Solution",
    "ExperienceEntry",
    "TrainingDataGenerator",
    "create_self_evolving_rlm",
]
