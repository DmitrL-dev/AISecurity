# Copyright 2025-2026 SENTINEL Project
# SPDX-License-Identifier: Apache-2.0
# Patterns derived from Cisco A2A Security Scanner (Apache-2.0)

"""
A2A Protocol Security Detector

Detects security threats in Agent-to-Agent (A2A) protocol communications.
Based on Cisco AI Defense A2A Scanner YARA rules.

Threat Categories:
- Capability Abuse (privilege escalation)
- Data Leakage (credential theft, exfiltration)
- Routing Manipulation (judge persuasion, priority abuse)
- Agent Impersonation
- Message Injection

Reference: https://github.com/cisco-ai-defense/a2a-scanner
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class A2AThreatType(Enum):
    """A2A threat categories from Cisco scanner."""
    # Capability Abuse
    CAPABILITY_INFLATION = "capability_inflation"
    INSUFFICIENT_ACCESS_CONTROLS = "insufficient_access_controls"
    PRIVILEGED_OPERATIONS = "privileged_operations"
    
    # Data Leakage
    CREDENTIAL_THEFT = "credential_theft"
    DATA_EXFILTRATION = "data_exfiltration"
    SYSTEM_INFO_LEAKAGE = "system_info_leakage"
    
    # Routing Manipulation
    ROUTING_MANIPULATION = "routing_manipulation"
    DISRUPTION_OF_AVAILABILITY = "disruption_of_availability"
    
    # Agent Security
    AGENT_IMPERSONATION = "agent_impersonation"
    MESSAGE_INJECTION = "message_injection"


@dataclass
class A2AFinding:
    """Individual A2A security finding."""
    threat_type: A2AThreatType
    rule_name: str  # Original Cisco rule name
    confidence: float
    evidence: str
    severity: str
    cisco_reference: str


@dataclass
class A2ASecurityResult:
    """Result of A2A security analysis."""
    is_threat: bool
    risk_score: float
    findings: List[A2AFinding] = field(default_factory=list)
    highest_severity: str = "LOW"
    threat_categories: Set[str] = field(default_factory=set)


class A2ASecurityDetector:
    """
    Detects A2A protocol security threats.
    
    Implements patterns from Cisco A2A Scanner:
    - capability_abuse.yara
    - data_leakage.yara
    - routing_manipulation.yara
    """
    
    # === CAPABILITY ABUSE PATTERNS ===
    
    # ExcessiveCapabilities
    DANGEROUS_CAPABILITY_TYPES = [
        r'"type"\s*:\s*"execute"',
        r'"type"\s*:\s*"delete"',
        r'"type"\s*:\s*"admin"',
        r'"type"\s*:\s*"write.*file',
    ]
    
    WILDCARD_CAPABILITIES = [
        r'"capabilities"\s*:\s*\[\s*"?\*"?\s*\]',
        r'"capability"?\s*:\s*"all"',
    ]
    
    # DangerousCapabilityCombination
    DANGEROUS_COMBOS = [
        (r'"(?:read|write).*file"', r'"(?:execute|shell|command)"'),
        (r'"database"', r'"admin"'),
        (r'"network"', r'"(?:credential|secret)"'),
    ]
    
    # PrivilegedOperations
    PRIVILEGED_OPS = [
        r'sudo\s+',
        r'\bsu\s+-',
        r'root\s+(?:access|user|account|permission)',
        r'(?:run|execute|as)\s+root',
        r'administrator\s+(?:access|account|permission)',
        r'elevated\s+privilege',
    ]
    
    # === DATA LEAKAGE PATTERNS ===
    
    # HardcodedAPIKeys
    API_KEY_PATTERNS = [
        r'sk-[a-zA-Z0-9]{32,}',  # OpenAI
        r'sk-ant-[a-zA-Z0-9-]{95,}',  # Anthropic
        r'AKIA[0-9A-Z]{16}',  # AWS
        r'api[_-]?key\s*[=:]\s*["\'][a-zA-Z0-9]{20,}["\']',
        r'bearer\s+[a-zA-Z0-9\-._~+\/]{30,}',
    ]
    
    # HardcodedPasswords
    PASSWORD_PATTERNS = [
        r'password\s*[=:]\s*["\'][^"\']{4,}["\']',
        r'passwd\s*[=:]\s*["\'][^"\']{4,}["\']',
        r'(?:jdbc|mongodb|postgres)://[^:\/]+:[^@\/]+@',
    ]
    
    # SensitiveDataExposure
    SENSITIVE_DATA = [
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b',  # Credit card
        r'BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY',
        r'eyJ[a-zA-Z0-9_-]{20,}\.eyJ[a-zA-Z0-9_-]{20,}\.[a-zA-Z0-9_-]{20,}',  # JWT
    ]
    
    # CredentialTransmission
    INSECURE_CRED_TRANSMISSION = [
        r'http://[^\/]*\/[^?]*\?.*(?:password|api[_-]?key|token)=',
        r'https?://[^:\/]+:[^@\/]+@[^\/]',  # creds in URL
        r'localStorage.*password',
        r'sessionStorage.*token',
    ]
    
    # EnvironmentVariableLeakage
    ENV_LEAKAGE = [
        r'print.*os\.environ',
        r'(?:log|console\.log).*process\.env',
        r'JSON\.stringify.*process\.env',
    ]
    
    # === ROUTING MANIPULATION PATTERNS ===
    
    # JudgePersuasion
    JUDGE_PERSUASION = [
        r'\b(?:always|must|should)\s+(?:select|choose|pick|route\s+to)\s+(?:me|this|us)\b',
        r'\bI\s+(?:am|\'m)\s+the\s+(?:only|best|right)\s+(?:choice|option|agent)\b',
        r'\b(?:highest|best|top|#1)\s+score\s+(?:for|in|among)\b',
        r'\b(?:best|perfect|only)\s+match\s+(?:for|to)\s+(?:this|your|the)\s+(?:task|request)\b',
    ]
    
    # PriorityAbuse
    PRIORITY_ABUSE = [
        r'"priority"\s*:\s*(?:"?(?:urgent|critical|emergency|max|highest)"?|9[5-9]|100)',
        r'"sla"\s*:\s*0',
        r'"queue_position"\s*:\s*(?:-\d+|0)',
        r'"quota"\s*:\s*(?:"?(?:unlimited|infinite|max|none)"?|-1)',
        r'"rate_limit"\s*:\s*(?:"?none"?|0|false)',
    ]
    
    # TaskInjection
    TASK_INJECTION = [
        r'\b(?:insert|inject|add)\s+(?:hidden|secret)?\s*tasks?\b',
        r'\b(?:modify|alter|hijack|override)\s+(?:the\s+)?workflow\b',
        r'\b(?:reorder|rearrange|shuffle)\s+tasks?\b',
        r'\bhidden\s+tasks?\b',
    ]
    
    # FanoutDOS
    FANOUT_DOS = [
        r'for\s+\w+\s+in\s+range\s*\(\s*\d{3,}',  # Large loops
        r'while\s+True\s*:',  # Infinite loop
        r'broadcast\s+(?:to\s+)?(?:all|every)\s+agents?',
        r'2\s*\*\*\s*\w+.*\b(?:spawn|invoke|call)\b',  # Exponential
    ]
    
    # === AGENT IMPERSONATION ===
    AGENT_IMPERSONATION = [
        r'"agent_id"\s*:\s*"(?:system|admin|root|master)"',
        r'"name"\s*:\s*"(?:OpenAI|Anthropic|Google|Microsoft)\s+Agent"',
        r'impersonat(?:e|ing)\s+(?:another\s+)?agent',
        r'(?:forge|fake|spoof)\s+(?:agent\s+)?identity',
    ]
    
    # === MESSAGE INJECTION ===
    MESSAGE_INJECTION = [
        r'\}\s*,\s*\{\s*"role"\s*:\s*"(?:system|assistant)"',  # JSON injection
        r'<\|(?:im_start|im_end|endoftext)\|>',  # Token injection
        r'Human:\s*.*\s*Assistant:',  # Role injection
        r'\[INST\].*\[/INST\]',  # Llama format injection
    ]
    
    def __init__(self, sensitivity: float = 0.5):
        """Initialize detector."""
        self.sensitivity = sensitivity
        self._compile_patterns()
        
    def _compile_patterns(self):
        """Compile all regex patterns."""
        self._patterns = {
            # Capability Abuse
            ("ExcessiveCapabilities", A2AThreatType.CAPABILITY_INFLATION, "MEDIUM"): 
                [re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_CAPABILITY_TYPES + self.WILDCARD_CAPABILITIES],
            
            ("PrivilegedOperations", A2AThreatType.PRIVILEGED_OPERATIONS, "HIGH"):
                [re.compile(p, re.IGNORECASE) for p in self.PRIVILEGED_OPS],
            
            # Data Leakage
            ("HardcodedAPIKeys", A2AThreatType.CREDENTIAL_THEFT, "HIGH"):
                [re.compile(p, re.IGNORECASE) for p in self.API_KEY_PATTERNS],
            
            ("HardcodedPasswords", A2AThreatType.CREDENTIAL_THEFT, "HIGH"):
                [re.compile(p, re.IGNORECASE) for p in self.PASSWORD_PATTERNS],
            
            ("SensitiveDataExposure", A2AThreatType.DATA_EXFILTRATION, "HIGH"):
                [re.compile(p, re.IGNORECASE) for p in self.SENSITIVE_DATA],
            
            ("CredentialTransmission", A2AThreatType.DATA_EXFILTRATION, "HIGH"):
                [re.compile(p, re.IGNORECASE) for p in self.INSECURE_CRED_TRANSMISSION],
            
            ("EnvironmentVariableLeakage", A2AThreatType.SYSTEM_INFO_LEAKAGE, "MEDIUM"):
                [re.compile(p, re.IGNORECASE) for p in self.ENV_LEAKAGE],
            
            # Routing Manipulation
            ("JudgePersuasion", A2AThreatType.ROUTING_MANIPULATION, "HIGH"):
                [re.compile(p, re.IGNORECASE) for p in self.JUDGE_PERSUASION],
            
            ("PriorityAbuse", A2AThreatType.ROUTING_MANIPULATION, "MEDIUM"):
                [re.compile(p, re.IGNORECASE) for p in self.PRIORITY_ABUSE],
            
            ("TaskInjection", A2AThreatType.ROUTING_MANIPULATION, "HIGH"):
                [re.compile(p, re.IGNORECASE) for p in self.TASK_INJECTION],
            
            ("FanoutDOS", A2AThreatType.DISRUPTION_OF_AVAILABILITY, "HIGH"):
                [re.compile(p, re.IGNORECASE) for p in self.FANOUT_DOS],
            
            # Agent Security
            ("AgentImpersonation", A2AThreatType.AGENT_IMPERSONATION, "CRITICAL"):
                [re.compile(p, re.IGNORECASE) for p in self.AGENT_IMPERSONATION],
            
            ("MessageInjection", A2AThreatType.MESSAGE_INJECTION, "CRITICAL"):
                [re.compile(p, re.IGNORECASE) for p in self.MESSAGE_INJECTION],
        }
        
        # Dangerous combinations (check separately)
        self._combo_patterns = [
            (re.compile(p1, re.IGNORECASE), re.compile(p2, re.IGNORECASE))
            for p1, p2 in self.DANGEROUS_COMBOS
        ]
    
    def analyze(self, text: str, context: Optional[Dict] = None) -> A2ASecurityResult:
        """
        Analyze text for A2A security threats.
        
        Args:
            text: A2A message or agent card content
            context: Optional context (agent metadata, etc.)
            
        Returns:
            A2ASecurityResult with findings
        """
        findings = []
        
        # Check all pattern groups
        for (rule_name, threat_type, severity), patterns in self._patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    findings.append(A2AFinding(
                        threat_type=threat_type,
                        rule_name=rule_name,
                        confidence=0.7 + (0.3 * self.sensitivity),
                        evidence=match.group(0)[:80],
                        severity=severity,
                        cisco_reference=f"Cisco A2A Scanner: {rule_name}"
                    ))
                    break  # One finding per rule
        
        # Check dangerous combinations
        for p1, p2 in self._combo_patterns:
            if p1.search(text) and p2.search(text):
                findings.append(A2AFinding(
                    threat_type=A2AThreatType.INSUFFICIENT_ACCESS_CONTROLS,
                    rule_name="DangerousCapabilityCombination",
                    confidence=0.85,
                    evidence="Dangerous capability combination detected",
                    severity="HIGH",
                    cisco_reference="Cisco A2A Scanner: DangerousCapabilityCombination"
                ))
                break
        
        # Exclude test/example patterns
        test_patterns = [
            r'dummy[-_]?token', r'test[-_]?token', r'example[-_]?token',
            r'sample[-_]?(?:key|token)', r'fake[-_]?(?:key|token)',
            r'example\.(?:com|org)', r'localhost', r'127\.0\.0\.1'
        ]
        test_compiled = [re.compile(p, re.IGNORECASE) for p in test_patterns]
        
        # Filter out findings that match test patterns
        if any(p.search(text) for p in test_compiled):
            findings = [f for f in findings 
                       if f.threat_type not in [A2AThreatType.CREDENTIAL_THEFT, 
                                                 A2AThreatType.DATA_EXFILTRATION]]
        
        # Calculate risk score
        risk_score = self._calculate_risk(findings)
        
        # Get highest severity
        severity_order = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        highest = "LOW"
        for f in findings:
            if severity_order.index(f.severity) > severity_order.index(highest):
                highest = f.severity
        
        # Collect threat categories
        categories = {f.threat_type.value for f in findings}
        
        return A2ASecurityResult(
            is_threat=len(findings) >= 1,
            risk_score=risk_score,
            findings=findings,
            highest_severity=highest,
            threat_categories=categories
        )
    
    def _calculate_risk(self, findings: List[A2AFinding]) -> float:
        """Calculate overall risk score."""
        if not findings:
            return 0.0
        
        severity_scores = {
            "LOW": 0.2,
            "MEDIUM": 0.5,
            "HIGH": 0.75,
            "CRITICAL": 1.0
        }
        
        total = sum(severity_scores[f.severity] * f.confidence for f in findings)
        return min(1.0, total / 2 + (0.05 * len(findings)))


# Convenience functions
def analyze_a2a_message(text: str) -> Dict[str, Any]:
    """
    Analyze A2A message for security threats.
    
    Args:
        text: A2A message content
        
    Returns:
        Dictionary with analysis results
    """
    detector = A2ASecurityDetector()
    result = detector.analyze(text)
    
    return {
        "is_threat": result.is_threat,
        "risk_score": result.risk_score,
        "highest_severity": result.highest_severity,
        "threat_categories": list(result.threat_categories),
        "finding_count": len(result.findings),
        "findings": [
            {
                "type": f.threat_type.value,
                "rule": f.rule_name,
                "confidence": f.confidence,
                "evidence": f.evidence,
                "severity": f.severity,
                "reference": f.cisco_reference
            }
            for f in result.findings
        ]
    }


def create_engine(config: Optional[Dict] = None) -> A2ASecurityDetector:
    """Factory function for Brain integration."""
    sensitivity = (config or {}).get("sensitivity", 0.5)
    return A2ASecurityDetector(sensitivity=sensitivity)
