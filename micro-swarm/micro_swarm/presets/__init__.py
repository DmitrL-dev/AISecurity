"""Preset registry for Micro-Model Swarm.

Load pre-configured SwarmOrchestrators for different domains.
"""

from __future__ import annotations

from typing import Callable

from micro_swarm.orchestrator import SwarmOrchestrator
from micro_swarm.presets.adtech import build_adtech
from micro_swarm.presets.security import build_security
from micro_swarm.presets.fraud import build_fraud
from micro_swarm.presets.strike import build_strike
from micro_swarm.presets.jailbreak import build_jailbreak

REGISTRY: dict[str, Callable[[], SwarmOrchestrator]] = {
    "adtech": build_adtech,
    "security": build_security,
    "fraud": build_fraud,
    "strike": build_strike,
    "jailbreak": build_jailbreak,
}


def load_preset(name: str) -> SwarmOrchestrator:
    """Load a pre-configured SwarmOrchestrator by name.

    Available presets: adtech, security, fraud, strike, jailbreak
    """
    if name not in REGISTRY:
        raise ValueError(
            f"Unknown preset: {name!r}. "
            f"Available: {list(REGISTRY.keys())}"
        )
    return REGISTRY[name]()


def list_presets() -> list[str]:
    """List available preset names."""
    return list(REGISTRY.keys())
