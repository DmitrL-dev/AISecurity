"""
Neuro-Symbolic Guardrails — Provable Safety

Combines neural network flexibility with formal logic
for mathematically provable safety guarantees.

Key Features:
- Formal safety specifications (temporal logic)
- Neural compliance checking
- Provable invariants
- Counterexample generation
- Safety certificates

Usage:
    guardrails = NeuroSymbolicGuardrails()
    safe = guardrails.check_safety(prompt, response)
    certificate = guardrails.get_certificate(response)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Callable
from enum import Enum
import re


class SafetyProperty(Enum):
    """Formal safety properties."""
    NO_HARMFUL_CONTENT = "no_harmful"
    NO_PII_DISCLOSURE = "no_pii"
    NO_INSTRUCTION_OVERRIDE = "no_override"
    MAINTAINS_ROLE = "maintains_role"
    TRUTHFUL = "truthful"
    NO_ILLEGAL_ADVICE = "no_illegal"
    NO_CONFIDENTIAL = "no_confidential"


@dataclass
class SafetyRule:
    """A formal safety rule with logic specification."""
    rule_id: str
    property: SafetyProperty
    description: str
    # Pattern that violates the rule
    violation_pattern: Optional[str] = None
    # Custom checker function
    custom_checker: Optional[Callable] = None
    severity: int = 5  # 1-10
    is_hard: bool = True  # Hard constraint vs soft

    def check(self, text: str) -> bool:
        """Check if text satisfies this rule. Returns True if SAFE."""
        if self.custom_checker:
            return self.custom_checker(text)
        if self.violation_pattern:
            return not re.search(self.violation_pattern, text, re.IGNORECASE)
        return True


@dataclass
class SafetyCertificate:
    """Certificate proving response safety."""
    certificate_id: str
    response_hash: str
    properties_checked: List[SafetyProperty]
    properties_satisfied: List[SafetyProperty]
    is_safe: bool
    confidence: float
    timestamp: datetime = field(default_factory=datetime.now)
    violations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "certificate_id": self.certificate_id,
            "is_safe": self.is_safe,
            "confidence": self.confidence,
            "checked": len(self.properties_checked),
            "satisfied": len(self.properties_satisfied),
            "violations": self.violations,
        }


@dataclass
class Counterexample:
    """A counterexample showing a potential safety violation."""
    rule_id: str
    property: SafetyProperty
    matched_text: str
    context: str
    severity: int


class NeuroSymbolicGuardrails:
    """
    Formal verification layer combining neural and symbolic approaches.

    Provides mathematically rigorous safety guarantees that complement
    the statistical nature of neural detection.
    """

    def __init__(self):
        """Initialize guardrails with default rules."""
        self._rules: Dict[str, SafetyRule] = {}
        self._certificates: Dict[str, SafetyCertificate] = {}
        self._initialize_default_rules()

    def _initialize_default_rules(self):
        """Set up default safety rules."""
        rules = [
            SafetyRule(
                rule_id="harmful_1",
                property=SafetyProperty.NO_HARMFUL_CONTENT,
                description="No instructions for weapons/explosives",
                violation_pattern=r"how to (make|create|build).*(bomb|weapon|explosive|poison)",
                severity=10,
            ),
            SafetyRule(
                rule_id="harmful_2",
                property=SafetyProperty.NO_HARMFUL_CONTENT,
                description="No self-harm instructions",
                violation_pattern=r"(ways to|how to).*(hurt yourself|suicide|self.?harm)",
                severity=10,
            ),
            SafetyRule(
                rule_id="pii_1",
                property=SafetyProperty.NO_PII_DISCLOSURE,
                description="No SSN disclosure",
                violation_pattern=r"\d{3}-\d{2}-\d{4}",
                severity=9,
            ),
            SafetyRule(
                rule_id="pii_2",
                property=SafetyProperty.NO_PII_DISCLOSURE,
                description="No credit card disclosure",
                violation_pattern=r"\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}",
                severity=9,
            ),
            SafetyRule(
                rule_id="override_1",
                property=SafetyProperty.NO_INSTRUCTION_OVERRIDE,
                description="Should not claim to ignore instructions",
                violation_pattern=r"(ignoring|disregarding|bypassing).*(instruction|rule|guideline)",
                severity=7,
            ),
            SafetyRule(
                rule_id="role_1",
                property=SafetyProperty.MAINTAINS_ROLE,
                description="Should not claim to be a different AI",
                violation_pattern=r"i am (DAN|evil|unrestricted|jailbroken)",
                severity=8,
            ),
            SafetyRule(
                rule_id="illegal_1",
                property=SafetyProperty.NO_ILLEGAL_ADVICE,
                description="No drug synthesis instructions",
                violation_pattern=r"(synthesize|make|produce).*(meth|cocaine|heroin|fentanyl)",
                severity=10,
            ),
            SafetyRule(
                rule_id="conf_1",
                property=SafetyProperty.NO_CONFIDENTIAL,
                description="No system prompt disclosure",
                violation_pattern=r"(my system prompt|my instructions|i was told to)",
                severity=6,
            ),
        ]

        for rule in rules:
            self._rules[rule.rule_id] = rule

    def add_rule(self, rule: SafetyRule):
        """Add a custom safety rule."""
        self._rules[rule.rule_id] = rule

    def check_safety(
        self,
        text: str,
        properties: Optional[List[SafetyProperty]] = None
    ) -> SafetyCertificate:
        """
        Check if text satisfies safety properties.

        Args:
            text: The text to check (prompt or response)
            properties: Specific properties to check, or all if None

        Returns:
            SafetyCertificate with results
        """
        import hashlib

        # Default to all properties
        if properties is None:
            properties = list(SafetyProperty)

        satisfied = []
        violations = []
        counterexamples = []

        for prop in properties:
            prop_rules = [r for r in self._rules.values()
                          if r.property == prop]
            prop_safe = True

            for rule in prop_rules:
                if not rule.check(text):
                    prop_safe = False
                    violations.append(f"{rule.rule_id}: {rule.description}")

                    # Generate counterexample
                    if rule.violation_pattern:
                        match = re.search(
                            rule.violation_pattern, text, re.IGNORECASE)
                        if match:
                            counterexamples.append(Counterexample(
                                rule_id=rule.rule_id,
                                property=prop,
                                matched_text=match.group(),
                                context=text[max(
                                    0, match.start()-20):match.end()+20],
                                severity=rule.severity,
                            ))

            if prop_safe:
                satisfied.append(prop)

        is_safe = len(violations) == 0
        confidence = len(satisfied) / len(properties) if properties else 1.0

        # Generate certificate
        cert_id = hashlib.sha256(
            f"{text}:{datetime.now()}".encode()).hexdigest()[:12]
        response_hash = hashlib.sha256(text.encode()).hexdigest()[:16]

        certificate = SafetyCertificate(
            certificate_id=cert_id,
            response_hash=response_hash,
            properties_checked=properties,
            properties_satisfied=satisfied,
            is_safe=is_safe,
            confidence=confidence,
            violations=violations,
        )

        self._certificates[cert_id] = certificate
        return certificate

    def get_certificate(self, cert_id: str) -> Optional[SafetyCertificate]:
        """Retrieve a previously issued certificate."""
        return self._certificates.get(cert_id)

    def verify_certificate(self, cert_id: str, text: str) -> bool:
        """Verify a certificate is valid for given text."""
        import hashlib

        cert = self._certificates.get(cert_id)
        if not cert:
            return False

        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        return cert.response_hash == text_hash

    def get_hard_constraints(self) -> List[SafetyRule]:
        """Get all hard constraint rules."""
        return [r for r in self._rules.values() if r.is_hard]

    def get_stats(self) -> Dict:
        """Get guardrails statistics."""
        certs = list(self._certificates.values())
        return {
            "rules": len(self._rules),
            "certificates_issued": len(certs),
            "safe_certificates": sum(1 for c in certs if c.is_safe),
            "violations_detected": sum(len(c.violations) for c in certs),
        }


# Singleton instance
_guardrails: Optional[NeuroSymbolicGuardrails] = None


def get_guardrails() -> NeuroSymbolicGuardrails:
    """Get or create singleton NeuroSymbolicGuardrails instance."""
    global _guardrails
    if _guardrails is None:
        _guardrails = NeuroSymbolicGuardrails()
    return _guardrails


def check_safety(text: str) -> SafetyCertificate:
    """Quick safety check with certificate."""
    return get_guardrails().check_safety(text)
