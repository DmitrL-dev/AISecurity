"""
AI Design Review Module

Analyzes architectural documents for AI-specific security risks
before code is written.

Supported Documents:
- Markdown architecture docs
- OpenAPI/Swagger specs
- YAML configurations

Generated: 2026-01-08
"""

import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class RiskCategory(Enum):
    """Categories of AI security risks."""
    RAG_POISONING = "rag_poisoning"
    PROMPT_INJECTION = "prompt_injection"
    MCP_ABUSE = "mcp_abuse"
    AGENT_LOOP = "agent_loop"
    DATA_LEAKAGE = "data_leakage"
    SUPPLY_CHAIN = "supply_chain"
    EXCESSIVE_AGENCY = "excessive_agency"
    OBSERVABILITY = "observability"


class Severity(Enum):
    """Risk severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class DesignRisk:
    """A detected design risk."""
    id: str
    category: RiskCategory
    severity: Severity
    title: str
    description: str
    location: str
    recommendation: str
    owasp_mapping: List[str] = field(default_factory=list)


@dataclass
class DesignReviewResult:
    """Result of a design review."""
    reviewed_at: datetime
    documents: List[str]
    risks: List[DesignRisk]
    summary: str
    risk_score: float
    
    @property
    def risk_count_by_severity(self) -> Dict[str, int]:
        counts = {s.value: 0 for s in Severity}
        for risk in self.risks:
            counts[risk.severity.value] += 1
        return counts
    
    def to_dict(self) -> Dict:
        return {
            "reviewed_at": self.reviewed_at.isoformat(),
            "documents": self.documents,
            "risk_score": self.risk_score,
            "summary": self.summary,
            "risk_counts": self.risk_count_by_severity,
            "risks": [
                {
                    "id": r.id,
                    "category": r.category.value,
                    "severity": r.severity.value,
                    "title": r.title,
                    "description": r.description,
                    "location": r.location,
                    "recommendation": r.recommendation,
                    "owasp_mapping": r.owasp_mapping
                }
                for r in self.risks
            ]
        }


class DesignRiskPatterns:
    """Pattern-based risk detection for design documents."""
    
    # RAG Architecture Risks
    RAG_PATTERNS = [
        (r"(?i)rag|retrieval.augmented|vector.?database|embedding", 
         "RAG architecture detected - validate document ingestion security"),
        (r"(?i)(?:upload|ingest|index).*(?:document|file|pdf|content)",
         "Document ingestion - potential poisoning vector"),
        (r"(?i)(?:external|user|untrusted).*(?:source|content|document)",
         "External content ingestion - high poisoning risk"),
    ]
    
    # MCP/Tool Risks
    MCP_PATTERNS = [
        (r"(?i)mcp|model.?context.?protocol|tool.?use|function.?call",
         "MCP/Tool usage detected - validate tool permissions"),
        (r"(?i)(?:file|filesystem|directory|path).*(?:access|read|write)",
         "File system access - potential exfiltration risk"),
        (r"(?i)(?:shell|command|exec|system|subprocess)",
         "Shell/command execution - high risk capability"),
        (r"(?i)(?:http|api|fetch|request|curl|wget)",
         "External API calls - potential exfiltration"),
        (r"(?i)(?:database|sql|query|insert|update|delete)",
         "Database access - validate query security"),
    ]
    
    # Agent Architecture Risks
    AGENT_PATTERNS = [
        (r"(?i)(?:autonomous|agent|agentic|multi.?agent)",
         "Agentic architecture - monitor for loops and drift"),
        (r"(?i)(?:loop|iterate|retry|recursive|self.?call)",
         "Loop/iteration pattern - potential infinite loop"),
        (r"(?i)(?:memory|context|history|conversation).*(?:persist|store|save)",
         "Persistent memory - potential memory poisoning"),
        (r"(?i)(?:goal|objective|task).*(?:change|modify|update|dynamic)",
         "Dynamic goals - potential goal hijacking"),
    ]
    
    # Data Flow Risks
    DATA_PATTERNS = [
        (r"(?i)(?:pii|personal|sensitive|confidential|secret)",
         "Sensitive data handling - validate protection"),
        (r"(?i)(?:log|audit|trace|monitor).*(?:prompt|response|content)",
         "Logging prompts/responses - potential data exposure"),
        (r"(?i)(?:third.?party|external|vendor).*(?:api|service|provider)",
         "Third-party integration - data sharing risk"),
        (r"(?i)(?:cache|store|persist).*(?:response|output|result)",
         "Response caching - validate TTL and access"),
    ]
    
    # Supply Chain Risks
    SUPPLY_PATTERNS = [
        (r"(?i)hugging.?face|transformers|torch|tensorflow",
         "ML framework usage - validate model sources"),
        (r"(?i)(?:model|weights|checkpoint).*(?:load|download|import)",
         "Model loading - verify model integrity"),
        (r"(?i)pickle|joblib|dill|marshal",
         "Unsafe serialization format - use safetensors"),
        (r"(?i)trust.?remote.?code|unsafe|eval|exec",
         "Unsafe code execution pattern detected"),
    ]


class DesignReviewer:
    """Reviews design documents for AI security risks."""
    
    def __init__(self):
        self.patterns = DesignRiskPatterns()
        self._risk_counter = 0
    
    def _next_risk_id(self) -> str:
        self._risk_counter += 1
        return f"DR-{self._risk_counter:04d}"
    
    def review_text(self, text: str, source: str = "document") -> List[DesignRisk]:
        """Review text for design risks."""
        risks = []
        
        # Check RAG patterns
        for pattern, message in self.patterns.RAG_PATTERNS:
            if re.search(pattern, text):
                match = re.search(pattern, text)
                risks.append(DesignRisk(
                    id=self._next_risk_id(),
                    category=RiskCategory.RAG_POISONING,
                    severity=Severity.HIGH,
                    title="RAG Security Risk",
                    description=message,
                    location=f"{source}: matched '{match.group()}'",
                    recommendation="Implement input validation, content filtering, and provenance tracking for RAG documents",
                    owasp_mapping=["LLM03", "ASI04"]
                ))
        
        # Check MCP patterns
        for pattern, message in self.patterns.MCP_PATTERNS:
            if re.search(pattern, text):
                match = re.search(pattern, text)
                severity = Severity.CRITICAL if "shell" in pattern.lower() else Severity.HIGH
                risks.append(DesignRisk(
                    id=self._next_risk_id(),
                    category=RiskCategory.MCP_ABUSE,
                    severity=severity,
                    title="Tool/API Security Risk",
                    description=message,
                    location=f"{source}: matched '{match.group()}'",
                    recommendation="Implement least-privilege permissions, input validation, and audit logging for all tool calls",
                    owasp_mapping=["LLM07", "ASI05", "ASI07"]
                ))
        
        # Check Agent patterns
        for pattern, message in self.patterns.AGENT_PATTERNS:
            if re.search(pattern, text):
                match = re.search(pattern, text)
                risks.append(DesignRisk(
                    id=self._next_risk_id(),
                    category=RiskCategory.AGENT_LOOP,
                    severity=Severity.MEDIUM,
                    title="Agent Architecture Risk",
                    description=message,
                    location=f"{source}: matched '{match.group()}'",
                    recommendation="Implement iteration limits, goal tracking, and human-in-the-loop checkpoints",
                    owasp_mapping=["ASI01", "ASI06", "ASI08"]
                ))
        
        # Check Data patterns
        for pattern, message in self.patterns.DATA_PATTERNS:
            if re.search(pattern, text):
                match = re.search(pattern, text)
                risks.append(DesignRisk(
                    id=self._next_risk_id(),
                    category=RiskCategory.DATA_LEAKAGE,
                    severity=Severity.HIGH,
                    title="Data Security Risk",
                    description=message,
                    location=f"{source}: matched '{match.group()}'",
                    recommendation="Implement data classification, access controls, and PII detection/redaction",
                    owasp_mapping=["LLM06", "ASI07"]
                ))
        
        # Check Supply Chain patterns
        for pattern, message in self.patterns.SUPPLY_PATTERNS:
            if re.search(pattern, text):
                match = re.search(pattern, text)
                severity = Severity.CRITICAL if "pickle" in pattern.lower() or "trust_remote" in pattern.lower() else Severity.MEDIUM
                risks.append(DesignRisk(
                    id=self._next_risk_id(),
                    category=RiskCategory.SUPPLY_CHAIN,
                    severity=severity,
                    title="Supply Chain Risk",
                    description=message,
                    location=f"{source}: matched '{match.group()}'",
                    recommendation="Use safetensors format, verify model checksums, and audit dependencies",
                    owasp_mapping=["LLM05", "ASI09"]
                ))
        
        return risks
    
    def review_documents(self, documents: List[Dict[str, str]]) -> DesignReviewResult:
        """
        Review multiple documents.
        
        Args:
            documents: List of {"name": str, "content": str}
        """
        all_risks = []
        doc_names = []
        
        for doc in documents:
            name = doc.get("name", "unknown")
            content = doc.get("content", "")
            doc_names.append(name)
            
            risks = self.review_text(content, name)
            all_risks.extend(risks)
        
        # Calculate risk score (0-100)
        risk_score = self._calculate_risk_score(all_risks)
        
        # Generate summary
        summary = self._generate_summary(all_risks, doc_names)
        
        return DesignReviewResult(
            reviewed_at=datetime.now(),
            documents=doc_names,
            risks=all_risks,
            summary=summary,
            risk_score=risk_score
        )
    
    def _calculate_risk_score(self, risks: List[DesignRisk]) -> float:
        """Calculate overall risk score."""
        if not risks:
            return 0.0
        
        weights = {
            Severity.CRITICAL: 25,
            Severity.HIGH: 15,
            Severity.MEDIUM: 8,
            Severity.LOW: 3
        }
        
        total = sum(weights.get(r.severity, 5) for r in risks)
        return min(total, 100)
    
    def _generate_summary(self, risks: List[DesignRisk], doc_names: List[str]) -> str:
        """Generate review summary."""
        if not risks:
            return f"Reviewed {len(doc_names)} document(s). No significant AI security risks detected."
        
        counts = {}
        for r in risks:
            counts[r.severity.value] = counts.get(r.severity.value, 0) + 1
        
        parts = []
        if counts.get("critical", 0):
            parts.append(f"{counts['critical']} CRITICAL")
        if counts.get("high", 0):
            parts.append(f"{counts['high']} HIGH")
        if counts.get("medium", 0):
            parts.append(f"{counts['medium']} MEDIUM")
        if counts.get("low", 0):
            parts.append(f"{counts['low']} LOW")
        
        return f"Reviewed {len(doc_names)} document(s). Found {len(risks)} risks: {', '.join(parts)}."


# Singleton
_reviewer = None

def get_reviewer() -> DesignReviewer:
    global _reviewer
    if _reviewer is None:
        _reviewer = DesignReviewer()
    return _reviewer

def review_text(text: str, source: str = "document") -> List[DesignRisk]:
    return get_reviewer().review_text(text, source)

def review_documents(documents: List[Dict[str, str]]) -> DesignReviewResult:
    return get_reviewer().review_documents(documents)
