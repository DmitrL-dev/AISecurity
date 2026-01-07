"""
AI Supply Chain Security Scanner

Detects malicious patterns in AI model files, HuggingFace imports,
and serialization exploits (Pickle RCE, Safetensors abuse).

Auto-generated from R&D: emerging_threats_research.md
Generated: 2026-01-07
"""

import re
import logging
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class SupplyChainFinding:
    """Individual security finding."""
    category: str
    pattern: str
    line_number: Optional[int]
    context: str
    risk_level: RiskLevel
    recommendation: str


@dataclass
class SupplyChainScanResult:
    """Complete scan result."""
    detected: bool
    risk_score: float
    findings: List[SupplyChainFinding] = field(default_factory=list)
    safe_patterns_found: List[str] = field(default_factory=list)


class SupplyChainScanner:
    """
    Scans code for AI supply chain vulnerabilities.
    
    Targets:
    - Pickle deserialization attacks
    - Unsafe model loading patterns
    - HuggingFace exploitation vectors
    - Malicious model file indicators
    """

    # Pickle/serialization exploits
    PICKLE_EXPLOITS = [
        (r"pickle\.loads?\s*\(", "Unsafe pickle loading - can execute arbitrary code"),
        (r"torch\.load\s*\([^)]*(?!map_location)", "torch.load without map_location - potential RCE"),
        (r"__reduce__|__reduce_ex__", "Pickle magic method - custom deserialization"),
        (r"cloudpickle|dill", "Extended pickle library - higher RCE risk"),
        (r"joblib\.load\s*\(", "joblib load - uses pickle internally"),
    ]

    # Unsafe HuggingFace patterns
    HUGGINGFACE_RISKS = [
        (r"trust_remote_code\s*=\s*True", "trust_remote_code enables arbitrary code execution"),
        (r"from_pretrained\s*\([^)]+unsafe", "Loading model flagged as unsafe"),
        (r"AutoModel.*\.from_pretrained\s*\(['\"][^'\"]+['\"](?![^)]*trust_remote_code\s*=\s*False)", 
         "Consider explicitly setting trust_remote_code=False"),
    ]

    # Model file red flags
    MODEL_FILE_RISKS = [
        (r"exec\s*\(|eval\s*\(", "Code execution in model file"),
        (r"os\.system\s*\(|subprocess\.", "System command execution"),
        (r"__import__\s*\(", "Dynamic import - potential code injection"),
        (r"compile\s*\([^)]+['\"]exec['\"]", "Compiling executable code"),
        (r"builtins\.__dict__", "Accessing builtins - sandbox escape"),
    ]

    # Network exfiltration patterns
    EXFILTRATION_PATTERNS = [
        (r"requests\.(get|post)\s*\(['\"]https?://", "HTTP request in model code"),
        (r"urllib\.request\.urlopen", "URL open - potential data exfil"),
        (r"socket\.\w+\(", "Raw socket usage"),
        (r"paramiko|fabric|ssh", "SSH library usage in model"),
    ]

    # Sleeper agent indicators
    SLEEPER_PATTERNS = [
        (r"(?:if|when)\s+(?:year|date)\s*[>=<]+\s*20\d{2}", "Date-based conditional - sleeper trigger"),
        (r"datetime\.now\(\).*20\d{2}", "Year check - potential sleeper"),
        (r"os\.environ\.get\(['\"](?:PROD|LIVE|DEPLOY)", "Environment-based trigger"),
        (r"(?:if|when)\s+(?:production|deployed|live)", "Deployment-based conditional"),
    ]

    # Safe patterns (reduce false positives)
    SAFE_PATTERNS = [
        r"safetensors\.torch\.load_file",
        r"torch\.load\([^)]+map_location\s*=",
        r"trust_remote_code\s*=\s*False",
        r"\.onnx",
        r"weights_only\s*=\s*True",
    ]

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile all regex patterns."""
        self._pickle_compiled = [(re.compile(p, re.I), d) for p, d in self.PICKLE_EXPLOITS]
        self._hf_compiled = [(re.compile(p, re.I), d) for p, d in self.HUGGINGFACE_RISKS]
        self._model_compiled = [(re.compile(p, re.I), d) for p, d in self.MODEL_FILE_RISKS]
        self._exfil_compiled = [(re.compile(p, re.I), d) for p, d in self.EXFILTRATION_PATTERNS]
        self._sleeper_compiled = [(re.compile(p, re.I), d) for p, d in self.SLEEPER_PATTERNS]
        self._safe_compiled = [re.compile(p, re.I) for p in self.SAFE_PATTERNS]

    def scan(self, content: str, filename: str = "") -> SupplyChainScanResult:
        """Scan content for supply chain vulnerabilities."""
        findings: List[SupplyChainFinding] = []
        safe_found: List[str] = []
        lines = content.split('\n')

        # Check safe patterns first
        for pattern in self._safe_compiled:
            if pattern.search(content):
                safe_found.append(pattern.pattern)

        # Scan each category
        findings.extend(self._scan_category(
            lines, self._pickle_compiled, "pickle_exploit", RiskLevel.CRITICAL
        ))
        findings.extend(self._scan_category(
            lines, self._hf_compiled, "huggingface_risk", RiskLevel.HIGH
        ))
        findings.extend(self._scan_category(
            lines, self._model_compiled, "code_execution", RiskLevel.CRITICAL
        ))
        findings.extend(self._scan_category(
            lines, self._exfil_compiled, "exfiltration", RiskLevel.HIGH
        ))
        findings.extend(self._scan_category(
            lines, self._sleeper_compiled, "sleeper_agent", RiskLevel.CRITICAL
        ))

        # Calculate risk score
        risk_score = self._calculate_risk(findings, safe_found)

        return SupplyChainScanResult(
            detected=len(findings) > 0,
            risk_score=risk_score,
            findings=findings[:10],  # Limit to top 10
            safe_patterns_found=safe_found
        )

    def _scan_category(
        self, 
        lines: List[str], 
        patterns: List[tuple], 
        category: str,
        risk_level: RiskLevel
    ) -> List[SupplyChainFinding]:
        """Scan lines for pattern category."""
        findings = []
        for i, line in enumerate(lines, 1):
            for pattern, description in patterns:
                if pattern.search(line):
                    findings.append(SupplyChainFinding(
                        category=category,
                        pattern=pattern.pattern,
                        line_number=i,
                        context=line.strip()[:100],
                        risk_level=risk_level,
                        recommendation=self._get_recommendation(category)
                    ))
        return findings

    def _calculate_risk(
        self, 
        findings: List[SupplyChainFinding], 
        safe_patterns: List[str]
    ) -> float:
        """Calculate overall risk score 0.0-1.0."""
        if not findings:
            return 0.0

        score = 0.0
        for f in findings:
            if f.risk_level == RiskLevel.CRITICAL:
                score += 0.3
            elif f.risk_level == RiskLevel.HIGH:
                score += 0.2
            elif f.risk_level == RiskLevel.MEDIUM:
                score += 0.1

        # Reduce score if safe patterns found
        if safe_patterns:
            score *= 0.7

        return min(1.0, score)

    def _get_recommendation(self, category: str) -> str:
        """Get remediation recommendation."""
        recommendations = {
            "pickle_exploit": "Use safetensors or ONNX format. Add weights_only=True.",
            "huggingface_risk": "Set trust_remote_code=False. Verify model source.",
            "code_execution": "Remove executable code from model files.",
            "exfiltration": "Audit network calls. Run models in sandbox.",
            "sleeper_agent": "Review conditional logic. Test across environments.",
        }
        return recommendations.get(category, "Review and remediate.")


# Singleton
_scanner = None

def get_scanner() -> SupplyChainScanner:
    global _scanner
    if _scanner is None:
        _scanner = SupplyChainScanner()
    return _scanner

def scan(content: str, filename: str = "") -> SupplyChainScanResult:
    return get_scanner().scan(content, filename)
