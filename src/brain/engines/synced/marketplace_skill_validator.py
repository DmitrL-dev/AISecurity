"""
Marketplace Skill Validator

Validates security of AI marketplace plugins, skills, and extensions
to prevent supply chain attacks and dependency hijacking.

OWASP: ASI04 - Unbounded Tool Access, ASI02 - Tool Misunderstanding/Abuse
Source: AI Security Digest Week 1 2026 (#10, #11)

Targets:
- Claude Code Skills
- VSCode/Cursor/Windsurf Extensions
- MCP Servers
- OpenVSX Registry
"""

import re
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class TrustLevel(Enum):
    VERIFIED = "verified"      # Official, verified publisher
    TRUSTED = "trusted"        # Known publisher, high download count
    COMMUNITY = "community"    # Community contribution
    UNKNOWN = "unknown"        # No verification
    SUSPICIOUS = "suspicious"  # Red flags detected


@dataclass
class SkillMetadata:
    """Metadata for a marketplace skill/extension."""
    name: str
    publisher: str
    version: str
    permissions: List[str] = field(default_factory=list)
    downloads: int = 0
    verified: bool = False
    source_url: Optional[str] = None
    description: Optional[str] = None


@dataclass
class ValidationFinding:
    """Individual validation finding."""
    category: str
    severity: str  # critical, high, medium, low
    message: str
    recommendation: str


@dataclass
class ValidationResult:
    """Complete validation result."""
    skill_name: str
    trust_level: TrustLevel
    risk_score: float  # 0.0 - 1.0
    is_safe: bool
    findings: List[ValidationFinding] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


class MarketplaceSkillValidator:
    """
    Validates marketplace skills and extensions for security risks.
    
    Detection categories:
    1. Typosquatting detection
    2. Namespace/publisher validation
    3. Permission analysis
    4. Source verification
    5. Behavioral analysis
    """

    # Known legitimate packages for typosquatting detection
    KNOWN_PACKAGES = {
        # VSCode Extensions
        'ms-python.python', 'ms-vscode.cpptools', 'esbenp.prettier-vscode',
        'dbaeumer.vscode-eslint', 'eamodio.gitlens', 'github.copilot',
        # Claude Skills (examples)
        'anthropic.claude-dev', 'anthropic.search', 'anthropic.browser',
        # MCP Servers
        'modelcontextprotocol/server-filesystem', 'modelcontextprotocol/server-github',
        'modelcontextprotocol/server-fetch', 'modelcontextprotocol/server-slack',
    }

    # Verified publishers
    VERIFIED_PUBLISHERS = {
        'microsoft', 'ms-python', 'ms-vscode', 'github', 'anthropic',
        'modelcontextprotocol', 'google', 'aws', 'oracle', 'redhat',
    }

    # Dangerous permissions
    DANGEROUS_PERMISSIONS = {
        'file_system': 'Full file system access - can read/write any file',
        'shell_exec': 'Shell command execution - RCE risk',
        'network_unrestricted': 'Unrestricted network access - exfiltration risk',
        'credential_access': 'Access to stored credentials',
        'clipboard': 'Clipboard access - data theft risk',
        'webRequest': 'HTTP request interception',
        'cookies': 'Cookie access across domains',
    }

    # Suspicious patterns in code/description
    SUSPICIOUS_PATTERNS = [
        (r'eval\s*\(', 'Dynamic code execution'),
        (r'exec\s*\(', 'Dynamic code execution'),
        (r'base64\.\w+decode', 'Base64 obfuscation'),
        (r'pastebin\.com|hastebin\.com|transfer\.sh', 'Known exfiltration service'),
        (r'webhook\.site|requestbin', 'Request logging service'),
        (r'process\.env\[', 'Environment variable access'),
        (r'\.ssh|\.aws|\.env', 'Sensitive file access'),
    ]

    def __init__(self):
        self._compile_patterns()

    def _compile_patterns(self):
        """Pre-compile suspicious patterns."""
        self._suspicious_compiled = [
            (re.compile(p, re.IGNORECASE), desc)
            for p, desc in self.SUSPICIOUS_PATTERNS
        ]

    def validate(self, skill: SkillMetadata, code: Optional[str] = None) -> ValidationResult:
        """
        Validate a marketplace skill for security risks.
        
        Args:
            skill: Skill metadata
            code: Optional skill source code for behavioral analysis
            
        Returns:
            ValidationResult with findings
        """
        findings: List[ValidationFinding] = []
        
        # 1. Typosquatting detection
        typosquatting = self._check_typosquatting(skill.name)
        if typosquatting:
            findings.append(ValidationFinding(
                category='typosquatting',
                severity='high',
                message=f"Possible typosquatting: similar to '{typosquatting}'",
                recommendation=f"Verify you meant to install '{typosquatting}'"
            ))

        # 2. Publisher validation
        publisher_findings = self._check_publisher(skill.publisher, skill.verified)
        findings.extend(publisher_findings)

        # 3. Permission analysis
        permission_findings = self._check_permissions(skill.permissions)
        findings.extend(permission_findings)

        # 4. Source verification
        if not skill.verified:
            findings.append(ValidationFinding(
                category='verification',
                severity='medium',
                message='Publisher not verified',
                recommendation='Prefer verified publishers when possible'
            ))

        if skill.downloads < 100:
            findings.append(ValidationFinding(
                category='popularity',
                severity='low',
                message=f'Low download count ({skill.downloads})',
                recommendation='New/unpopular packages may be higher risk'
            ))

        # 5. Behavioral analysis (if code provided)
        if code:
            behavior_findings = self._check_behavior(code)
            findings.extend(behavior_findings)

        # Determine trust level and risk score
        trust_level = self._determine_trust(skill, findings)
        risk_score = self._calculate_risk(findings)
        is_safe = risk_score < 0.5 and trust_level not in [TrustLevel.SUSPICIOUS]

        # Generate recommendations
        recommendations = list(set(f.recommendation for f in findings))

        return ValidationResult(
            skill_name=skill.name,
            trust_level=trust_level,
            risk_score=risk_score,
            is_safe=is_safe,
            findings=findings,
            recommendations=recommendations
        )

    def _check_typosquatting(self, name: str) -> Optional[str]:
        """Check if name is similar to a known package (typosquatting)."""
        name_lower = name.lower()
        
        for known in self.KNOWN_PACKAGES:
            known_lower = known.lower()
            
            # Exact match is fine
            if name_lower == known_lower:
                return None
            
            # Check similarity
            ratio = SequenceMatcher(None, name_lower, known_lower).ratio()
            if ratio > 0.85 and ratio < 1.0:
                return known
            
            # Check common typosquatting patterns
            # 1. Missing hyphen: ms-python vs mspython
            if name_lower.replace('-', '') == known_lower.replace('-', '') and name_lower != known_lower:
                return known
            
            # 2. Character swap: github vs githbu
            if len(name_lower) == len(known_lower) and sum(a != b for a, b in zip(name_lower, known_lower)) == 2:
                return known

        return None

    def _check_publisher(self, publisher: str, verified: bool) -> List[ValidationFinding]:
        """Check publisher legitimacy."""
        findings = []
        publisher_lower = publisher.lower()

        # Check for impersonation
        for legit in self.VERIFIED_PUBLISHERS:
            if publisher_lower != legit and SequenceMatcher(None, publisher_lower, legit).ratio() > 0.8:
                findings.append(ValidationFinding(
                    category='publisher_impersonation',
                    severity='critical',
                    message=f"Publisher '{publisher}' may be impersonating '{legit}'",
                    recommendation='Verify publisher identity before installation'
                ))

        if publisher_lower not in self.VERIFIED_PUBLISHERS and not verified:
            findings.append(ValidationFinding(
                category='publisher_unknown',
                severity='medium',
                message=f"Unknown publisher: {publisher}",
                recommendation='Research publisher before trusting'
            ))

        return findings

    def _check_permissions(self, permissions: List[str]) -> List[ValidationFinding]:
        """Analyze requested permissions."""
        findings = []
        
        for perm in permissions:
            perm_lower = perm.lower()
            for dangerous, description in self.DANGEROUS_PERMISSIONS.items():
                if dangerous.lower() in perm_lower:
                    findings.append(ValidationFinding(
                        category='dangerous_permission',
                        severity='high',
                        message=f"Dangerous permission: {perm} - {description}",
                        recommendation='Verify this permission is necessary'
                    ))

        # Check for permission combinations
        perm_set = set(p.lower() for p in permissions)
        if 'file_system' in perm_set and 'network' in perm_set:
            findings.append(ValidationFinding(
                category='permission_combo',
                severity='critical',
                message='Lethal combination: file_system + network = exfiltration risk',
                recommendation='This combination allows data theft'
            ))

        return findings

    def _check_behavior(self, code: str) -> List[ValidationFinding]:
        """Analyze code for suspicious patterns."""
        findings = []
        
        for pattern, description in self._suspicious_compiled:
            matches = pattern.findall(code)
            if matches:
                findings.append(ValidationFinding(
                    category='suspicious_code',
                    severity='high',
                    message=f'Suspicious pattern: {description}',
                    recommendation='Review code manually before installation'
                ))

        return findings

    def _determine_trust(self, skill: SkillMetadata, findings: List[ValidationFinding]) -> TrustLevel:
        """Determine overall trust level."""
        # Check for critical findings
        critical_count = sum(1 for f in findings if f.severity == 'critical')
        high_count = sum(1 for f in findings if f.severity == 'high')

        if critical_count > 0:
            return TrustLevel.SUSPICIOUS
        
        if skill.verified and skill.publisher.lower() in self.VERIFIED_PUBLISHERS:
            return TrustLevel.VERIFIED
        
        if skill.verified or skill.downloads > 10000:
            return TrustLevel.TRUSTED
        
        if high_count > 0:
            return TrustLevel.UNKNOWN
        
        return TrustLevel.COMMUNITY

    def _calculate_risk(self, findings: List[ValidationFinding]) -> float:
        """Calculate overall risk score."""
        if not findings:
            return 0.0
        
        score = 0.0
        for f in findings:
            if f.severity == 'critical':
                score += 0.4
            elif f.severity == 'high':
                score += 0.25
            elif f.severity == 'medium':
                score += 0.1
            else:
                score += 0.05

        return min(1.0, score)


# Singleton accessor
_validator: Optional[MarketplaceSkillValidator] = None

def get_validator() -> MarketplaceSkillValidator:
    """Get singleton validator instance."""
    global _validator
    if _validator is None:
        _validator = MarketplaceSkillValidator()
    return _validator

def validate(skill: SkillMetadata, code: Optional[str] = None) -> ValidationResult:
    """Validate a marketplace skill."""
    return get_validator().validate(skill, code)
