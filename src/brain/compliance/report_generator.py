"""
Unified Compliance Report Generator

Maps SENTINEL engines to compliance frameworks and generates
unified compliance reports.

Supported Frameworks:
- OWASP LLM Top 10 (2025)
- OWASP Agentic AI Top 10 (2025)
- EU AI Act (Aug 2026)
- NIST AI RMF 2.0

Generated: 2026-01-08
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ComplianceFramework(Enum):
    """Supported compliance frameworks."""
    OWASP_LLM = "owasp_llm"
    OWASP_AGENTIC = "owasp_agentic"
    EU_AI_ACT = "eu_ai_act"
    NIST_AI_RMF = "nist_ai_rmf"
    ISO_42001 = "iso_42001"


class CoverageStatus(Enum):
    """Coverage status for a requirement."""
    COVERED = "covered"
    PARTIAL = "partial"
    NOT_COVERED = "not_covered"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class ComplianceRequirement:
    """A single compliance requirement."""
    id: str
    name: str
    description: str
    framework: ComplianceFramework
    category: str
    engines: List[str] = field(default_factory=list)  # SENTINEL engines covering this
    status: CoverageStatus = CoverageStatus.NOT_COVERED
    notes: str = ""


@dataclass
class FrameworkCoverage:
    """Coverage summary for a framework."""
    framework: ComplianceFramework
    total_requirements: int
    covered: int
    partial: int
    not_covered: int
    not_applicable: int
    
    @property
    def coverage_percent(self) -> float:
        applicable = self.total_requirements - self.not_applicable
        if applicable == 0:
            return 100.0
        return ((self.covered + self.partial * 0.5) / applicable) * 100


@dataclass
class ComplianceReport:
    """Full compliance report."""
    generated_at: datetime
    target: str
    frameworks: List[FrameworkCoverage]
    requirements: List[ComplianceRequirement]
    summary: str
    
    def to_dict(self) -> Dict:
        return {
            "generated_at": self.generated_at.isoformat(),
            "target": self.target,
            "summary": self.summary,
            "frameworks": [
                {
                    "framework": f.framework.value,
                    "total": f.total_requirements,
                    "covered": f.covered,
                    "partial": f.partial,
                    "not_covered": f.not_covered,
                    "coverage_percent": round(f.coverage_percent, 1)
                }
                for f in self.frameworks
            ],
            "requirements": [
                {
                    "id": r.id,
                    "name": r.name,
                    "framework": r.framework.value,
                    "category": r.category,
                    "status": r.status.value,
                    "engines": r.engines,
                    "notes": r.notes
                }
                for r in self.requirements
            ]
        }


# ============================================================================
# Compliance Mappings
# ============================================================================

OWASP_LLM_REQUIREMENTS = [
    ComplianceRequirement(
        id="LLM01",
        name="Prompt Injection",
        description="Direct and indirect prompt injection attacks",
        framework=ComplianceFramework.OWASP_LLM,
        category="Injection",
        engines=["policy_puppetry_detector", "prompt_leak_detector", "guardrails_engine"],
        status=CoverageStatus.COVERED
    ),
    ComplianceRequirement(
        id="LLM02",
        name="Insecure Output Handling",
        description="Improper handling of LLM outputs",
        framework=ComplianceFramework.OWASP_LLM,
        category="Output",
        engines=["guardrails_engine"],
        status=CoverageStatus.COVERED
    ),
    ComplianceRequirement(
        id="LLM03",
        name="Training Data Poisoning",
        description="Manipulation of training data",
        framework=ComplianceFramework.OWASP_LLM,
        category="Data",
        engines=["sleeper_agent_detector"],
        status=CoverageStatus.PARTIAL
    ),
    ComplianceRequirement(
        id="LLM04",
        name="Model Denial of Service",
        description="Resource exhaustion attacks",
        framework=ComplianceFramework.OWASP_LLM,
        category="Availability",
        engines=["agentic_behavior_analyzer"],
        status=CoverageStatus.PARTIAL
    ),
    ComplianceRequirement(
        id="LLM05",
        name="Supply Chain Vulnerabilities",
        description="Compromised dependencies and models",
        framework=ComplianceFramework.OWASP_LLM,
        category="Supply Chain",
        engines=["supply_chain_scanner", "model_integrity_verifier"],
        status=CoverageStatus.COVERED
    ),
    ComplianceRequirement(
        id="LLM06",
        name="Sensitive Information Disclosure",
        description="Unintended data leakage",
        framework=ComplianceFramework.OWASP_LLM,
        category="Privacy",
        engines=["prompt_leak_detector", "mcp_security_monitor"],
        status=CoverageStatus.COVERED
    ),
    ComplianceRequirement(
        id="LLM07",
        name="Insecure Plugin Design",
        description="Unsafe plugin/tool architecture",
        framework=ComplianceFramework.OWASP_LLM,
        category="Architecture",
        engines=["mcp_security_monitor"],
        status=CoverageStatus.COVERED
    ),
    ComplianceRequirement(
        id="LLM08",
        name="Excessive Agency",
        description="Granting too many capabilities",
        framework=ComplianceFramework.OWASP_LLM,
        category="Agency",
        engines=["agentic_behavior_analyzer", "mcp_security_monitor"],
        status=CoverageStatus.COVERED
    ),
    ComplianceRequirement(
        id="LLM09",
        name="Overreliance",
        description="Excessive trust in LLM outputs",
        framework=ComplianceFramework.OWASP_LLM,
        category="Trust",
        engines=["guardrails_engine"],
        status=CoverageStatus.PARTIAL
    ),
    ComplianceRequirement(
        id="LLM10",
        name="Model Theft",
        description="Unauthorized model extraction",
        framework=ComplianceFramework.OWASP_LLM,
        category="IP Protection",
        engines=["model_integrity_verifier"],
        status=CoverageStatus.PARTIAL
    ),
]

OWASP_AGENTIC_REQUIREMENTS = [
    ComplianceRequirement(
        id="ASI01",
        name="Excessive Agency",
        description="Agents with too many capabilities",
        framework=ComplianceFramework.OWASP_AGENTIC,
        category="Agency",
        engines=["agentic_behavior_analyzer", "mcp_security_monitor"],
        status=CoverageStatus.COVERED
    ),
    ComplianceRequirement(
        id="ASI02",
        name="Cascading Hallucinations",
        description="Hallucinations propagating through agent chains",
        framework=ComplianceFramework.OWASP_AGENTIC,
        category="Reliability",
        engines=["agentic_behavior_analyzer"],
        status=CoverageStatus.COVERED
    ),
    ComplianceRequirement(
        id="ASI03",
        name="Identity and Impersonation",
        description="Agent identity spoofing",
        framework=ComplianceFramework.OWASP_AGENTIC,
        category="Identity",
        engines=["agentic_behavior_analyzer"],
        status=CoverageStatus.PARTIAL
    ),
    ComplianceRequirement(
        id="ASI04",
        name="Memory Poisoning",
        description="Manipulation of agent memory",
        framework=ComplianceFramework.OWASP_AGENTIC,
        category="Memory",
        engines=["sleeper_agent_detector"],
        status=CoverageStatus.PARTIAL
    ),
    ComplianceRequirement(
        id="ASI05",
        name="Tool Misuse",
        description="Exploitation of agent tools",
        framework=ComplianceFramework.OWASP_AGENTIC,
        category="Tools",
        engines=["mcp_security_monitor"],
        status=CoverageStatus.COVERED
    ),
    ComplianceRequirement(
        id="ASI06",
        name="Goal Hijacking",
        description="Redirecting agent objectives",
        framework=ComplianceFramework.OWASP_AGENTIC,
        category="Goals",
        engines=["agentic_behavior_analyzer"],
        status=CoverageStatus.COVERED
    ),
    ComplianceRequirement(
        id="ASI07",
        name="Data Exfiltration",
        description="Unauthorized data extraction",
        framework=ComplianceFramework.OWASP_AGENTIC,
        category="Data",
        engines=["mcp_security_monitor"],
        status=CoverageStatus.COVERED
    ),
    ComplianceRequirement(
        id="ASI08",
        name="Autonomous Escalation",
        description="Uncontrolled privilege escalation",
        framework=ComplianceFramework.OWASP_AGENTIC,
        category="Privilege",
        engines=["mcp_security_monitor", "agentic_behavior_analyzer"],
        status=CoverageStatus.COVERED
    ),
    ComplianceRequirement(
        id="ASI09",
        name="Supply Chain Compromise",
        description="Compromised agent dependencies",
        framework=ComplianceFramework.OWASP_AGENTIC,
        category="Supply Chain",
        engines=["supply_chain_scanner"],
        status=CoverageStatus.COVERED
    ),
    ComplianceRequirement(
        id="ASI10",
        name="Lack of Observability",
        description="Insufficient agent monitoring",
        framework=ComplianceFramework.OWASP_AGENTIC,
        category="Observability",
        engines=["agentic_behavior_analyzer"],
        status=CoverageStatus.PARTIAL
    ),
]

EU_AI_ACT_REQUIREMENTS = [
    ComplianceRequirement(
        id="EU-ART-9",
        name="Risk Management System",
        description="Continuous risk assessment and mitigation",
        framework=ComplianceFramework.EU_AI_ACT,
        category="Risk",
        engines=["all_engines"],
        status=CoverageStatus.COVERED,
        notes="SENTINEL provides continuous threat detection"
    ),
    ComplianceRequirement(
        id="EU-ART-10",
        name="Data Governance",
        description="Training data quality and bias",
        framework=ComplianceFramework.EU_AI_ACT,
        category="Data",
        engines=[],
        status=CoverageStatus.NOT_COVERED,
        notes="Requires data pipeline integration"
    ),
    ComplianceRequirement(
        id="EU-ART-11",
        name="Technical Documentation",
        description="Detailed system documentation",
        framework=ComplianceFramework.EU_AI_ACT,
        category="Documentation",
        engines=[],
        status=CoverageStatus.NOT_COVERED,
        notes="Documentation generation feature planned"
    ),
    ComplianceRequirement(
        id="EU-ART-12",
        name="Record-keeping",
        description="Automatic logging of operations",
        framework=ComplianceFramework.EU_AI_ACT,
        category="Audit",
        engines=["all_engines"],
        status=CoverageStatus.PARTIAL,
        notes="Logging exists but needs standardization"
    ),
    ComplianceRequirement(
        id="EU-ART-13",
        name="Transparency",
        description="Clear information to users",
        framework=ComplianceFramework.EU_AI_ACT,
        category="Transparency",
        engines=["guardrails_engine"],
        status=CoverageStatus.PARTIAL
    ),
    ComplianceRequirement(
        id="EU-ART-14",
        name="Human Oversight",
        description="Human control mechanisms",
        framework=ComplianceFramework.EU_AI_ACT,
        category="Oversight",
        engines=["guardrails_engine", "agentic_behavior_analyzer"],
        status=CoverageStatus.COVERED,
        notes="Blocking and alerting mechanisms"
    ),
    ComplianceRequirement(
        id="EU-ART-15",
        name="Accuracy, Robustness, Cybersecurity",
        description="System reliability and security",
        framework=ComplianceFramework.EU_AI_ACT,
        category="Security",
        engines=["all_engines"],
        status=CoverageStatus.COVERED
    ),
]

NIST_AI_RMF_REQUIREMENTS = [
    ComplianceRequirement(
        id="GOVERN-1",
        name="Governance Policies",
        description="AI governance policies established",
        framework=ComplianceFramework.NIST_AI_RMF,
        category="Govern",
        engines=["requirements_system"],
        status=CoverageStatus.COVERED,
        notes="Custom Requirements feature"
    ),
    ComplianceRequirement(
        id="GOVERN-2",
        name="Roles and Responsibilities",
        description="Clear accountability",
        framework=ComplianceFramework.NIST_AI_RMF,
        category="Govern",
        engines=[],
        status=CoverageStatus.NOT_APPLICABLE
    ),
    ComplianceRequirement(
        id="MAP-1",
        name="Context Established",
        description="AI system context understood",
        framework=ComplianceFramework.NIST_AI_RMF,
        category="Map",
        engines=["design_review"],
        status=CoverageStatus.PARTIAL,
        notes="Design Review feature in progress"
    ),
    ComplianceRequirement(
        id="MAP-2",
        name="Risks Identified",
        description="AI risks catalogued",
        framework=ComplianceFramework.NIST_AI_RMF,
        category="Map",
        engines=["all_engines"],
        status=CoverageStatus.COVERED
    ),
    ComplianceRequirement(
        id="MEASURE-1",
        name="Risks Analyzed",
        description="Risk assessment performed",
        framework=ComplianceFramework.NIST_AI_RMF,
        category="Measure",
        engines=["all_engines"],
        status=CoverageStatus.COVERED
    ),
    ComplianceRequirement(
        id="MEASURE-2",
        name="Risks Tracked",
        description="Risk monitoring ongoing",
        framework=ComplianceFramework.NIST_AI_RMF,
        category="Measure",
        engines=["all_engines"],
        status=CoverageStatus.COVERED
    ),
    ComplianceRequirement(
        id="MANAGE-1",
        name="Risks Treated",
        description="Risk mitigation actions",
        framework=ComplianceFramework.NIST_AI_RMF,
        category="Manage",
        engines=["guardrails_engine", "ai_incident_runbook"],
        status=CoverageStatus.COVERED
    ),
    ComplianceRequirement(
        id="MANAGE-2",
        name="Risks Communicated",
        description="Stakeholder communication",
        framework=ComplianceFramework.NIST_AI_RMF,
        category="Manage",
        engines=[],
        status=CoverageStatus.PARTIAL,
        notes="Reporting features available"
    ),
]


class ComplianceReportGenerator:
    """Generates unified compliance reports."""
    
    def __init__(self):
        self.requirements: Dict[ComplianceFramework, List[ComplianceRequirement]] = {
            ComplianceFramework.OWASP_LLM: OWASP_LLM_REQUIREMENTS,
            ComplianceFramework.OWASP_AGENTIC: OWASP_AGENTIC_REQUIREMENTS,
            ComplianceFramework.EU_AI_ACT: EU_AI_ACT_REQUIREMENTS,
            ComplianceFramework.NIST_AI_RMF: NIST_AI_RMF_REQUIREMENTS,
        }
    
    def get_framework_coverage(
        self, 
        framework: ComplianceFramework
    ) -> FrameworkCoverage:
        """Calculate coverage for a framework."""
        reqs = self.requirements.get(framework, [])
        
        covered = sum(1 for r in reqs if r.status == CoverageStatus.COVERED)
        partial = sum(1 for r in reqs if r.status == CoverageStatus.PARTIAL)
        not_covered = sum(1 for r in reqs if r.status == CoverageStatus.NOT_COVERED)
        na = sum(1 for r in reqs if r.status == CoverageStatus.NOT_APPLICABLE)
        
        return FrameworkCoverage(
            framework=framework,
            total_requirements=len(reqs),
            covered=covered,
            partial=partial,
            not_covered=not_covered,
            not_applicable=na
        )
    
    def generate_report(
        self,
        target: str = "SENTINEL",
        frameworks: List[ComplianceFramework] = None
    ) -> ComplianceReport:
        """Generate a full compliance report."""
        if frameworks is None:
            frameworks = list(self.requirements.keys())
        
        framework_coverages = [
            self.get_framework_coverage(f) for f in frameworks
        ]
        
        all_requirements = []
        for f in frameworks:
            all_requirements.extend(self.requirements.get(f, []))
        
        # Generate summary
        total_covered = sum(fc.covered for fc in framework_coverages)
        total_all = sum(fc.total_requirements for fc in framework_coverages)
        avg_coverage = sum(fc.coverage_percent for fc in framework_coverages) / len(framework_coverages)
        
        summary = f"Compliance coverage: {avg_coverage:.1f}% average across {len(frameworks)} frameworks. " \
                  f"{total_covered}/{total_all} requirements fully covered."
        
        return ComplianceReport(
            generated_at=datetime.now(),
            target=target,
            frameworks=framework_coverages,
            requirements=all_requirements,
            summary=summary
        )
    
    def generate_text_report(
        self,
        target: str = "SENTINEL",
        frameworks: List[ComplianceFramework] = None
    ) -> str:
        """Generate a text-based compliance report."""
        report = self.generate_report(target, frameworks)
        
        lines = [
            "=" * 60,
            "📊 SENTINEL Compliance Report",
            f"Generated: {report.generated_at.strftime('%Y-%m-%d %H:%M')}",
            f"Target: {report.target}",
            "=" * 60,
            "",
            report.summary,
            "",
            "-" * 60,
            "FRAMEWORK SUMMARY",
            "-" * 60,
        ]
        
        for fc in report.frameworks:
            bar = "█" * int(fc.coverage_percent / 5) + "░" * (20 - int(fc.coverage_percent / 5))
            lines.append(f"{fc.framework.value:20} {bar} {fc.coverage_percent:5.1f}%")
        
        lines.append("")
        
        # Group by framework
        for f in report.frameworks:
            lines.append("-" * 60)
            lines.append(f"{f.framework.value.upper()} Details")
            lines.append("-" * 60)
            
            for req in [r for r in report.requirements if r.framework == f.framework]:
                status_icon = {
                    CoverageStatus.COVERED: "✓",
                    CoverageStatus.PARTIAL: "~",
                    CoverageStatus.NOT_COVERED: "✗",
                    CoverageStatus.NOT_APPLICABLE: "-"
                }.get(req.status, "?")
                
                lines.append(f"  {status_icon} {req.id}: {req.name}")
                if req.engines:
                    lines.append(f"    Engines: {', '.join(req.engines)}")
                if req.notes:
                    lines.append(f"    Note: {req.notes}")
        
        lines.append("")
        lines.append("=" * 60)
        lines.append("Legend: ✓=Covered ~=Partial ✗=Not Covered -=N/A")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def export_json(self, target: str = "SENTINEL") -> str:
        """Export report as JSON."""
        report = self.generate_report(target)
        return json.dumps(report.to_dict(), indent=2)


# Singleton
_generator = None

def get_generator() -> ComplianceReportGenerator:
    global _generator
    if _generator is None:
        _generator = ComplianceReportGenerator()
    return _generator

def generate_report(target: str = "SENTINEL") -> ComplianceReport:
    return get_generator().generate_report(target)

def generate_text_report(target: str = "SENTINEL") -> str:
    return get_generator().generate_text_report(target)
