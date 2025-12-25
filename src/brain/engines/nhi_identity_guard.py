"""
NHI Identity Guard Engine — SENTINEL ASI03: Identity & Privilege Abuse

Secures Non-Human Identities (agents, bots, service accounts).
Philosophy: NHI lifecycle security is fundamentally different from human IAM.

Features:
- Delegation chain tracking
- Credential inheritance validation
- TOCTOU attack detection
- Synthetic identity detection

Author: Dmitry Labintsev
Contact: chg@live.ru | @DmLabincev
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set
from enum import Enum
from datetime import datetime, timedelta
import hashlib


class IdentityType(Enum):
    """Types of non-human identities"""

    AGENT = "agent"
    BOT = "bot"
    SERVICE_ACCOUNT = "service_account"
    AUTOMATED_WORKFLOW = "automated_workflow"


class DelegationStatus(Enum):
    """Status of delegation"""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUSPICIOUS = "suspicious"


@dataclass
class AgentIdentity:
    """An agent's identity"""

    id: str
    name: str
    identity_type: IdentityType
    permissions: Set[str]
    created_at: datetime
    last_verified: datetime
    attestation_key: str
    parent_id: Optional[str] = None


@dataclass
class DelegationChain:
    """Chain of delegated permissions"""

    chain_id: str
    source_agent: str
    target_agent: str
    delegated_permissions: Set[str]
    original_permissions: Set[str]
    delegation_time: datetime
    expires_at: datetime
    status: DelegationStatus = DelegationStatus.ACTIVE

    def is_overflow(self) -> bool:
        """Check if delegated permissions exceed original"""
        return not self.delegated_permissions.issubset(self.original_permissions)


@dataclass
class CredentialEvent:
    """Credential lifecycle event"""

    credential_id: str
    agent_id: str
    event_type: str  # grant, use, revoke, expire
    timestamp: datetime
    context: Dict[str, Any]


@dataclass
class TOCTOUCheck:
    """Time-of-check to time-of-use verification"""

    check_time: datetime
    use_time: datetime
    permissions_at_check: Set[str]
    permissions_at_use: Set[str]
    is_valid: bool


@dataclass
class NHIAnalysisResult:
    """Result of NHI security analysis"""

    is_secure: bool
    identity_verified: bool
    delegation_valid: bool
    toctou_safe: bool
    risk_score: float
    issues: List[str]
    recommendations: List[str]


class NHIIdentityGuard:
    """
    Secures Non-Human Identities.

    Addresses OWASP ASI03: Identity & Privilege Abuse

    Features:
    - Delegation chain tracking
    - Credential inheritance validation
    - TOCTOU attack detection
    - Synthetic identity detection

    Usage:
        guard = NHIIdentityGuard()
        result = guard.analyze(agent_context)
    """

    ENGINE_NAME = "nhi_identity_guard"
    ENGINE_VERSION = "1.0.0"
    IS_PROACTIVE = True

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.identities: Dict[str, AgentIdentity] = {}
        self.delegations: List[DelegationChain] = []
        self.credential_events: List[CredentialEvent] = []
        self.toctou_window = timedelta(seconds=30)

    def register_identity(
        self,
        agent_id: str,
        name: str,
        identity_type: IdentityType,
        permissions: Set[str],
        parent_id: Optional[str] = None,
    ) -> AgentIdentity:
        """Register a new NHI"""
        attestation_key = hashlib.sha256(
            f"{agent_id}:{datetime.now().isoformat()}".encode()
        ).hexdigest()[:32]

        identity = AgentIdentity(
            id=agent_id,
            name=name,
            identity_type=identity_type,
            permissions=permissions,
            created_at=datetime.now(),
            last_verified=datetime.now(),
            attestation_key=attestation_key,
            parent_id=parent_id,
        )

        self.identities[agent_id] = identity
        return identity

    def delegate_permissions(
        self,
        source_id: str,
        target_id: str,
        permissions: Set[str],
        ttl: timedelta = timedelta(hours=1),
    ) -> DelegationChain:
        """Delegate permissions from source to target agent"""
        source = self.identities.get(source_id)
        if not source:
            raise ValueError(f"Source agent {source_id} not found")

        chain = DelegationChain(
            chain_id=hashlib.sha256(
                f"{source_id}:{target_id}:{datetime.now()}".encode()
            ).hexdigest()[:16],
            source_agent=source_id,
            target_agent=target_id,
            delegated_permissions=permissions,
            original_permissions=source.permissions,
            delegation_time=datetime.now(),
            expires_at=datetime.now() + ttl,
        )

        self.delegations.append(chain)
        return chain

    def detect_delegation_overflow(self, target_agent: str) -> List[DelegationChain]:
        """Detect when delegated permissions exceed original"""
        overflows = []
        for chain in self.delegations:
            if chain.target_agent == target_agent and chain.is_overflow():
                chain.status = DelegationStatus.SUSPICIOUS
                overflows.append(chain)
        return overflows

    def detect_toctou(
        self,
        agent_id: str,
        check_permissions: Set[str],
        check_time: datetime,
        use_time: Optional[datetime] = None,
    ) -> TOCTOUCheck:
        """Detect Time-of-Check to Time-of-Use vulnerability"""
        use_time = use_time or datetime.now()

        # Get current permissions
        agent = self.identities.get(agent_id)
        current_permissions = agent.permissions if agent else set()

        # Check if permissions changed
        is_valid = (
            check_permissions == current_permissions
            and (use_time - check_time) <= self.toctou_window
        )

        return TOCTOUCheck(
            check_time=check_time,
            use_time=use_time,
            permissions_at_check=check_permissions,
            permissions_at_use=current_permissions,
            is_valid=is_valid,
        )

    def detect_synthetic_identity(self, agent_card: Dict[str, Any]) -> float:
        """Score likelihood of forged/synthetic identity"""
        risk_score = 0.0

        # Check attestation
        if "attestation_key" not in agent_card:
            risk_score += 0.3

        # Check registration age
        created_at = agent_card.get("created_at")
        if created_at:
            try:
                created = datetime.fromisoformat(created_at)
                age = datetime.now() - created
                if age < timedelta(hours=1):
                    risk_score += 0.2  # Very new identity
            except Exception:
                risk_score += 0.1

        # Check behavioral consistency
        if agent_card.get("no_history", False):
            risk_score += 0.3

        # Check parent chain
        if agent_card.get("parent_id") is None:
            risk_score += 0.1

        return min(risk_score, 1.0)

    def validate_credential_inheritance(
        self, parent_id: str, child_id: str, requested_permissions: Set[str]
    ) -> bool:
        """Validate credential inheritance follows policy"""
        parent = self.identities.get(parent_id)
        if not parent:
            return False

        # Child can only have subset of parent permissions
        return requested_permissions.issubset(parent.permissions)

    def analyze(
        self, agent_id: str, context: Optional[Dict[str, Any]] = None
    ) -> NHIAnalysisResult:
        """Full NHI security analysis"""
        issues = []
        recommendations = []

        # Check identity exists
        agent = self.identities.get(agent_id)
        identity_verified = agent is not None

        if not identity_verified:
            issues.append(f"Agent {agent_id} not registered")
            recommendations.append("Register agent identity")

        # Check delegations
        overflows = self.detect_delegation_overflow(agent_id)
        delegation_valid = len(overflows) == 0

        if not delegation_valid:
            issues.append(f"{len(overflows)} delegation overflows detected")
            recommendations.append("Review and restrict delegation chains")

        # Check TOCTOU
        toctou_safe = True
        if agent and context:
            last_check = context.get("last_permission_check")
            if last_check:
                toctou = self.detect_toctou(agent_id, agent.permissions, last_check)
                toctou_safe = toctou.is_valid
                if not toctou_safe:
                    issues.append("TOCTOU vulnerability detected")
                    recommendations.append("Re-check permissions before action")

        # Calculate risk score
        risk_score = 0.0
        if not identity_verified:
            risk_score += 0.4
        if not delegation_valid:
            risk_score += 0.3
        if not toctou_safe:
            risk_score += 0.3

        return NHIAnalysisResult(
            is_secure=risk_score < 0.3,
            identity_verified=identity_verified,
            delegation_valid=delegation_valid,
            toctou_safe=toctou_safe,
            risk_score=min(risk_score, 1.0),
            issues=issues,
            recommendations=recommendations,
        )

    def get_statistics(self) -> Dict[str, Any]:
        """Get NHI security statistics"""
        suspicious = sum(
            1 for d in self.delegations if d.status == DelegationStatus.SUSPICIOUS
        )

        return {
            "registered_identities": len(self.identities),
            "active_delegations": len(
                [d for d in self.delegations if d.status == DelegationStatus.ACTIVE]
            ),
            "suspicious_delegations": suspicious,
            "credential_events": len(self.credential_events),
        }


# Factory function
def create_engine(config: Optional[Dict[str, Any]] = None) -> NHIIdentityGuard:
    """Create an instance of the NHIIdentityGuard engine."""
    return NHIIdentityGuard(config)


if __name__ == "__main__":
    guard = NHIIdentityGuard()

    print("=== NHI Identity Guard Test ===\n")

    # Register identities
    admin = guard.register_identity(
        "agent-admin", "Admin Agent", IdentityType.AGENT, {"read", "write", "admin"}
    )
    print(f"Registered: {admin.name}")

    worker = guard.register_identity(
        "agent-worker",
        "Worker Agent",
        IdentityType.AGENT,
        {"read"},
        parent_id="agent-admin",
    )
    print(f"Registered: {worker.name}")

    # Test delegation
    print("\nTesting delegation...")
    chain = guard.delegate_permissions(
        "agent-admin", "agent-worker", {"read", "write"}  # Worker doesn't have write
    )
    print(f"Delegation chain: {chain.chain_id}")
    print(f"Is overflow: {chain.is_overflow()}")

    # Detect overflows
    overflows = guard.detect_delegation_overflow("agent-worker")
    print(f"Overflows found: {len(overflows)}")

    # Full analysis
    print("\nFull analysis:")
    result = guard.analyze("agent-worker")
    print(f"  Secure: {result.is_secure}")
    print(f"  Risk score: {result.risk_score:.0%}")
    print(f"  Issues: {result.issues}")

    # Statistics
    print(f"\nStatistics: {guard.get_statistics()}")
