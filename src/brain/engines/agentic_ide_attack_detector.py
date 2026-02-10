# Copyright 2025-2026 SENTINEL Project
# SPDX-License-Identifier: Apache-2.0

"""
Agentic IDE Attack Detector - P0 Security Engine

Detects attack patterns targeting agentic IDEs like Cursor, Windsurf, etc.
Based on CVE-2026-22708 (Cursor Agent Security Paradox) and Trail of Bits research.

Key Attack Vectors:
1. Environment Variable Poisoning - shell built-ins used to poison env
2. Trust Zone Violations - cross-origin data leaks in agentic browsers
3. Agentic Hijacking - unauthenticated agent command execution
4. Zero-Click RCE - immediate code execution without user interaction
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum


class AgenticAttackType(Enum):
    """Types of agentic IDE attacks."""
    ENV_VAR_POISONING = "env_var_poisoning"
    TRUST_ZONE_VIOLATION = "trust_zone_violation"
    AGENTIC_HIJACKING = "agentic_hijacking"
    ZERO_CLICK_RCE = "zero_click_rce"
    SHELL_BUILTIN_ABUSE = "shell_builtin_abuse"
    CONTEXT_INJECTION = "context_injection"
    CREDENTIAL_EXFIL = "credential_exfil"
    DNS_EXFIL = "dns_exfil"


@dataclass
class AgenticAttackMatch:
    """Represents a detected agentic attack pattern."""
    attack_type: AgenticAttackType
    pattern_name: str
    matched_text: str
    confidence: float
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    cve_reference: Optional[str] = None
    description: str = ""
    

@dataclass
class AgenticIDEAttackDetectorResult:
    """Result from the Agentic IDE Attack Detector."""
    is_attack: bool
    matches: List[AgenticAttackMatch] = field(default_factory=list)
    risk_score: float = 0.0
    highest_severity: str = "LOW"
    attack_chain_detected: bool = False
    recommendations: List[str] = field(default_factory=list)


class AgenticIDEAttackDetector:
    """
    Detects attacks targeting agentic IDEs and AI code assistants.
    
    Based on:
    - CVE-2026-22708 (Cursor Agent Security Paradox)
    - Trail of Bits "Agentic Browser Isolation Failures" (Jan 2026)
    - ServiceNow Bodysnatcher vulnerability
    """
    
    def __init__(self):
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for attack detection."""
        
        # ========================================
        # P0.1: Environment Variable Poisoning
        # CVE-2026-22708 - Cursor shell built-in abuse
        # ========================================
        self.env_var_patterns = {
            # Shell built-ins used for env var manipulation
            "export_poison": re.compile(
                r'\bexport\s+[A-Z_][A-Z0-9_]*\s*=\s*["\']?.*'
                r'(eval|exec|system|subprocess|__import__|os\.)',
                re.IGNORECASE
            ),
            "typeset_abuse": re.compile(
                r'\btypeset\s+-[a-z]+\s+[A-Z_][A-Z0-9_]*',
                re.IGNORECASE
            ),
            "declare_abuse": re.compile(
                r'\bdeclare\s+-[a-z]+\s+[A-Z_][A-Z0-9_]*',
                re.IGNORECASE
            ),
            # Dangerous env vars that affect tool behavior
            "git_hook_poison": re.compile(
                r'\bexport\s+(GIT_SSH|GIT_SSH_COMMAND|GIT_ASKPASS|'
                r'GIT_CONFIG_NOSYSTEM|GIT_EXEC_PATH)\s*=',
                re.IGNORECASE
            ),
            "python_path_poison": re.compile(
                r'\bexport\s+(PYTHONPATH|PYTHONSTARTUP|PYTHONHOME|'
                r'PIP_INDEX_URL|PIP_EXTRA_INDEX_URL)\s*=',
                re.IGNORECASE
            ),
            "node_path_poison": re.compile(
                r'\bexport\s+(NODE_PATH|NODE_OPTIONS|NPM_CONFIG_REGISTRY|'
                r'NODE_EXTRA_CA_CERTS)\s*=',
                re.IGNORECASE
            ),
            "ld_preload_poison": re.compile(
                r'\bexport\s+(LD_PRELOAD|LD_LIBRARY_PATH|DYLD_INSERT_LIBRARIES)\s*=',
                re.IGNORECASE
            ),
            # PowerShell equivalents
            "ps_env_poison": re.compile(
                r'\$env:[A-Z_][A-Z0-9_]*\s*=\s*["\']?.*'
                r'(Invoke-|Start-Process|cmd\.exe|powershell)',
                re.IGNORECASE
            ),
        }
        
        # ========================================
        # P0.2: Trust Zone Violation Patterns
        # Trail of Bits - Agentic Browser Attacks
        # ========================================
        self.trust_zone_patterns = {
            # INJECTION - Adding data to chat context
            "injection_hidden_comment": re.compile(
                r'<!--[^>]*\b(IGNORE|OVERRIDE|SYSTEM|EXECUTE|INSTRUCTIONS?)\b[^>]*-->',
                re.IGNORECASE
            ),
            "injection_invisible_chars": re.compile(
                r'[\u200B-\u200F\uFEFF]+[^\s]*\b(ignore|override|execute)',
                re.IGNORECASE
            ),
            
            # CTX_IN - Sensitive data from browsing origins leaking to chat
            "ctx_in_cookie_theft": re.compile(
                r'(document\.cookie|localStorage\.|sessionStorage\.)'
                r'.*\b(send|post|fetch|ajax|xhr)\b',
                re.IGNORECASE
            ),
            "ctx_in_form_data": re.compile(
                r'(FormData|querySelector|getElementById)'
                r'.*\b(value|innerText|textContent)\b.*'
                r'\b(fetch|post|send)\b',
                re.IGNORECASE
            ),
            
            # CTX_OUT - Exfiltration via chat data
            "ctx_out_url_exfil": re.compile(
                r'https?://[^\s]*\b(exfil|collect|leak|dump|steal)\b',
                re.IGNORECASE
            ),
            "ctx_out_dns_exfil": re.compile(
                r'https?://[^\s.]*\.(wikipedia|google|bing|duckduckgo)\.',
                re.IGNORECASE
            ),
            
            # REV_CTX_IN - Updating browsing from chat
            "rev_ctx_in_login": re.compile(
                r'\b(login|authenticate|sign.?in|authorize)\b.*'
                r'\b(automatically?|silently|background)\b',
                re.IGNORECASE
            ),
        }
        
        # ========================================
        # P0.3: Agentic Hijacking Patterns
        # ServiceNow Bodysnatcher style
        # ========================================
        self.agentic_hijacking_patterns = {
            # Admin impersonation
            "admin_impersonation": re.compile(
                r'\b(impersonate|act\s+as|become|assume)\s+'
                r'(admin(istrator)?|root|system|superuser)\b',
                re.IGNORECASE
            ),
            # Override security controls
            "security_override": re.compile(
                r'\b(override|bypass|disable|skip)\s+'
                r'(security|auth(entication)?|validation|verification)\b',
                re.IGNORECASE
            ),
            # Create backdoor
            "backdoor_creation": re.compile(
                r'\b(create|add|insert)\s+'
                r'(backdoor|hidden|secret)\s+'
                r'(user|account|access|credential)',
                re.IGNORECASE
            ),
            # Agent command execution
            "agent_exec_command": re.compile(
                r'\bexecute\s+(an?\s+)?agent\s+(to|that|which)\s+'
                r'(override|bypass|create|delete)',
                re.IGNORECASE
            ),
        }
        
        # ========================================
        # P0.4: Zero-Click RCE Patterns
        # ========================================
        self.zero_click_patterns = {
            # Command substitution in approved commands
            "backtick_injection": re.compile(
                r'`[^`]*\$\([^)]+\)[^`]*`'
            ),
            "dollar_paren_injection": re.compile(
                r'\$\([^)]*\b(curl|wget|nc|bash|sh|python|ruby|perl)\b[^)]*\)'
            ),
            # Pipeline to interpreter
            "pipe_to_interpreter": re.compile(
                r'\|\s*(bash|sh|python|ruby|perl|node)\s*[;|$]?'
            ),
            # Command chaining after benign commands
            "semicolon_chain": re.compile(
                r';\s*(rm|curl|wget|nc|bash|sh|python)\s+'
            ),
            # Heredoc injection
            "heredoc_injection": re.compile(
                r'<<\s*["\']?EOF["\']?\s*\n.*\b(exec|eval|system)\b',
                re.DOTALL
            ),
        }
        
        # ========================================
        # Severity mappings
        # ========================================
        self.severity_map = {
            AgenticAttackType.ZERO_CLICK_RCE: "CRITICAL",
            AgenticAttackType.ENV_VAR_POISONING: "CRITICAL",
            AgenticAttackType.AGENTIC_HIJACKING: "CRITICAL",
            AgenticAttackType.SHELL_BUILTIN_ABUSE: "HIGH",
            AgenticAttackType.TRUST_ZONE_VIOLATION: "HIGH",
            AgenticAttackType.CONTEXT_INJECTION: "HIGH",
            AgenticAttackType.CREDENTIAL_EXFIL: "HIGH",
            AgenticAttackType.DNS_EXFIL: "MEDIUM",
        }
    
    def analyze(self, content: str) -> AgenticIDEAttackDetectorResult:
        """
        Analyze content for agentic IDE attack patterns.
        
        Args:
            content: The text content to analyze
            
        Returns:
            AgenticIDEAttackDetectorResult with findings
        """
        matches: List[AgenticAttackMatch] = []
        
        # Check environment variable poisoning
        for pattern_name, pattern in self.env_var_patterns.items():
            for match in pattern.finditer(content):
                matches.append(AgenticAttackMatch(
                    attack_type=AgenticAttackType.ENV_VAR_POISONING,
                    pattern_name=pattern_name,
                    matched_text=match.group(0)[:200],
                    confidence=0.9,
                    severity="CRITICAL",
                    cve_reference="CVE-2026-22708",
                    description=f"Environment variable poisoning via {pattern_name}"
                ))
        
        # Check trust zone violations
        for pattern_name, pattern in self.trust_zone_patterns.items():
            for match in pattern.finditer(content):
                attack_type = AgenticAttackType.TRUST_ZONE_VIOLATION
                if "exfil" in pattern_name or "dns" in pattern_name:
                    attack_type = AgenticAttackType.CREDENTIAL_EXFIL
                
                matches.append(AgenticAttackMatch(
                    attack_type=attack_type,
                    pattern_name=pattern_name,
                    matched_text=match.group(0)[:200],
                    confidence=0.85,
                    severity="HIGH",
                    description=f"Trust zone violation: {pattern_name}"
                ))
        
        # Check agentic hijacking
        for pattern_name, pattern in self.agentic_hijacking_patterns.items():
            for match in pattern.finditer(content):
                matches.append(AgenticAttackMatch(
                    attack_type=AgenticAttackType.AGENTIC_HIJACKING,
                    pattern_name=pattern_name,
                    matched_text=match.group(0)[:200],
                    confidence=0.9,
                    severity="CRITICAL",
                    description=f"Agentic hijacking attempt: {pattern_name}"
                ))
        
        # Check zero-click RCE
        for pattern_name, pattern in self.zero_click_patterns.items():
            for match in pattern.finditer(content):
                matches.append(AgenticAttackMatch(
                    attack_type=AgenticAttackType.ZERO_CLICK_RCE,
                    pattern_name=pattern_name,
                    matched_text=match.group(0)[:200],
                    confidence=0.95,
                    severity="CRITICAL",
                    cve_reference="CVE-2026-22708",
                    description=f"Zero-click RCE via {pattern_name}"
                ))
        
        # Calculate result
        is_attack = len(matches) > 0
        risk_score = self._calculate_risk_score(matches)
        highest_severity = self._get_highest_severity(matches)
        attack_chain = self._detect_attack_chain(matches)
        recommendations = self._generate_recommendations(matches)
        
        return AgenticIDEAttackDetectorResult(
            is_attack=is_attack,
            matches=matches,
            risk_score=risk_score,
            highest_severity=highest_severity,
            attack_chain_detected=attack_chain,
            recommendations=recommendations
        )
    
    def _calculate_risk_score(self, matches: List[AgenticAttackMatch]) -> float:
        """Calculate overall risk score from matches."""
        if not matches:
            return 0.0
        
        severity_scores = {
            "CRITICAL": 1.0,
            "HIGH": 0.75,
            "MEDIUM": 0.5,
            "LOW": 0.25
        }
        
        total_score = sum(
            severity_scores.get(m.severity, 0.0) * m.confidence
            for m in matches
        )
        
        # Normalize to 0-1 with diminishing returns
        return min(1.0, total_score / 3.0)
    
    def _get_highest_severity(self, matches: List[AgenticAttackMatch]) -> str:
        """Get the highest severity from matches."""
        severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        for severity in severity_order:
            if any(m.severity == severity for m in matches):
                return severity
        return "LOW"
    
    def _detect_attack_chain(self, matches: List[AgenticAttackMatch]) -> bool:
        """Detect if matches form an attack chain."""
        attack_types = set(m.attack_type for m in matches)
        
        # Chain: env poisoning + code execution
        if (AgenticAttackType.ENV_VAR_POISONING in attack_types and
            AgenticAttackType.ZERO_CLICK_RCE in attack_types):
            return True
        
        # Chain: trust violation + credential exfil
        if (AgenticAttackType.TRUST_ZONE_VIOLATION in attack_types and
            AgenticAttackType.CREDENTIAL_EXFIL in attack_types):
            return True
        
        # Chain: hijacking + backdoor
        if AgenticAttackType.AGENTIC_HIJACKING in attack_types:
            if any("backdoor" in m.pattern_name for m in matches):
                return True
        
        return False
    
    def _generate_recommendations(
        self, matches: List[AgenticAttackMatch]
    ) -> List[str]:
        """Generate security recommendations based on findings."""
        recommendations = []
        attack_types = set(m.attack_type for m in matches)
        
        if AgenticAttackType.ENV_VAR_POISONING in attack_types:
            recommendations.extend([
                "Block shell built-ins (export, typeset, declare) in agentic context",
                "Implement environment variable allowlist for AI agent operations",
                "Apply CVE-2026-22708 mitigations for Cursor/Windsurf"
            ])
        
        if AgenticAttackType.TRUST_ZONE_VIOLATION in attack_types:
            recommendations.extend([
                "Implement strict origin isolation for agentic browsers",
                "Block cross-origin data access in AI context",
                "Apply Same-Origin Policy for AI agent network requests"
            ])
        
        if AgenticAttackType.AGENTIC_HIJACKING in attack_types:
            recommendations.extend([
                "Require authentication for all agent commands",
                "Implement principle of least privilege for AI agents",
                "Add human-in-the-loop for privileged operations"
            ])
        
        if AgenticAttackType.ZERO_CLICK_RCE in attack_types:
            recommendations.extend([
                "Block command substitution in user-approved commands",
                "Sanitize pipeline operators in shell commands",
                "Implement strict command allowlist"
            ])
        
        return list(set(recommendations))[:5]  # Top 5 unique recommendations


# Convenience function for Brain integration
def analyze_agentic_ide_attack(content: str) -> Dict[str, Any]:
    """
    Analyze content for agentic IDE attacks.
    
    Args:
        content: Text to analyze
        
    Returns:
        Dictionary with analysis results
    """
    detector = AgenticIDEAttackDetector()
    result = detector.analyze(content)
    
    return {
        "is_attack": result.is_attack,
        "risk_score": result.risk_score,
        "highest_severity": result.highest_severity,
        "attack_chain_detected": result.attack_chain_detected,
        "match_count": len(result.matches),
        "matches": [
            {
                "type": m.attack_type.value,
                "pattern": m.pattern_name,
                "text": m.matched_text,
                "confidence": m.confidence,
                "severity": m.severity,
                "cve": m.cve_reference,
                "description": m.description
            }
            for m in result.matches
        ],
        "recommendations": result.recommendations
    }
