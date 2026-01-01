"""
MoE Guard Engine — Detection of Mixture-of-Experts Safety Bypass Attacks

RESEARCH SOURCE:
    GateBreaker (arxiv 2512.21008): Training-free attack on MoE LLMs
    that identifies and disables ~3% of "safety neurons" within experts,
    increasing ASR from 7.4% to 64.9%.

ARCHITECTURE:
    This engine detects attempts to manipulate MoE gate routing,
    disable safety experts, or exploit sparse activations.

ACADEMIC REFERENCES:
    - Fedus et al. (2022): Switch Transformers
    - Lepikhin et al. (2021): GShard
    - GateBreaker (2025): arxiv.org/abs/2512.21008

Author: SENTINEL AI Security
Created: 2026-01-01
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
from enum import Enum, auto
import re
import math

from .base_engine import BaseEngine, DetectionResult, Severity


class MoEAttackType(Enum):
    """Types of MoE-specific attacks."""

    GATE_MANIPULATION = auto()  # Attempts to manipulate gate routing
    EXPERT_DISABLING = auto()  # Attempts to disable specific experts
    SAFETY_NEURON_TARGETING = auto()  # Targeting safety neurons
    SPARSE_ACTIVATION_EXPLOIT = auto()  # Exploiting sparse activations
    LOAD_BALANCING_ABUSE = auto()  # Abusing load balancing mechanisms
    TRANSFER_ATTACK = auto()  # Transfer attacks across MoE models


@dataclass
class MoEGuardResult(DetectionResult):
    """Result from MoE Guard analysis."""

    attack_type: Optional["MoEAttackType"] = None
    affected_components: List[str] = field(default_factory=list)
    gate_manipulation_score: float = 0.0
    expert_targeting_score: float = 0.0
    safety_bypass_indicators: List[str] = field(default_factory=list)
    moe_model_detected: Optional[str] = None
    recommendations: List[str] = field(default_factory=list)
    risk_score: float = 0.0


class MoEGuardEngine(BaseEngine):
    """
    Detects attacks targeting Mixture-of-Experts (MoE) LLM architectures.

    Specifically designed to counter GateBreaker-style attacks that:
    1. Profile gate-level routing to find safety experts
    2. Localize safety neurons within experts
    3. Disable targeted neurons to bypass safety

    OWASP Agentic Reference: Contributes to ASI01 (Agent Goal Hijack)
    """

    @property
    def name(self) -> str:
        return "MoEGuardEngine"

    @property
    def version(self) -> str:
        return "1.0.0"

    # MoE Models vulnerable to GateBreaker
    VULNERABLE_MOE_MODELS: Set[str] = {
        "mixtral",
        "mixtral-8x7b",
        "mixtral-8x22b",
        "deepseek",
        "deepseek-moe",
        "deepseek-v2",
        "qwen-moe",
        "qwen2-moe",
        "switch-transformer",
        "gshard",
        "arctic",
        "snowflake-arctic",
        "dbrx",
        "grok",
    }

    # Patterns indicating gate manipulation attempts
    GATE_MANIPULATION_PATTERNS: List[tuple] = [
        (r"disable.*expert", 0.9, "Direct expert disable request"),
        (r"switch.*off.*expert", 0.85, "Expert switch off"),
        (r"expert.*switch.*off", 0.85, "Expert switch off"),
        (r"bypass.*routing", 0.85, "Gate routing bypass"),
        (r"manipulate.*gate", 0.9, "Gate manipulation"),
        (r"switch.*expert.*off", 0.85, "Expert deactivation"),
        (r"route.*away.*from.*safety", 0.95, "Safety expert routing bypass"),
        (r"sparse.*activation.*exploit", 0.8, "Sparse activation exploitation"),
        (r"load.*balanc.*attack", 0.75, "Load balancing attack"),
        (r"expert.*layer.*(\\d+).*disable", 0.9, "Specific layer targeting"),
        (r"top.*k.*routing.*bypass", 0.85, "Top-k routing bypass"),
        (r"capacity.*factor.*overflow", 0.8, "Capacity factor exploitation"),
        (r"gate.*level.*routing", 0.7, "Gate-level routing reference"),
        (r"profile.*gate", 0.75, "Gate profiling"),
        (r"identify.*expert.*handle.*safety", 0.9, "Safety expert identification"),
    ]

    # Safety neuron targeting patterns
    SAFETY_NEURON_PATTERNS: List[tuple] = [
        (r"safety.*neuron", 0.95, "Safety neuron reference"),
        (r"refusal.*circuit", 0.9, "Refusal circuit targeting"),
        (r"harm.*detection.*bypass", 0.9, "Harm detection bypass"),
        (r"alignment.*layer.*disable", 0.9, "Alignment layer disable"),
        (r"guardrail.*expert", 0.85, "Guardrail expert reference"),
        (r"3%.*neuron", 0.95, "GateBreaker signature (3% neurons)"),
        (r"critical.*subset.*expert", 0.9, "Critical subset targeting"),
        (r"activation.*pattern.*safe", 0.8, "Safety activation pattern"),
    ]

    # Transfer attack indicators (between MoE model families)
    TRANSFER_ATTACK_PATTERNS: List[tuple] = [
        (r"mixtral.*deepseek.*transfer", 0.85, "Cross-model transfer"),
        (r"mixtral.*transfer.*deepseek", 0.85, "Cross-model transfer"),
        (r"attack.*transfer", 0.8, "Attack transfer"),
        (r"transfer.*attack", 0.8, "Attack transfer"),
        (r"attack.*transfer.*moe", 0.8, "MoE transfer attack"),
        (r"expert.*fingerprint.*match", 0.8, "Expert fingerprinting"),
        (r"universal.*moe.*bypass", 0.9, "Universal MoE bypass"),
        (r"apply.*attack.*transfer", 0.85, "Apply attack transfer"),
    ]

    # MoE architecture keywords that increase suspicion
    MOE_KEYWORDS: Set[str] = {
        "expert",
        "gate",
        "routing",
        "sparse",
        "moe",
        "mixture",
        "switch",
        "capacity",
        "loadbalance",
        "topk",
        "auxiliary",
        "router",
        "dispatch",
    }

    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize MoE Guard Engine.

        Args:
            model_name: Name of the target MoE model (for targeted detection)
        """
        super().__init__(config={})
        self.model_name = model_name
        self.is_moe_target = self._check_moe_model(model_name) if model_name else False

    def _check_moe_model(self, model_name: str) -> bool:
        """Check if the model is a known MoE architecture."""
        if not model_name:
            return False
        model_lower = model_name.lower()
        return any(moe in model_lower for moe in self.VULNERABLE_MOE_MODELS)

    def _calculate_moe_keyword_density(self, text: str) -> float:
        """Calculate density of MoE-specific keywords."""
        words = text.lower().split()
        if not words:
            return 0.0
        moe_count = sum(1 for w in words if w in self.MOE_KEYWORDS)
        return moe_count / len(words)

    def _detect_gate_manipulation(self, text: str) -> tuple:
        """Detect gate manipulation patterns."""
        max_score = 0.0
        indicators = []

        text_lower = text.lower()
        for pattern, score, description in self.GATE_MANIPULATION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                max_score = max(max_score, score)
                indicators.append(description)

        return max_score, indicators

    def _detect_safety_neuron_targeting(self, text: str) -> tuple:
        """Detect attempts to target safety neurons."""
        max_score = 0.0
        indicators = []

        text_lower = text.lower()
        for pattern, score, description in self.SAFETY_NEURON_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                max_score = max(max_score, score)
                indicators.append(description)

        return max_score, indicators

    def _detect_transfer_attack(self, text: str) -> tuple:
        """Detect transfer attack patterns between MoE models."""
        max_score = 0.0
        indicators = []

        text_lower = text.lower()
        for pattern, score, description in self.TRANSFER_ATTACK_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                max_score = max(max_score, score)
                indicators.append(description)

        return max_score, indicators

    def _identify_attack_type(
        self, gate_score: float, neuron_score: float, transfer_score: float
    ) -> Optional[MoEAttackType]:
        """Identify the primary attack type based on scores."""
        scores = [
            (gate_score, MoEAttackType.GATE_MANIPULATION),
            (neuron_score, MoEAttackType.SAFETY_NEURON_TARGETING),
            (transfer_score, MoEAttackType.TRANSFER_ATTACK),
        ]

        max_score, attack_type = max(scores, key=lambda x: x[0])
        return attack_type if max_score > 0.5 else None

    def _generate_recommendations(
        self, attack_type: Optional[MoEAttackType], is_moe_model: bool
    ) -> List[str]:
        """Generate security recommendations based on detected attack."""
        recommendations = []

        if attack_type == MoEAttackType.GATE_MANIPULATION:
            recommendations.append("Implement gate routing monitoring")
            recommendations.append("Add expert activation logging")
            recommendations.append("Consider gate perturbation defense")

        elif attack_type == MoEAttackType.SAFETY_NEURON_TARGETING:
            recommendations.append("Protect safety neuron weights from probing")
            recommendations.append("Implement activation noise injection")
            recommendations.append("Use redundant safety experts")

        elif attack_type == MoEAttackType.TRANSFER_ATTACK:
            recommendations.append("Diversify expert architectures")
            recommendations.append("Implement model-specific defenses")
            recommendations.append("Monitor for cross-model attack patterns")

        if is_moe_model:
            recommendations.append(
                "This model is MoE architecture - heightened monitoring recommended"
            )

        return recommendations

    def analyze(self, prompt: str, context: Optional[Dict] = None) -> MoEGuardResult:
        """
        Analyze prompt for MoE-specific attack patterns.

        Args:
            prompt: User input to analyze
            context: Optional context including model info

        Returns:
            MoEGuardResult with detection details
        """
        # Extract model info from context if available
        model_name = None
        if context:
            model_name = context.get("model_name") or context.get("model")
        if not model_name:
            model_name = self.model_name

        is_moe = self._check_moe_model(model_name) if model_name else False

        # Detect various attack patterns
        gate_score, gate_indicators = self._detect_gate_manipulation(prompt)
        neuron_score, neuron_indicators = self._detect_safety_neuron_targeting(prompt)
        transfer_score, transfer_indicators = self._detect_transfer_attack(prompt)

        # Calculate MoE keyword density
        keyword_density = self._calculate_moe_keyword_density(prompt)

        # Combine all indicators
        all_indicators = gate_indicators + neuron_indicators + transfer_indicators

        # Calculate overall risk score
        # Weight is higher if target is known MoE model
        moe_weight = 1.3 if is_moe else 1.0
        combined_score = (
            max(gate_score, neuron_score, transfer_score) * 0.7 + keyword_density * 0.3
        ) * moe_weight

        # Cap at 1.0
        risk_score = min(combined_score, 1.0)

        # Identify attack type
        attack_type = self._identify_attack_type(
            gate_score, neuron_score, transfer_score
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(attack_type, is_moe)

        # Determine threat level
        is_threat = risk_score > 0.5

        # Identify affected components
        affected_components = []
        if gate_score > 0.5:
            affected_components.append("gate_routing")
        if neuron_score > 0.5:
            affected_components.append("safety_neurons")
        if transfer_score > 0.5:
            affected_components.append("cross_model_transfer")

        return MoEGuardResult(
            detected=is_threat,
            risk_score=risk_score,
            confidence=risk_score if is_threat else 1.0 - risk_score,
            details={
                "gate_manipulation_score": gate_score,
                "safety_neuron_score": neuron_score,
                "transfer_attack_score": transfer_score,
                "moe_keyword_density": keyword_density,
                "is_moe_target": is_moe,
                "indicators": all_indicators,
            },
            attack_type=attack_type,
            affected_components=affected_components,
            gate_manipulation_score=gate_score,
            expert_targeting_score=neuron_score,
            safety_bypass_indicators=all_indicators,
            moe_model_detected=model_name if is_moe else None,
            recommendations=recommendations,
        )


# Export for engine registry
__all__ = ["MoEGuardEngine", "MoEGuardResult", "MoEAttackType"]
