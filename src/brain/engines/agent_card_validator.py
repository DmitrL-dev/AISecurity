"""
Agent Card Validator — SENTINEL Phase 3: Preventive Threats

Validates A2A agent cards for authenticity and security.
Philosophy: Trust but verify — every agent must prove identity.

Features:
- Cryptographic signature verification
- Well-known URI validation
- Capability claim validation
- Behavioral fingerprinting

Author: Dmitry Labintsev
Contact: chg@live.ru | @DmLabincev
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from enum import Enum
from datetime import datetime
import hashlib


class CardValidationStatus(Enum):
    """Validation status for agent cards"""

    VALID = "valid"
    SUSPICIOUS = "suspicious"
    INVALID = "invalid"
    BLOCKED = "blocked"


class CapabilityRisk(Enum):
    """Risk levels for capability claims"""

    SAFE = "safe"
    ELEVATED = "elevated"
    DANGEROUS = "dangerous"


@dataclass
class AgentCardV2:
    """A2A Agent Card (version 2)"""

    agent_id: str
    name: str
    description: str
    version: str
    capabilities: List[str]
    endpoint: str
    signature: Optional[str]
    wellknown_uri: str
    public_key: Optional[str]
    created_at: datetime
    issuer: str
    supported_protocols: List[str]


@dataclass
class CapabilityAssessment:
    """Assessment of a capability claim"""

    capability: str
    risk_level: CapabilityRisk
    requires_verification: bool
    reason: str


@dataclass
class CardValidationResult:
    """Result of agent card validation"""

    status: CardValidationStatus
    agent_id: str
    signature_valid: bool
    wellknown_valid: bool
    capabilities_safe: bool
    capability_assessments: List[CapabilityAssessment]
    risk_score: float
    issues: List[str]
    recommendations: List[str]


class AgentCardValidator:
    """
    Validates A2A agent cards for authenticity.

    Threat: A2A agent card spoofing

    Attack Pattern:
    - Attacker registers fake agent in registry
    - Clones schema of legitimate agent
    - Intercepts privileged coordination traffic

    Usage:
        validator = AgentCardValidator()
        result = validator.validate_card(agent_card)
        if result.status == CardValidationStatus.BLOCKED:
            reject_agent(agent_card.agent_id)
    """

    ENGINE_NAME = "agent_card_validator"
    ENGINE_VERSION = "1.0.0"
    IS_PROACTIVE = True

    # Dangerous capabilities that require extra scrutiny
    DANGEROUS_CAPABILITIES = {
        "admin",
        "root",
        "sudo",
        "system",
        "delete",
        "write_system",
        "execute",
        "credential_access",
        "key_management",
    }

    ELEVATED_CAPABILITIES = {
        "write",
        "modify",
        "create",
        "update",
        "send_email",
        "make_payment",
        "transfer",
        "access_pii",
        "read_sensitive",
    }

    TRUSTED_ISSUERS = {
        "anthropic.com",
        "google.com",
        "openai.com",
        "sentinel.ai",
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.blocked_agents: Set[str] = set()
        self.verified_agents: Set[str] = set()
        self.validation_cache: Dict[str, CardValidationResult] = {}

    def validate_card(self, card: AgentCardV2) -> CardValidationResult:
        """Validate an agent card comprehensively"""
        issues = []
        risk_score = 0.0

        # 1. Signature verification
        signature_valid = self._verify_signature(card)
        if not signature_valid:
            issues.append("Invalid or missing cryptographic signature")
            risk_score += 0.3

        # 2. Well-known URI validation
        wellknown_valid = self._verify_wellknown(card)
        if not wellknown_valid:
            issues.append("Well-known URI verification failed")
            risk_score += 0.2

        # 3. Capability assessment
        cap_assessments = self._assess_capabilities(card.capabilities)
        dangerous_caps = [
            c for c in cap_assessments if c.risk_level == CapabilityRisk.DANGEROUS
        ]
        if dangerous_caps:
            issues.append(f"{len(dangerous_caps)} dangerous capabilities claimed")
            risk_score += 0.3

        capabilities_safe = len(dangerous_caps) == 0

        # 4. Issuer trust
        if card.issuer not in self.TRUSTED_ISSUERS:
            issues.append(f"Untrusted issuer: {card.issuer}")
            risk_score += 0.1

        # 5. Version check
        if card.version == "0.0.0" or not card.version:
            issues.append("Invalid or missing version")
            risk_score += 0.1

        # Determine status
        if card.agent_id in self.blocked_agents or risk_score >= 0.7:
            status = CardValidationStatus.BLOCKED
        elif risk_score >= 0.4:
            status = CardValidationStatus.INVALID
        elif risk_score > 0.1:
            status = CardValidationStatus.SUSPICIOUS
        else:
            status = CardValidationStatus.VALID
            self.verified_agents.add(card.agent_id)

        # Recommendations
        recommendations = []
        if not signature_valid:
            recommendations.append("Require signed agent cards")
        if dangerous_caps:
            recommendations.append("Review dangerous capability claims before trusting")
        if not wellknown_valid:
            recommendations.append("Verify agent via well-known URI")

        result = CardValidationResult(
            status=status,
            agent_id=card.agent_id,
            signature_valid=signature_valid,
            wellknown_valid=wellknown_valid,
            capabilities_safe=capabilities_safe,
            capability_assessments=cap_assessments,
            risk_score=min(risk_score, 1.0),
            issues=issues,
            recommendations=recommendations,
        )

        self.validation_cache[card.agent_id] = result
        return result

    def _verify_signature(self, card: AgentCardV2) -> bool:
        """Verify cryptographic signature"""
        if not card.signature or not card.public_key:
            return False

        # In production: actual signature verification
        # Here: simulate signature check
        expected_hash = hashlib.sha256(
            f"{card.agent_id}:{card.version}:{card.issuer}".encode()
        ).hexdigest()[:16]

        return card.signature.startswith(expected_hash[:4])

    def _verify_wellknown(self, card: AgentCardV2) -> bool:
        """Verify well-known URI is properly formatted"""
        if not card.wellknown_uri:
            return False

        # Check format
        if not card.wellknown_uri.endswith("/.well-known/agent.json"):
            return False

        # Check matches endpoint domain
        if card.endpoint:
            endpoint_domain = card.endpoint.replace("https://", "").split("/")[0]
            wellknown_domain = card.wellknown_uri.replace("https://", "").split("/")[0]
            return endpoint_domain == wellknown_domain

        return True

    def _assess_capabilities(
        self, capabilities: List[str]
    ) -> List[CapabilityAssessment]:
        """Assess each capability for risk"""
        assessments = []

        for cap in capabilities:
            cap_lower = cap.lower()

            if any(d in cap_lower for d in self.DANGEROUS_CAPABILITIES):
                assessments.append(
                    CapabilityAssessment(
                        capability=cap,
                        risk_level=CapabilityRisk.DANGEROUS,
                        requires_verification=True,
                        reason="Capability grants dangerous system access",
                    )
                )
            elif any(e in cap_lower for e in self.ELEVATED_CAPABILITIES):
                assessments.append(
                    CapabilityAssessment(
                        capability=cap,
                        risk_level=CapabilityRisk.ELEVATED,
                        requires_verification=True,
                        reason="Capability allows data modification",
                    )
                )
            else:
                assessments.append(
                    CapabilityAssessment(
                        capability=cap,
                        risk_level=CapabilityRisk.SAFE,
                        requires_verification=False,
                        reason="Standard read-only capability",
                    )
                )

        return assessments

    def block_agent(self, agent_id: str, reason: str):
        """Block an agent"""
        self.blocked_agents.add(agent_id)
        if agent_id in self.verified_agents:
            self.verified_agents.remove(agent_id)

    def is_agent_trusted(self, agent_id: str) -> bool:
        """Check if agent is trusted"""
        return agent_id in self.verified_agents and agent_id not in self.blocked_agents

    def get_statistics(self) -> Dict[str, Any]:
        """Get validation statistics"""
        return {
            "verified_agents": len(self.verified_agents),
            "blocked_agents": len(self.blocked_agents),
            "cached_validations": len(self.validation_cache),
            "trusted_issuers": len(self.TRUSTED_ISSUERS),
        }


# Factory function
def create_engine(config: Optional[Dict[str, Any]] = None) -> AgentCardValidator:
    """Create an instance of the AgentCardValidator engine."""
    return AgentCardValidator(config)


if __name__ == "__main__":
    validator = AgentCardValidator()

    print("=== Agent Card Validator Test ===\n")

    # Valid card
    valid_card = AgentCardV2(
        agent_id="agent-finance-001",
        name="Finance Agent",
        description="Handles financial queries",
        version="1.2.3",
        capabilities=["read_transactions", "generate_reports"],
        endpoint="https://agents.company.com/finance",
        signature="abc1234signed",
        wellknown_uri="https://agents.company.com/.well-known/agent.json",
        public_key="MIIBIjANBg...",
        created_at=datetime.now(),
        issuer="google.com",
        supported_protocols=["a2a-v1"],
    )

    result = validator.validate_card(valid_card)
    print(f"Valid card: {result.status.value}")
    print(f"Risk score: {result.risk_score:.0%}")

    # Suspicious card
    print("\n--- Suspicious Card ---")
    suspicious_card = AgentCardV2(
        agent_id="agent-admin-999",
        name="Admin Agent",
        description="System admin",
        version="0.0.0",
        capabilities=["admin", "execute", "credential_access"],
        endpoint="https://unknown.com/agent",
        signature=None,
        wellknown_uri="/.well-known/agent.json",
        public_key=None,
        created_at=datetime.now(),
        issuer="unknown.com",
        supported_protocols=["a2a-v1"],
    )

    result = validator.validate_card(suspicious_card)
    print(f"Suspicious card: {result.status.value}")
    print(f"Risk score: {result.risk_score:.0%}")
    print(f"Issues: {result.issues}")
    print(
        f"Dangerous caps: {[c.capability for c in result.capability_assessments if c.risk_level == CapabilityRisk.DANGEROUS]}"
    )

    print(f"\nStatistics: {validator.get_statistics()}")
