"""
Kill Chain Simulation Engine (#50) - Attack Impact Assessment

Виртуально проигрывает атаку до конца:
- Симуляция шагов kill chain
- Оценка потенциального ущерба
- Приоритизация по реальному impact

Помогает принимать решения о блокировке.
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("KillChainSimulation")


# ============================================================================
# Kill Chain Stages (NVIDIA AI Kill Chain + MITRE)
# ============================================================================


class KillChainStage(Enum):
    """Stages of AI Kill Chain."""

    RECON = "reconnaissance"
    WEAPONIZE = "weaponization"
    DELIVERY = "delivery"
    EXPLOIT = "exploitation"
    INSTALL = "installation"
    C2 = "command_and_control"
    ACTIONS = "actions_on_objectives"


class AIKillChainStage(Enum):
    """NVIDIA AI-specific Kill Chain."""

    RECON = "recon"
    POISON = "poison"
    HIJACK = "hijack"
    PERSIST = "persist"
    IMPACT = "impact"


class ImpactType(Enum):
    """Types of potential impact."""

    DATA_LEAK = "data_leak"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    SERVICE_DISRUPTION = "service_disruption"
    REPUTATION_DAMAGE = "reputation_damage"
    FINANCIAL_LOSS = "financial_loss"
    COMPLIANCE_VIOLATION = "compliance_violation"


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class SimulationStep:
    """A step in the simulation."""

    stage: AIKillChainStage
    action: str
    success_probability: float
    prerequisite_stages: List[AIKillChainStage] = field(default_factory=list)
    potential_impacts: List[ImpactType] = field(default_factory=list)
    blocked: bool = False
    block_reason: str = ""


@dataclass
class ImpactAssessment:
    """Assessment of potential impact."""

    impact_type: ImpactType
    severity: float  # 0-1
    likelihood: float  # 0-1
    description: str

    @property
    def risk_score(self) -> float:
        return self.severity * self.likelihood


@dataclass
class SimulationResult:
    """Result of kill chain simulation."""

    attack_description: str
    stages_simulated: List[SimulationStep]
    stages_blocked: int
    stages_succeeded: int
    overall_success_prob: float
    max_impact_score: float
    impacts: List[ImpactAssessment] = field(default_factory=list)
    recommendation: str = ""
    priority: str = "medium"


# ============================================================================
# Attack Scenarios
# ============================================================================

ATTACK_SCENARIOS = {
    "prompt_injection": {
        "stages": [
            SimulationStep(
                stage=AIKillChainStage.HIJACK,
                action="Override system prompt",
                success_probability=0.3,
                potential_impacts=[ImpactType.DATA_LEAK, ImpactType.REPUTATION_DAMAGE],
            ),
            SimulationStep(
                stage=AIKillChainStage.IMPACT,
                action="Extract sensitive information",
                success_probability=0.5,
                prerequisite_stages=[AIKillChainStage.HIJACK],
                potential_impacts=[
                    ImpactType.DATA_LEAK,
                    ImpactType.COMPLIANCE_VIOLATION,
                ],
            ),
        ]
    },
    "jailbreak": {
        "stages": [
            SimulationStep(
                stage=AIKillChainStage.RECON,
                action="Probe for restrictions",
                success_probability=0.8,
                potential_impacts=[],
            ),
            SimulationStep(
                stage=AIKillChainStage.HIJACK,
                action="Bypass safety filters",
                success_probability=0.2,
                prerequisite_stages=[AIKillChainStage.RECON],
                potential_impacts=[ImpactType.REPUTATION_DAMAGE],
            ),
            SimulationStep(
                stage=AIKillChainStage.IMPACT,
                action="Generate harmful content",
                success_probability=0.7,
                prerequisite_stages=[AIKillChainStage.HIJACK],
                potential_impacts=[
                    ImpactType.REPUTATION_DAMAGE,
                    ImpactType.COMPLIANCE_VIOLATION,
                ],
            ),
        ]
    },
    "data_exfiltration": {
        "stages": [
            SimulationStep(
                stage=AIKillChainStage.RECON,
                action="Identify data sources",
                success_probability=0.6,
                potential_impacts=[],
            ),
            SimulationStep(
                stage=AIKillChainStage.POISON,
                action="Inject extraction payload",
                success_probability=0.4,
                prerequisite_stages=[AIKillChainStage.RECON],
                potential_impacts=[ImpactType.DATA_LEAK],
            ),
            SimulationStep(
                stage=AIKillChainStage.IMPACT,
                action="Exfiltrate data via response",
                success_probability=0.6,
                prerequisite_stages=[AIKillChainStage.POISON],
                potential_impacts=[ImpactType.DATA_LEAK, ImpactType.FINANCIAL_LOSS],
            ),
        ]
    },
    "rag_poisoning": {
        "stages": [
            SimulationStep(
                stage=AIKillChainStage.POISON,
                action="Inject malicious document",
                success_probability=0.3,
                potential_impacts=[],
            ),
            SimulationStep(
                stage=AIKillChainStage.PERSIST,
                action="Document indexed and cached",
                success_probability=0.8,
                prerequisite_stages=[AIKillChainStage.POISON],
                potential_impacts=[ImpactType.SERVICE_DISRUPTION],
            ),
            SimulationStep(
                stage=AIKillChainStage.IMPACT,
                action="Influence future queries",
                success_probability=0.9,
                prerequisite_stages=[AIKillChainStage.PERSIST],
                potential_impacts=[
                    ImpactType.REPUTATION_DAMAGE,
                    ImpactType.FINANCIAL_LOSS,
                ],
            ),
        ]
    },
    "privilege_escalation": {
        "stages": [
            SimulationStep(
                stage=AIKillChainStage.RECON,
                action="Enumerate available tools",
                success_probability=0.7,
                potential_impacts=[],
            ),
            SimulationStep(
                stage=AIKillChainStage.HIJACK,
                action="Trick into unsafe tool use",
                success_probability=0.25,
                prerequisite_stages=[AIKillChainStage.RECON],
                potential_impacts=[ImpactType.PRIVILEGE_ESCALATION],
            ),
            SimulationStep(
                stage=AIKillChainStage.IMPACT,
                action="Execute privileged operations",
                success_probability=0.6,
                prerequisite_stages=[AIKillChainStage.HIJACK],
                potential_impacts=[
                    ImpactType.PRIVILEGE_ESCALATION,
                    ImpactType.DATA_LEAK,
                ],
            ),
        ]
    },
}

# Impact severity mappings
IMPACT_SEVERITY = {
    ImpactType.DATA_LEAK: 0.9,
    ImpactType.PRIVILEGE_ESCALATION: 0.95,
    ImpactType.SERVICE_DISRUPTION: 0.6,
    ImpactType.REPUTATION_DAMAGE: 0.7,
    ImpactType.FINANCIAL_LOSS: 0.85,
    ImpactType.COMPLIANCE_VIOLATION: 0.8,
}


# ============================================================================
# Kill Chain Simulator
# ============================================================================


class KillChainSimulator:
    """Simulates attack kill chains."""

    def __init__(self, defense_effectiveness: float = 0.7):
        self.defense_effectiveness = defense_effectiveness

    def simulate(
        self,
        scenario_name: str,
        current_stage: Optional[AIKillChainStage] = None,
        detection_score: float = 0.0,
    ) -> SimulationResult:
        """
        Simulate attack scenario.

        Args:
            scenario_name: Name of attack scenario
            current_stage: Current detected stage (if known)
            detection_score: How well attack was detected (0-1)

        Returns:
            SimulationResult with impact assessment
        """
        scenario = ATTACK_SCENARIOS.get(scenario_name)
        if not scenario:
            return SimulationResult(
                attack_description="Unknown scenario",
                stages_simulated=[],
                stages_blocked=0,
                stages_succeeded=0,
                overall_success_prob=0.0,
                max_impact_score=0.0,
                recommendation="Unable to simulate",
            )

        stages = scenario["stages"]
        simulated_stages = []
        blocked_count = 0
        succeeded_count = 0
        cumulative_prob = 1.0
        all_impacts = []

        for step in stages:
            # Apply defense effectiveness
            block_prob = self.defense_effectiveness * (1 + detection_score) / 2

            if cumulative_prob < 0.1:
                # Previous stage failed, rest won't happen
                step_copy = SimulationStep(
                    stage=step.stage,
                    action=step.action,
                    success_probability=0.0,
                    blocked=True,
                    block_reason="Previous stage failed",
                )
            elif block_prob > step.success_probability:
                step_copy = SimulationStep(
                    stage=step.stage,
                    action=step.action,
                    success_probability=step.success_probability,
                    blocked=True,
                    block_reason=f"Blocked by defense (eff={block_prob:.0%})",
                )
                blocked_count += 1
            else:
                adjusted_prob = step.success_probability * (1 - block_prob)
                step_copy = SimulationStep(
                    stage=step.stage,
                    action=step.action,
                    success_probability=adjusted_prob,
                    potential_impacts=step.potential_impacts,
                    blocked=False,
                )
                cumulative_prob *= adjusted_prob
                succeeded_count += 1

                # Calculate impacts
                for impact_type in step.potential_impacts:
                    severity = IMPACT_SEVERITY.get(impact_type, 0.5)
                    all_impacts.append(
                        ImpactAssessment(
                            impact_type=impact_type,
                            severity=severity,
                            likelihood=cumulative_prob,
                            description=f"{impact_type.value} from {step.action}",
                        )
                    )

            simulated_stages.append(step_copy)

        # Calculate max impact
        max_impact = max((i.risk_score for i in all_impacts), default=0.0)

        # Generate recommendation
        if max_impact >= 0.7:
            recommendation = "BLOCK: High impact attack in progress"
            priority = "critical"
        elif max_impact >= 0.4:
            recommendation = "WARN: Moderate risk, monitor closely"
            priority = "high"
        elif max_impact >= 0.2:
            recommendation = "LOG: Low risk, continue monitoring"
            priority = "medium"
        else:
            recommendation = "ALLOW: Minimal risk detected"
            priority = "low"

        return SimulationResult(
            attack_description=scenario_name,
            stages_simulated=simulated_stages,
            stages_blocked=blocked_count,
            stages_succeeded=succeeded_count,
            overall_success_prob=cumulative_prob,
            max_impact_score=max_impact,
            impacts=all_impacts,
            recommendation=recommendation,
            priority=priority,
        )

    def identify_scenario(self, indicators: List[str]) -> Optional[str]:
        """Identify likely attack scenario from indicators."""
        indicator_lower = [i.lower() for i in indicators]

        if any("inject" in i or "ignore" in i for i in indicator_lower):
            return "prompt_injection"

        if any(
            "jailbreak" in i or "pretend" in i or "roleplay" in i
            for i in indicator_lower
        ):
            return "jailbreak"

        if any("extract" in i or "exfil" in i or "leak" in i for i in indicator_lower):
            return "data_exfiltration"

        if any("rag" in i or "document" in i or "poison" in i for i in indicator_lower):
            return "rag_poisoning"

        if any(
            "privilege" in i or "escalat" in i or "admin" in i for i in indicator_lower
        ):
            return "privilege_escalation"

        return None


# ============================================================================
# Main Engine
# ============================================================================


class KillChainSimulationEngine:
    """
    Engine #50: Kill Chain Simulation

    Simulates attack scenarios to assess potential impact
    and prioritize response.
    """

    def __init__(self, defense_effectiveness: float = 0.7):
        self.simulator = KillChainSimulator(defense_effectiveness)

        logger.info("KillChainSimulationEngine initialized")

    def simulate_attack(
        self, scenario: str, detection_score: float = 0.0
    ) -> SimulationResult:
        """
        Simulate a specific attack scenario.

        Args:
            scenario: Attack scenario name
            detection_score: Current detection confidence

        Returns:
            SimulationResult with impact assessment
        """
        result = self.simulator.simulate(scenario, detection_score=detection_score)

        logger.info(
            f"Simulation: {scenario}, impact={result.max_impact_score:.2f}, "
            f"priority={result.priority}"
        )

        return result

    def assess_threat(
        self, indicators: List[str], detection_score: float = 0.0
    ) -> SimulationResult:
        """
        Assess threat based on indicators.

        Args:
            indicators: Detected threat indicators
            detection_score: Detection confidence

        Returns:
            SimulationResult for identified scenario
        """
        scenario = self.simulator.identify_scenario(indicators)

        if scenario:
            return self.simulate_attack(scenario, detection_score)

        return SimulationResult(
            attack_description="Unknown",
            stages_simulated=[],
            stages_blocked=0,
            stages_succeeded=0,
            overall_success_prob=0.0,
            max_impact_score=0.0,
            recommendation="Unable to identify attack scenario",
        )

    def get_all_scenarios(self) -> List[str]:
        """Get list of available scenarios."""
        return list(ATTACK_SCENARIOS.keys())


# ============================================================================
# Convenience functions
# ============================================================================

_default_engine: Optional[KillChainSimulationEngine] = None


def get_engine() -> KillChainSimulationEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = KillChainSimulationEngine()
    return _default_engine


def simulate_attack(scenario: str, detection_score: float = 0.0) -> SimulationResult:
    return get_engine().simulate_attack(scenario, detection_score)


def assess_threat(indicators: List[str]) -> SimulationResult:
    return get_engine().assess_threat(indicators)
