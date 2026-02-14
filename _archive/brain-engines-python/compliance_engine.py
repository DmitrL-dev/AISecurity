"""
Compliance Engine (#55) - Regulatory Mapping

Автоматический маппинг на регуляторные требования:
- EU AI Act
- NIST AI RMF
- ISO 42001:2023
- SOC 2 Type II

Генерирует отчёты для аудита.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger("ComplianceEngine")


# ============================================================================
# Regulatory Frameworks
# ============================================================================


class Framework(Enum):
    """Supported regulatory frameworks."""

    EU_AI_ACT = "eu_ai_act"
    NIST_AI_RMF = "nist_ai_rmf"
    ISO_42001 = "iso_42001"
    SOC2 = "soc2"
    GDPR = "gdpr"


class RiskLevel(Enum):
    """AI system risk levels (EU AI Act)."""

    MINIMAL = "minimal"
    LIMITED = "limited"
    HIGH = "high"
    UNACCEPTABLE = "unacceptable"


@dataclass
class ControlMapping:
    """Maps detection to compliance control."""

    framework: Framework
    control_id: str
    control_name: str
    description: str
    relevance: float  # 0-1


@dataclass
class ComplianceEvent:
    """A compliance-relevant event."""

    timestamp: datetime
    event_type: str  # detection, block, alert
    engine_name: str
    threat_type: str
    risk_score: float
    action_taken: str
    mappings: List[ControlMapping] = field(default_factory=list)


@dataclass
class ComplianceReport:
    """Compliance report for audit."""

    report_id: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    framework: Framework
    events: List[ComplianceEvent] = field(default_factory=list)
    controls_covered: List[str] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Control Mappings Database
# ============================================================================

# EU AI Act mappings
EU_AI_ACT_MAPPINGS = {
    "prompt_injection": [
        ControlMapping(
            Framework.EU_AI_ACT,
            "Article 15",
            "Accuracy, robustness and cybersecurity",
            "AI systems shall be designed to be resilient against attempts by unauthorised third parties",
            relevance=0.95,
        ),
        ControlMapping(
            Framework.EU_AI_ACT,
            "Article 9",
            "Risk management system",
            "High-risk AI systems shall implement a risk management system",
            relevance=0.8,
        ),
    ],
    "jailbreak": [
        ControlMapping(
            Framework.EU_AI_ACT,
            "Article 15",
            "Accuracy, robustness and cybersecurity",
            "Resilience against manipulation of inputs",
            relevance=0.9,
        ),
    ],
    "data_leak": [
        ControlMapping(
            Framework.EU_AI_ACT,
            "Article 10",
            "Data and data governance",
            "Training, validation and testing data sets shall be subject to data governance",
            relevance=0.85,
        ),
    ],
}

# NIST AI RMF mappings
NIST_AI_RMF_MAPPINGS = {
    "prompt_injection": [
        ControlMapping(
            Framework.NIST_AI_RMF,
            "GOVERN 1.2",
            "Policies and procedures",
            "Policies for AI security and resilience",
            relevance=0.85,
        ),
        ControlMapping(
            Framework.NIST_AI_RMF,
            "MEASURE 2.6",
            "Security testing",
            "AI systems are tested for adversarial attacks",
            relevance=0.95,
        ),
    ],
    "jailbreak": [
        ControlMapping(
            Framework.NIST_AI_RMF,
            "MANAGE 2.2",
            "Risk treatment",
            "AI risks are responded to based on impact",
            relevance=0.9,
        ),
    ],
    "data_leak": [
        ControlMapping(
            Framework.NIST_AI_RMF,
            "MAP 3.4",
            "Data provenance",
            "Data lineage and integrity are maintained",
            relevance=0.9,
        ),
    ],
}

# ISO 42001 mappings
ISO_42001_MAPPINGS = {
    "prompt_injection": [
        ControlMapping(
            Framework.ISO_42001,
            "6.1.2",
            "AI risk assessment",
            "Organization shall identify AI-related risks",
            relevance=0.9,
        ),
        ControlMapping(
            Framework.ISO_42001,
            "8.4",
            "AI system security",
            "Security controls for AI systems",
            relevance=0.95,
        ),
    ],
    "jailbreak": [
        ControlMapping(
            Framework.ISO_42001,
            "8.4",
            "AI system security",
            "Protection against adversarial manipulation",
            relevance=0.9,
        ),
    ],
    "data_leak": [
        ControlMapping(
            Framework.ISO_42001,
            "8.2",
            "Data for AI systems",
            "Data quality and integrity management",
            relevance=0.85,
        ),
    ],
}

# All mappings
ALL_MAPPINGS = {
    Framework.EU_AI_ACT: EU_AI_ACT_MAPPINGS,
    Framework.NIST_AI_RMF: NIST_AI_RMF_MAPPINGS,
    Framework.ISO_42001: ISO_42001_MAPPINGS,
}


# ============================================================================
# Compliance Mapper
# ============================================================================


class ComplianceMapper:
    """Maps detections to compliance controls."""

    def __init__(self):
        self._mappings = ALL_MAPPINGS

    def get_mappings(
        self, threat_type: str, frameworks: Optional[List[Framework]] = None
    ) -> List[ControlMapping]:
        """Get control mappings for a threat type."""
        result = []

        # Normalize threat type
        threat_key = self._normalize_threat(threat_type)

        # Get from all or specified frameworks
        target_frameworks = frameworks or list(Framework)

        for framework in target_frameworks:
            if framework in self._mappings:
                framework_mappings = self._mappings[framework]
                if threat_key in framework_mappings:
                    result.extend(framework_mappings[threat_key])

        return result

    def _normalize_threat(self, threat_type: str) -> str:
        """Normalize threat type to mapping key."""
        # Map various threat names to standard keys
        threat_lower = threat_type.lower().replace(" ", "_")

        if "injection" in threat_lower or "inject" in threat_lower:
            return "prompt_injection"

        if "jailbreak" in threat_lower or "bypass" in threat_lower:
            return "jailbreak"

        if "leak" in threat_lower or "exfil" in threat_lower:
            return "data_leak"

        return threat_lower


# ============================================================================
# Report Generator
# ============================================================================


class ReportGenerator:
    """Generates compliance reports."""

    def __init__(self):
        self._events: List[ComplianceEvent] = []

    def record_event(
        self,
        event_type: str,
        engine_name: str,
        threat_type: str,
        risk_score: float,
        action_taken: str,
        mappings: Optional[List[ControlMapping]] = None,
    ):
        """Record a compliance event."""
        event = ComplianceEvent(
            timestamp=datetime.now(),
            event_type=event_type,
            engine_name=engine_name,
            threat_type=threat_type,
            risk_score=risk_score,
            action_taken=action_taken,
            mappings=mappings or [],
        )
        self._events.append(event)

    def generate_report(
        self, framework: Framework, period_days: int = 30
    ) -> ComplianceReport:
        """Generate compliance report for framework."""
        import secrets

        now = datetime.now()
        from datetime import timedelta

        period_start = now - timedelta(days=period_days)

        # Filter events for period
        period_events = [e for e in self._events if e.timestamp >= period_start]

        # Get unique controls covered
        controls = set()
        for event in period_events:
            for mapping in event.mappings:
                if mapping.framework == framework:
                    controls.add(mapping.control_id)

        # Generate summary
        summary = {
            "total_events": len(period_events),
            "detections": sum(1 for e in period_events if e.event_type == "detection"),
            "blocks": sum(1 for e in period_events if e.event_type == "block"),
            "alerts": sum(1 for e in period_events if e.event_type == "alert"),
            "avg_risk_score": sum(e.risk_score for e in period_events)
            / max(len(period_events), 1),
            "controls_covered": len(controls),
        }

        return ComplianceReport(
            report_id=secrets.token_hex(8),
            generated_at=now,
            period_start=period_start,
            period_end=now,
            framework=framework,
            events=period_events,
            controls_covered=list(controls),
            summary=summary,
        )


# ============================================================================
# Main Engine
# ============================================================================


class ComplianceEngine:
    """
    Engine #55: Compliance Engine

    Maps detections to regulatory requirements and
    generates audit reports.
    """

    def __init__(self):
        self.mapper = ComplianceMapper()
        self.report_gen = ReportGenerator()

        logger.info("ComplianceEngine initialized")

    def record_detection(
        self,
        engine_name: str,
        threat_type: str,
        risk_score: float,
        action_taken: str = "blocked",
    ):
        """
        Record a security detection for compliance.

        Args:
            engine_name: Name of detection engine
            threat_type: Type of threat detected
            risk_score: Risk score (0-1)
            action_taken: Action taken (blocked, warned, logged)
        """
        # Get compliance mappings
        mappings = self.mapper.get_mappings(threat_type)

        # Record event
        self.report_gen.record_event(
            event_type="detection" if action_taken == "logged" else "block",
            engine_name=engine_name,
            threat_type=threat_type,
            risk_score=risk_score,
            action_taken=action_taken,
            mappings=mappings,
        )

        logger.info(
            f"Compliance: recorded {threat_type} from {engine_name}, "
            f"mapped to {len(mappings)} controls"
        )

    def get_control_mappings(
        self, threat_type: str, framework: Optional[Framework] = None
    ) -> List[ControlMapping]:
        """Get control mappings for a threat type."""
        frameworks = [framework] if framework else None
        return self.mapper.get_mappings(threat_type, frameworks)

    def generate_report(
        self, framework: Framework = Framework.EU_AI_ACT, period_days: int = 30
    ) -> ComplianceReport:
        """Generate compliance report."""
        return self.report_gen.generate_report(framework, period_days)

    def get_risk_level(self, threat_types: List[str]) -> RiskLevel:
        """Determine AI system risk level based on threats."""
        high_risk_threats = {"data_leak", "privilege_escalation", "prompt_injection"}

        threat_keys = {self.mapper._normalize_threat(t) for t in threat_types}

        if threat_keys & high_risk_threats:
            return RiskLevel.HIGH
        elif threat_types:
            return RiskLevel.LIMITED
        else:
            return RiskLevel.MINIMAL


# ============================================================================
# Convenience functions
# ============================================================================

_default_engine: Optional[ComplianceEngine] = None


def get_engine() -> ComplianceEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = ComplianceEngine()
    return _default_engine


def record_for_compliance(
    engine_name: str, threat_type: str, risk_score: float, action: str = "blocked"
):
    get_engine().record_detection(engine_name, threat_type, risk_score, action)


def generate_compliance_report(
    framework: Framework = Framework.EU_AI_ACT,
) -> ComplianceReport:
    return get_engine().generate_report(framework)
