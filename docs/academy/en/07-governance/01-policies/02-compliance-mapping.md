# Compliance Mapping for AI Systems

> **Level:** Advanced  
> **Time:** 45 minutes  
> **Track:** 07 — Governance  
> **Module:** 07.1 — Policies  
> **Version:** 1.0

---

## Learning Objectives

- [ ] Understand compliance frameworks for AI systems
- [ ] Implement mapping policies → compliance controls
- [ ] Build compliance reporting
- [ ] Integrate compliance tracking into SENTINEL

---

## 1. Compliance Frameworks Overview

### 1.1 Major Frameworks

```
┌────────────────────────────────────────────────────────────────────┐
│              AI COMPLIANCE LANDSCAPE                                │
├────────────────────────────────────────────────────────────────────┤
│                                                                    │
│  EU AI Act                                                         │
│  ├── Risk-based classification                                    │
│  ├── Transparency requirements                                    │
│  └── Human oversight mandates                                     │
│                                                                    │
│  NIST AI RMF                                                       │
│  ├── Govern, Map, Measure, Manage                                 │
│  ├── AI system risk assessment                                    │
│  └── Trustworthy AI characteristics                               │
│                                                                    │
│  ISO/IEC 42001                                                     │
│  ├── AI Management System                                         │
│  ├── Governance and accountability                                │
│  └── Continuous improvement                                       │
│                                                                    │
│  Industry-Specific                                                 │
│  ├── HIPAA (Healthcare AI)                                        │
│  ├── SOC 2 (Cloud AI Services)                                    │
│  └── PCI-DSS (Financial AI)                                       │
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 2. Compliance Model

### 2.1 Core Entities

```python
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
from datetime import datetime

class Framework(Enum):
    EU_AI_ACT = "eu_ai_act"
    NIST_AI_RMF = "nist_ai_rmf"
    ISO_42001 = "iso_42001"
    HIPAA = "hipaa"
    SOC2 = "soc2"
    PCI_DSS = "pci_dss"
    CUSTOM = "custom"

class ControlStatus(Enum):
    NOT_IMPLEMENTED = "not_implemented"
    PARTIAL = "partial"
    IMPLEMENTED = "implemented"
    NOT_APPLICABLE = "not_applicable"

class RiskLevel(Enum):
    UNACCEPTABLE = "unacceptable"  # EU AI Act: Prohibited
    HIGH = "high"
    LIMITED = "limited"
    MINIMAL = "minimal"

@dataclass
class ComplianceControl:
    """Single compliance control"""
    control_id: str
    framework: Framework
    title: str
    description: str
    requirements: List[str] = field(default_factory=list)
    
    # Status
    status: ControlStatus = ControlStatus.NOT_IMPLEMENTED
    implementation_notes: str = ""
    
    # Evidence
    evidence_links: List[str] = field(default_factory=list)
    policy_mappings: List[str] = field(default_factory=list)
    
    # Metadata
    last_assessed: Optional[datetime] = None
    assessor: str = ""

@dataclass
class ComplianceFramework:
    """Complete compliance framework"""
    framework_id: str
    name: str
    version: str
    controls: List[ComplianceControl] = field(default_factory=list)
    
    def get_control(self, control_id: str) -> Optional[ComplianceControl]:
        for c in self.controls:
            if c.control_id == control_id:
                return c
        return None
    
    def get_compliance_score(self) -> float:
        if not self.controls:
            return 0.0
        
        implemented = sum(1 for c in self.controls 
                        if c.status == ControlStatus.IMPLEMENTED)
        applicable = sum(1 for c in self.controls 
                        if c.status != ControlStatus.NOT_APPLICABLE)
        
        return implemented / applicable if applicable > 0 else 0.0
```

### 2.2 Framework Definitions

```python
class FrameworkLibrary:
    """Library of compliance frameworks"""
    
    @staticmethod
    def get_eu_ai_act() -> ComplianceFramework:
        """EU AI Act compliance framework"""
        return ComplianceFramework(
            framework_id="eu_ai_act_2024",
            name="EU AI Act",
            version="2024",
            controls=[
                ComplianceControl(
                    control_id="EU-AI-1",
                    framework=Framework.EU_AI_ACT,
                    title="Risk Classification",
                    description="Classify AI system by risk level",
                    requirements=[
                        "Perform risk assessment",
                        "Document risk classification",
                        "Review classification periodically"
                    ]
                ),
                ComplianceControl(
                    control_id="EU-AI-2", 
                    framework=Framework.EU_AI_ACT,
                    title="Transparency",
                    description="Ensure AI system transparency",
                    requirements=[
                        "Inform users of AI interaction",
                        "Provide explanations for decisions",
                        "Document training data sources"
                    ]
                ),
                ComplianceControl(
                    control_id="EU-AI-3",
                    framework=Framework.EU_AI_ACT,
                    title="Human Oversight",
                    description="Implement human oversight mechanisms",
                    requirements=[
                        "Enable human intervention",
                        "Provide override capabilities",
                        "Log oversight actions"
                    ]
                ),
                ComplianceControl(
                    control_id="EU-AI-4",
                    framework=Framework.EU_AI_ACT,
                    title="Data Governance",
                    description="Ensure proper data governance",
                    requirements=[
                        "Document data sources",
                        "Implement data quality checks",
                        "Maintain data lineage"
                    ]
                ),
                ComplianceControl(
                    control_id="EU-AI-5",
                    framework=Framework.EU_AI_ACT,
                    title="Technical Documentation",
                    description="Maintain technical documentation",
                    requirements=[
                        "Document system architecture",
                        "Describe training methodology",
                        "Record testing procedures"
                    ]
                )
            ]
        )
    
    @staticmethod
    def get_nist_ai_rmf() -> ComplianceFramework:
        """NIST AI Risk Management Framework"""
        return ComplianceFramework(
            framework_id="nist_ai_rmf_1_0",
            name="NIST AI RMF",
            version="1.0",
            controls=[
                ComplianceControl(
                    control_id="GOVERN-1",
                    framework=Framework.NIST_AI_RMF,
                    title="Governance Structure",
                    description="Establish AI governance structure",
                    requirements=[
                        "Define roles and responsibilities",
                        "Establish oversight mechanisms",
                        "Create accountability framework"
                    ]
                ),
                ComplianceControl(
                    control_id="MAP-1",
                    framework=Framework.NIST_AI_RMF,
                    title="Context Mapping",
                    description="Map AI system context and impacts",
                    requirements=[
                        "Identify stakeholders",
                        "Document use cases",
                        "Assess potential impacts"
                    ]
                ),
                ComplianceControl(
                    control_id="MEASURE-1",
                    framework=Framework.NIST_AI_RMF,
                    title="Risk Measurement",
                    description="Measure and track AI risks",
                    requirements=[
                        "Define risk metrics",
                        "Implement monitoring",
                        "Track risk indicators"
                    ]
                ),
                ComplianceControl(
                    control_id="MANAGE-1",
                    framework=Framework.NIST_AI_RMF,
                    title="Risk Management",
                    description="Manage identified risks",
                    requirements=[
                        "Prioritize risks",
                        "Implement mitigations",
                        "Review effectiveness"
                    ]
                )
            ]
        )
```

---

## 3. Policy-to-Control Mapping

### 3.1 Mapping Engine

```python
@dataclass
class PolicyControlMapping:
    """Mapping between policy and compliance control"""
    mapping_id: str
    policy_id: str
    control_id: str
    framework: Framework
    coverage: float  # 0-1, how much of control is covered
    notes: str = ""

class ComplianceMappingEngine:
    """Maps policies to compliance controls"""
    
    def __init__(self):
        self.mappings: List[PolicyControlMapping] = []
        self.frameworks: Dict[str, ComplianceFramework] = {}
    
    def add_framework(self, framework: ComplianceFramework):
        self.frameworks[framework.framework_id] = framework
    
    def add_mapping(self, mapping: PolicyControlMapping):
        self.mappings.append(mapping)
    
    def get_mappings_for_policy(self, policy_id: str) -> List[PolicyControlMapping]:
        return [m for m in self.mappings if m.policy_id == policy_id]
    
    def get_mappings_for_control(self, control_id: str) -> List[PolicyControlMapping]:
        return [m for m in self.mappings if m.control_id == control_id]
    
    def calculate_control_coverage(self, control_id: str) -> float:
        """Calculate total coverage for a control from all mapped policies"""
        mappings = self.get_mappings_for_control(control_id)
        if not mappings:
            return 0.0
        
        # Sum coverage, capped at 1.0
        total = sum(m.coverage for m in mappings)
        return min(total, 1.0)
    
    def get_framework_coverage(self, framework_id: str) -> Dict[str, float]:
        """Get coverage for all controls in a framework"""
        framework = self.frameworks.get(framework_id)
        if not framework:
            return {}
        
        return {
            c.control_id: self.calculate_control_coverage(c.control_id)
            for c in framework.controls
        }
    
    def find_gaps(self, framework_id: str, threshold: float = 0.8) -> List[str]:
        """Find controls with insufficient coverage"""
        coverage = self.get_framework_coverage(framework_id)
        return [cid for cid, cov in coverage.items() if cov < threshold]
```

### 3.2 Auto-Mapping

```python
class AutoMapper:
    """Automatic policy-to-control mapping suggestions"""
    
    def __init__(self):
        # Keywords for each control category
        self.control_keywords = {
            "transparency": ["log", "audit", "record", "document", "explain"],
            "human_oversight": ["approval", "review", "human", "override", "intervene"],
            "data_governance": ["data", "privacy", "retention", "quality", "source"],
            "access_control": ["permission", "role", "access", "authorize", "deny"],
            "risk_management": ["risk", "threat", "vulnerability", "mitigate", "assess"]
        }
    
    def suggest_mappings(self, policy: 'Policy', 
                         framework: ComplianceFramework) -> List[PolicyControlMapping]:
        """Suggest mappings based on policy content"""
        suggestions = []
        
        policy_text = self._extract_policy_text(policy)
        
        for control in framework.controls:
            score = self._calculate_relevance(policy_text, control)
            
            if score > 0.3:  # Threshold for suggestion
                suggestions.append(PolicyControlMapping(
                    mapping_id=f"auto_{policy.policy_id}_{control.control_id}",
                    policy_id=policy.policy_id,
                    control_id=control.control_id,
                    framework=control.framework,
                    coverage=score,
                    notes="Auto-suggested mapping"
                ))
        
        return suggestions
    
    def _extract_policy_text(self, policy: 'Policy') -> str:
        """Extract searchable text from policy"""
        parts = [policy.name, policy.description]
        for rule in policy.rules:
            parts.append(rule.description)
            parts.extend(rule.actions)
        return " ".join(parts).lower()
    
    def _calculate_relevance(self, policy_text: str, 
                            control: ComplianceControl) -> float:
        """Calculate relevance score"""
        control_text = f"{control.title} {control.description}".lower()
        
        # Simple keyword matching
        policy_words = set(policy_text.split())
        control_words = set(control_text.split())
        
        common = policy_words & control_words
        if not control_words:
            return 0.0
        
        return len(common) / len(control_words)
```

---

## 4. Compliance Reporting

### 4.1 Report Generator

```python
@dataclass
class ComplianceReport:
    """Compliance status report"""
    framework_id: str
    framework_name: str
    generated_at: datetime
    
    # Summary
    total_controls: int
    implemented: int
    partial: int
    not_implemented: int
    not_applicable: int
    
    # Score
    compliance_score: float
    
    # Details
    control_details: List[Dict]
    gaps: List[str]
    recommendations: List[str]

class ComplianceReporter:
    """Generates compliance reports"""
    
    def __init__(self, mapping_engine: ComplianceMappingEngine):
        self.engine = mapping_engine
    
    def generate_report(self, framework_id: str) -> ComplianceReport:
        """Generate compliance report for framework"""
        framework = self.engine.frameworks.get(framework_id)
        if not framework:
            raise ValueError(f"Framework {framework_id} not found")
        
        # Count statuses
        status_counts = {s: 0 for s in ControlStatus}
        control_details = []
        
        for control in framework.controls:
            status_counts[control.status] += 1
            coverage = self.engine.calculate_control_coverage(control.control_id)
            
            control_details.append({
                'control_id': control.control_id,
                'title': control.title,
                'status': control.status.value,
                'coverage': coverage,
                'mappings': len(self.engine.get_mappings_for_control(control.control_id))
            })
        
        # Find gaps
        gaps = self.engine.find_gaps(framework_id, threshold=0.8)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(framework, gaps)
        
        return ComplianceReport(
            framework_id=framework_id,
            framework_name=framework.name,
            generated_at=datetime.utcnow(),
            total_controls=len(framework.controls),
            implemented=status_counts[ControlStatus.IMPLEMENTED],
            partial=status_counts[ControlStatus.PARTIAL],
            not_implemented=status_counts[ControlStatus.NOT_IMPLEMENTED],
            not_applicable=status_counts[ControlStatus.NOT_APPLICABLE],
            compliance_score=framework.get_compliance_score(),
            control_details=control_details,
            gaps=gaps,
            recommendations=recommendations
        )
    
    def _generate_recommendations(self, framework: ComplianceFramework,
                                  gaps: List[str]) -> List[str]:
        """Generate recommendations for gaps"""
        recommendations = []
        
        for gap_id in gaps[:5]:  # Top 5 gaps
            control = framework.get_control(gap_id)
            if control:
                recommendations.append(
                    f"Implement policies covering: {control.title} - {control.description}"
                )
        
        return recommendations
    
    def export_report(self, report: ComplianceReport, format: str = "json") -> str:
        """Export report to specified format"""
        import json
        
        data = {
            'framework': report.framework_name,
            'generated_at': report.generated_at.isoformat(),
            'compliance_score': round(report.compliance_score * 100, 1),
            'summary': {
                'total': report.total_controls,
                'implemented': report.implemented,
                'partial': report.partial,
                'not_implemented': report.not_implemented
            },
            'gaps': report.gaps,
            'recommendations': report.recommendations,
            'controls': report.control_details
        }
        
        if format == "json":
            return json.dumps(data, indent=2)
        else:
            raise ValueError(f"Unsupported format: {format}")
```

---

## 5. SENTINEL Integration

```python
from dataclasses import dataclass

@dataclass
class ComplianceConfig:
    """Compliance engine configuration"""
    enabled_frameworks: List[str] = field(default_factory=lambda: ["eu_ai_act", "nist_ai_rmf"])
    auto_mapping: bool = True
    gap_threshold: float = 0.8

class SENTINELComplianceEngine:
    """Compliance engine for SENTINEL"""
    
    def __init__(self, config: ComplianceConfig):
        self.config = config
        self.mapping_engine = ComplianceMappingEngine()
        self.reporter = ComplianceReporter(self.mapping_engine)
        self.auto_mapper = AutoMapper()
        
        # Load enabled frameworks
        self._load_frameworks()
    
    def _load_frameworks(self):
        if "eu_ai_act" in self.config.enabled_frameworks:
            self.mapping_engine.add_framework(FrameworkLibrary.get_eu_ai_act())
        if "nist_ai_rmf" in self.config.enabled_frameworks:
            self.mapping_engine.add_framework(FrameworkLibrary.get_nist_ai_rmf())
    
    def map_policy(self, policy: 'Policy', auto: bool = None):
        """Map policy to compliance controls"""
        use_auto = auto if auto is not None else self.config.auto_mapping
        
        if use_auto:
            for fw in self.mapping_engine.frameworks.values():
                suggestions = self.auto_mapper.suggest_mappings(policy, fw)
                for mapping in suggestions:
                    self.mapping_engine.add_mapping(mapping)
    
    def add_mapping(self, policy_id: str, control_id: str,
                    framework: str, coverage: float):
        """Manually add mapping"""
        mapping = PolicyControlMapping(
            mapping_id=f"manual_{policy_id}_{control_id}",
            policy_id=policy_id,
            control_id=control_id,
            framework=Framework(framework),
            coverage=coverage,
            notes="Manual mapping"
        )
        self.mapping_engine.add_mapping(mapping)
    
    def get_report(self, framework_id: str) -> ComplianceReport:
        """Generate compliance report"""
        return self.reporter.generate_report(framework_id)
    
    def get_gaps(self, framework_id: str) -> List[str]:
        """Get compliance gaps"""
        return self.mapping_engine.find_gaps(framework_id, self.config.gap_threshold)
    
    def get_all_frameworks(self) -> List[Dict]:
        """List all frameworks with status"""
        return [
            {
                'id': fw.framework_id,
                'name': fw.name,
                'controls': len(fw.controls),
                'score': fw.get_compliance_score()
            }
            for fw in self.mapping_engine.frameworks.values()
        ]
```

---

## 6. Summary

| Component | Description |
|-----------|-------------|
| **Control** | Unit of compliance requirement |
| **Framework** | Set of controls (EU AI Act, NIST) |
| **Mapping** | Policy → control link |
| **Coverage** | Degree of control coverage |
| **Report** | Compliance status report |

---

## Next Lesson

→ [Module 07.2: Audit Trail](../02-audit/README.md)

---

*AI Security Academy | Track 07: Governance | Module 07.1: Policies*
