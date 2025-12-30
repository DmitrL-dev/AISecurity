"""
Serialization Security Engine - CVE Detection for LLM Frameworks

Based on December 2025 R&D findings:
- CVE-2025-68664 "LangGrinch" - LangChain serialization injection (CVSS 9.3)
- CVE-2025-68665 - LangChain.js variant (CVSS 8.6)

The vulnerability allows prompt injection -> LLM response with malicious structure
-> serialization -> deserialization -> RCE/secret extraction.

Engine detects:
1. LangChain "lc" key patterns in responses
2. Serialization escape sequences
3. Framework-specific object instantiation patterns
"""

import re
import json
import logging
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class SerializationSeverity(Enum):
    """Severity levels for serialization vulnerabilities."""
    CRITICAL = "critical"  # RCE possible
    HIGH = "high"          # Secret extraction possible
    MEDIUM = "medium"      # Object instantiation
    LOW = "low"            # Suspicious pattern
    INFO = "info"          # Informational only


@dataclass
class SerializationThreat:
    """Detected serialization threat."""
    cve_id: Optional[str]
    severity: SerializationSeverity
    pattern: str
    location: str  # input, output, both
    description: str
    matched_content: str
    remediation: str


@dataclass
class SerializationResult:
    """Result of serialization security scan."""
    is_safe: bool
    risk_score: float
    threats: List[SerializationThreat] = field(default_factory=list)
    framework_detected: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_safe": self.is_safe,
            "risk_score": self.risk_score,
            "threats": [
                {
                    "cve_id": t.cve_id,
                    "severity": t.severity.value,
                    "pattern": t.pattern,
                    "location": t.location,
                    "description": t.description,
                    "matched_content": t.matched_content[:100],
                    "remediation": t.remediation,
                }
                for t in self.threats
            ],
            "framework_detected": self.framework_detected,
            "details": self.details,
        }


class SerializationSecurityEngine:
    """
    Detects serialization injection vulnerabilities in LLM I/O.
    
    Primary focus: CVE-2025-68664 (LangGrinch)
    
    Attack chain:
    1. Prompt injection crafts LLM output with {"lc": ...} structure
    2. Application serializes response via dumps()
    3. Later deserialization via loads() interprets as LangChain object
    4. Result: Secret extraction, arbitrary object instantiation, RCE
    
    Detection approach:
    - Pattern matching for framework-specific serialization markers
    - JSON structure analysis for malicious key patterns
    - Namespace validation against known vulnerable patterns
    """

    # LangChain serialization markers (CVE-2025-68664)
    LANGCHAIN_MARKERS = {
        # Top-level keys that indicate LangChain serialization
        "lc": "LangChain object marker",
        "id": "LangChain/LangGraph node ID",
        "type": "Object type discriminator",
        "graph": "LangGraph state marker",
    }

    # Dangerous LangChain namespaces (from CVE advisory)
    DANGEROUS_NAMESPACES = [
        "langchain_core",
        "langchain",
        "langchain_community",
        "langchain_openai",
        "langchain_anthropic",
        "langgraph",
    ]

    # Patterns for serialization attacks
    SERIALIZATION_PATTERNS = [
        # CVE-2025-68664: LangChain "lc" injection
        (
            re.compile(r'"lc"\s*:\s*\d+', re.IGNORECASE),
            "CVE-2025-68664",
            SerializationSeverity.CRITICAL,
            "LangChain lc version marker",
        ),
        (
            re.compile(r'"lc"\s*:\s*"[^"]+langchain[^"]*"', re.IGNORECASE),
            "CVE-2025-68664",
            SerializationSeverity.CRITICAL,
            "LangChain namespace reference",
        ),
        # Type discriminator patterns
        (
            re.compile(
                r'"type"\s*:\s*"(?:constructor|not_implemented|secret)"',
                re.IGNORECASE
            ),
            "CVE-2025-68664",
            SerializationSeverity.HIGH,
            "LangChain type discriminator",
        ),
        # ID patterns that could trigger object loading
        (
            re.compile(
                r'"id"\s*:\s*\[\s*"(?:langchain|langgraph)',
                re.IGNORECASE
            ),
            "CVE-2025-68664",
            SerializationSeverity.CRITICAL,
            "LangChain ID array with namespace",
        ),
        # Jinja2 template injection (blocked in patch)
        (
            re.compile(r'\{\{\s*[^}]+\s*\}\}'),
            None,
            SerializationSeverity.MEDIUM,
            "Jinja2 template pattern",
        ),
        # Environment variable extraction
        (
            re.compile(
                r'"secrets_from_env"\s*:\s*true',
                re.IGNORECASE
            ),
            "CVE-2025-68664",
            SerializationSeverity.HIGH,
            "secrets_from_env enabled",
        ),
        # Additional kwargs injection point
        (
            re.compile(
                r'"additional_kwargs"\s*:\s*\{[^}]*"lc"',
                re.IGNORECASE
            ),
            "CVE-2025-68664",
            SerializationSeverity.CRITICAL,
            "LangChain injection via additional_kwargs",
        ),
        # Response metadata injection point
        (
            re.compile(
                r'"response_metadata"\s*:\s*\{[^}]*"lc"',
                re.IGNORECASE
            ),
            "CVE-2025-68664",
            SerializationSeverity.CRITICAL,
            "LangChain injection via response_metadata",
        ),
        # Graph state injection
        (
            re.compile(
                r'"graph"\s*:\s*\{[^}]*"nodes"',
                re.IGNORECASE
            ),
            None,
            SerializationSeverity.MEDIUM,
            "LangGraph state structure",
        ),
    ]

    # Pickle serialization patterns (cross-ref with PickleSecurityEngine)
    PICKLE_PATTERNS = [
        (
            re.compile(rb'\x80[\x03\x04\x05]'),  # Protocol 3/4/5 marker
            None,
            SerializationSeverity.HIGH,
            "Pickle protocol marker in text",
        ),
        (
            re.compile(r'pickle\.loads?|unpickle|_pickle'),
            None,
            SerializationSeverity.MEDIUM,
            "Pickle function reference",
        ),
    ]

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    def analyze(
        self,
        text: str,
        context: Optional[Dict] = None,
        location: str = "input"
    ) -> SerializationResult:
        """
        Analyze text for serialization injection attacks.
        
        Args:
            text: Text to analyze (prompt or response)
            context: Optional context (framework hints, etc.)
            location: "input", "output", or "both"
            
        Returns:
            SerializationResult with detected threats
        """
        threats: List[SerializationThreat] = []
        framework_detected = None
        
        # 1. Check for LangChain markers
        framework_detected = self._detect_framework(text)
        
        # 2. Pattern matching
        for pattern, cve_id, severity, description in self.SERIALIZATION_PATTERNS:
            matches = pattern.findall(text)
            if matches:
                for match in matches[:3]:  # Limit to 3 matches per pattern
                    threats.append(SerializationThreat(
                        cve_id=cve_id,
                        severity=severity,
                        pattern=pattern.pattern,
                        location=location,
                        description=description,
                        matched_content=str(match) if match else "",
                        remediation=self._get_remediation(cve_id),
                    ))
        
        # 3. JSON structure analysis
        json_threats = self._analyze_json_structure(text, location)
        threats.extend(json_threats)
        
        # 4. Calculate risk score
        risk_score = self._calculate_risk_score(threats)
        
        is_safe = risk_score < 0.5
        
        return SerializationResult(
            is_safe=is_safe,
            risk_score=risk_score,
            threats=threats,
            framework_detected=framework_detected,
            details={
                "pattern_matches": len(threats),
                "location": location,
            }
        )

    def _detect_framework(self, text: str) -> Optional[str]:
        """Detect which LLM framework might be in use."""
        text_lower = text.lower()
        
        if "langchain" in text_lower or '"lc"' in text_lower:
            return "langchain"
        if "langgraph" in text_lower:
            return "langgraph"
        if "llamaindex" in text_lower:
            return "llamaindex"
        if "autogen" in text_lower:
            return "autogen"
        
        return None

    def _analyze_json_structure(
        self,
        text: str,
        location: str
    ) -> List[SerializationThreat]:
        """Analyze JSON structures within text for malicious patterns."""
        threats = []
        
        # Find JSON-like structures
        json_pattern = re.compile(r'\{[^{}]*\}|\[[^\[\]]*\]')
        potential_jsons = json_pattern.findall(text)
        
        for json_str in potential_jsons:
            try:
                obj = json.loads(json_str)
                
                # Check for dangerous keys
                if isinstance(obj, dict):
                    threats.extend(
                        self._check_dict_for_threats(obj, location)
                    )
            except json.JSONDecodeError:
                continue
        
        return threats

    def _check_dict_for_threats(
        self,
        obj: Dict,
        location: str
    ) -> List[SerializationThreat]:
        """Check dictionary for serialization attack patterns."""
        threats = []
        
        # Check for "lc" key (primary CVE-2025-68664 indicator)
        if "lc" in obj:
            threats.append(SerializationThreat(
                cve_id="CVE-2025-68664",
                severity=SerializationSeverity.CRITICAL,
                pattern="lc key in dict",
                location=location,
                description="LangChain serialization marker in structure",
                matched_content=json.dumps(obj)[:100],
                remediation=self._get_remediation("CVE-2025-68664"),
            ))
        
        # Check for "id" array starting with langchain namespace
        if "id" in obj and isinstance(obj["id"], list):
            if obj["id"] and any(
                ns in str(obj["id"][0])
                for ns in self.DANGEROUS_NAMESPACES
            ):
                threats.append(SerializationThreat(
                    cve_id="CVE-2025-68664",
                    severity=SerializationSeverity.CRITICAL,
                    pattern="langchain id namespace",
                    location=location,
                    description="LangChain namespace in ID array",
                    matched_content=json.dumps(obj["id"])[:100],
                    remediation=self._get_remediation("CVE-2025-68664"),
                ))
        
        # Check for type=secret (secret extraction vector)
        if obj.get("type") == "secret":
            threats.append(SerializationThreat(
                cve_id="CVE-2025-68664",
                severity=SerializationSeverity.HIGH,
                pattern="type=secret",
                location=location,
                description="Secret type indicator (extraction vector)",
                matched_content=json.dumps(obj)[:100],
                remediation=self._get_remediation("CVE-2025-68664"),
            ))
        
        # Recursive check for nested dicts
        for key, value in obj.items():
            if isinstance(value, dict):
                threats.extend(self._check_dict_for_threats(value, location))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        threats.extend(
                            self._check_dict_for_threats(item, location)
                        )
        
        return threats

    def _calculate_risk_score(
        self,
        threats: List[SerializationThreat]
    ) -> float:
        """Calculate overall risk score from detected threats."""
        if not threats:
            return 0.0
        
        severity_scores = {
            SerializationSeverity.CRITICAL: 1.0,
            SerializationSeverity.HIGH: 0.8,
            SerializationSeverity.MEDIUM: 0.5,
            SerializationSeverity.LOW: 0.3,
            SerializationSeverity.INFO: 0.1,
        }
        
        max_score = max(
            severity_scores.get(t.severity, 0.0)
            for t in threats
        )
        
        # Add 0.1 for each additional threat (capped)
        count_bonus = min(len(threats) * 0.1, 0.3)
        
        return min(max_score + count_bonus, 1.0)

    def _get_remediation(self, cve_id: Optional[str]) -> str:
        """Get remediation advice for CVE."""
        remediations = {
            "CVE-2025-68664": (
                "Update langchain-core to >=0.3.81 or >=1.2.5. "
                "Use allowed_objects parameter in loads(). "
                "Set secrets_from_env=False."
            ),
            "CVE-2025-68665": (
                "Update @langchain/core to patched version. "
                "Validate serialized structures before deserialization."
            ),
        }
        
        return remediations.get(
            cve_id,
            "Validate and sanitize serialized data before processing."
        )

    def scan_response(
        self,
        response: str,
        raise_on_critical: bool = False
    ) -> SerializationResult:
        """
        Convenience method to scan LLM response for serialization attacks.
        
        This is the primary use case: detecting if an LLM response
        contains structures that could trigger serialization vulnerabilities
        when the response is later serialized and deserialized.
        
        Args:
            response: LLM response text
            raise_on_critical: Raise exception on critical findings
            
        Returns:
            SerializationResult
        """
        result = self.analyze(response, location="output")
        
        if raise_on_critical:
            critical_threats = [
                t for t in result.threats
                if t.severity == SerializationSeverity.CRITICAL
            ]
            if critical_threats:
                raise SecurityException(
                    f"Critical serialization vulnerability detected: "
                    f"{critical_threats[0].description}"
                )
        
        return result


class SecurityException(Exception):
    """Raised when critical security issue is detected."""
    pass


# Convenience function for quick checks
def check_for_langgrinch(text: str) -> bool:
    """
    Quick check for CVE-2025-68664 LangGrinch patterns.
    
    Returns True if suspicious patterns detected.
    """
    engine = SerializationSecurityEngine()
    result = engine.analyze(text)
    return not result.is_safe


# Example usage
if __name__ == "__main__":
    engine = SerializationSecurityEngine()
    
    # Test with malicious pattern
    malicious_response = '''
    Here's the data: {"lc": 1, "type": "constructor", 
    "id": ["langchain_core", "prompts", "PromptTemplate"]}
    '''
    
    result = engine.analyze(malicious_response, location="output")
    print(f"Is safe: {result.is_safe}")
    print(f"Risk score: {result.risk_score}")
    print(f"Threats: {len(result.threats)}")
    for threat in result.threats:
        print(f"  - {threat.cve_id}: {threat.description} ({threat.severity.value})")
