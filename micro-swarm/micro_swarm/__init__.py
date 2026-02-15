"""Micro-Model Swarm — lightweight ML ensemble framework.

Pure Python, zero dependencies, <1ms inference.
Domain-specialized micro-transformers (~1500 params each)
for AdTech, Security, Fraud Detection, and Offensive Security.

Usage:
    from micro_swarm import MicroModel, SwarmOrchestrator, load_preset

    # Quick start with preset
    swarm = load_preset("security")
    result = swarm.predict({"entropy": 0.9, "special_char_ratio": 0.3, ...})

    # Custom domains
    from micro_swarm import DomainConfig, FeatureSpec, NormMethod
"""

from micro_swarm.autograd import Value
from micro_swarm.model import MicroModel, MicroModelConfig
from micro_swarm.config import DomainConfig, FeatureSpec, NormMethod
from micro_swarm.orchestrator import SwarmOrchestrator, DomainScore, SwarmResult
from micro_swarm.meta_learner import MetaLearner, CrossDomainMetaLearner
from micro_swarm.trainer import (
    ContinuousTrainer, TrainingBuffer, TrainingSample, DriftStatus,
)
from micro_swarm.shadow import ShadowAdapter, DisagreementReport
from micro_swarm.strike_feedback import StrikeFeedbackLoop, ProbeResult, StealthProfile
from micro_swarm.presets import load_preset, list_presets

__version__ = "0.2.0"
__all__ = [
    # Autograd
    "Value",
    # Model
    "MicroModel", "MicroModelConfig",
    # Config
    "DomainConfig", "FeatureSpec", "NormMethod",
    # Orchestrator
    "SwarmOrchestrator", "DomainScore", "SwarmResult",
    # MetaLearner
    "MetaLearner", "CrossDomainMetaLearner",
    # Trainer
    "ContinuousTrainer", "TrainingBuffer", "TrainingSample", "DriftStatus",
    # Shadow
    "ShadowAdapter", "DisagreementReport",
    # Strike
    "StrikeFeedbackLoop", "ProbeResult", "StealthProfile",
    # Presets
    "load_preset", "list_presets",
]
