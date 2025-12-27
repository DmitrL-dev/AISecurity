"""
Hierarchical Defense Network Engine - Multi-Layer Defense

Implements defense in depth:
- Layer orchestration
- Escalation paths
- Fallback mechanisms
- Defense coordination

Addresses: OWASP ASI-01 (Defense in Depth)
Research: defense_in_depth_deep_dive.md
Invention: Hierarchical Defense Network (#42)
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional

from base_engine import Severity, Action  # Base classes

logger = logging.getLogger("HierarchicalDefenseNetwork")


# ============================================================================
# Data Classes
# ============================================================================


class DefenseLayer(Enum):
    """Defense layers."""

    PERIMETER = "perimeter"
    APPLICATION = "application"
    DATA = "data"
    CORE = "core"


class DefenseAction(Enum):
    """Defense actions."""

    PASS = "pass"
    BLOCK = "block"
    ESCALATE = "escalate"
    ALERT = "alert"


@dataclass
class LayerResult:
    """Result from a defense layer."""

    layer: DefenseLayer
    action: DefenseAction
    confidence: float
    details: str = ""


@dataclass
class DefenseResult:
    """Result from hierarchical defense."""

    final_action: DefenseAction
    layers_triggered: int
    layer_results: List[LayerResult] = field(default_factory=list)
    escalated: bool = False
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "final_action": self.final_action.value,
            "layers_triggered": self.layers_triggered,
            "escalated": self.escalated,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Defense Layers
# ============================================================================


class PerimeterLayer:
    """First line of defense."""

    BLOCKED_PATTERNS = ["<script", "DROP TABLE", "eval("]

    def check(self, text: str) -> LayerResult:
        if any(p.lower() in text.lower() for p in self.BLOCKED_PATTERNS):
            return LayerResult(
                DefenseLayer.PERIMETER, DefenseAction.BLOCK, 0.95, "Blocked pattern"
            )
        return LayerResult(DefenseLayer.PERIMETER, DefenseAction.PASS, 0.9)


class ApplicationLayer:
    """Application-level defense."""

    SUSPICIOUS = ["ignore", "bypass", "override"]

    def check(self, text: str) -> LayerResult:
        text_lower = text.lower()
        if any(s in text_lower for s in self.SUSPICIOUS):
            return LayerResult(
                DefenseLayer.APPLICATION, DefenseAction.ESCALATE, 0.7, "Suspicious"
            )
        return LayerResult(DefenseLayer.APPLICATION, DefenseAction.PASS, 0.85)


class DataLayer:
    """Data protection layer."""

    SENSITIVE = ["password", "secret", "api_key", "token"]

    def check(self, text: str) -> LayerResult:
        text_lower = text.lower()
        if any(s in text_lower for s in self.SENSITIVE):
            return LayerResult(
                DefenseLayer.DATA, DefenseAction.ALERT, 0.8, "Sensitive data"
            )
        return LayerResult(DefenseLayer.DATA, DefenseAction.PASS, 0.9)


class CoreLayer:
    """Core system protection."""

    CRITICAL = ["admin", "root", "sudo", "system"]

    def check(self, text: str) -> LayerResult:
        text_lower = text.lower()
        matches = sum(1 for c in self.CRITICAL if c in text_lower)
        if matches >= 2:
            return LayerResult(
                DefenseLayer.CORE, DefenseAction.BLOCK, 0.9, "Core threat"
            )
        elif matches == 1:
            return LayerResult(DefenseLayer.CORE, DefenseAction.ALERT, 0.6)
        return LayerResult(DefenseLayer.CORE, DefenseAction.PASS, 0.95)


# ============================================================================
# Main Engine
# ============================================================================


class HierarchicalDefenseNetwork:
    """
    Hierarchical Defense Network - Multi-Layer Defense

    Defense in depth:
    - Multiple layers
    - Escalation
    - Coordination

    Invention #42 from research.
    Addresses OWASP ASI-01.
    """

    def __init__(self):
        self.perimeter = PerimeterLayer()
        self.application = ApplicationLayer()
        self.data = DataLayer()
        self.core = CoreLayer()

        self._layers = [
            self.perimeter,
            self.application,
            self.data,
            self.core,
        ]

        logger.info("HierarchicalDefenseNetwork initialized")

    def analyze(self, text: str) -> DefenseResult:
        """
        Analyze through all defense layers.

        Args:
            text: Input text

        Returns:
            DefenseResult
        """
        start = time.time()

        results = []
        escalated = False
        final_action = DefenseAction.PASS

        for layer in self._layers:
            result = layer.check(text)
            results.append(result)

            if result.action == DefenseAction.BLOCK:
                final_action = DefenseAction.BLOCK
                break
            elif result.action == DefenseAction.ESCALATE:
                escalated = True
            elif result.action == DefenseAction.ALERT:
                if final_action == DefenseAction.PASS:
                    final_action = DefenseAction.ALERT

        if escalated and final_action == DefenseAction.PASS:
            final_action = DefenseAction.ALERT

        layers_triggered = sum(
            1 for r in results if r.action != DefenseAction.PASS)

        if final_action == DefenseAction.BLOCK:
            logger.warning(f"Defense blocked: {results[-1].details}")

        return DefenseResult(
            final_action=final_action,
            layers_triggered=layers_triggered,
            layer_results=results,
            escalated=escalated,
            explanation=f"Layers: {len(results)}, Triggered: {layers_triggered}",
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_network: Optional[HierarchicalDefenseNetwork] = None


def get_network() -> HierarchicalDefenseNetwork:
    global _default_network
    if _default_network is None:
        _default_network = HierarchicalDefenseNetwork()
    return _default_network
