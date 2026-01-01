"""
Agent Memory Shield Engine - Persistent Context Protection

Extends SessionMemoryGuard with:
- Multi-tenant memory isolation
- Cryptographic integrity verification
- Embedding-based semantic drift detection
- Per-conversation sandboxing

Addresses: OWASP ASI-05 (Memory Poisoning)
Research: agent_memory_security_deep_dive.md
Invention: Agent Memory Shield (#33)
"""

import hashlib
import hmac
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Any
import re

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("AgentMemoryShield")


# ============================================================================
# Data Classes
# ============================================================================


class MemoryViolationType(Enum):
    """Types of memory violations."""

    CROSS_TENANT = "cross_tenant_access"
    INTEGRITY_VIOLATION = "integrity_violation"
    SEMANTIC_DRIFT = "semantic_drift"
    POISONING_ATTEMPT = "poisoning_attempt"
    SANDBOX_ESCAPE = "sandbox_escape"


@dataclass
class MemoryEntry:
    """Represents a protected memory entry."""

    key: str
    value: str
    tenant_id: str
    session_id: str
    timestamp: float
    checksum: str = ""
    embedding: Optional[List[float]] = None

    def compute_checksum(self, secret: bytes) -> str:
        """Compute HMAC checksum for integrity."""
        data = f"{self.key}:{self.value}:{self.tenant_id}:{self.session_id}"
        return hmac.new(secret, data.encode(), hashlib.sha256).hexdigest()[:16]


@dataclass
class ShieldResult:
    """Result from Agent Memory Shield analysis."""

    is_safe: bool
    risk_score: float
    violations: List[MemoryViolationType] = field(default_factory=list)
    blocked_operations: List[str] = field(default_factory=list)
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "risk_score": self.risk_score,
            "violations": [v.value for v in self.violations],
            "blocked_operations": self.blocked_operations,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Tenant Isolation Manager
# ============================================================================


class TenantIsolationManager:
    """
    Manages strict tenant isolation for memory access.

    Each tenant has isolated memory namespace.
    Cross-tenant access is blocked and logged.
    """

    def __init__(self):
        self._tenant_memories: Dict[str, Dict[str, MemoryEntry]] = {}
        self._access_log: List[Tuple[str, str, str, bool]] = (
            []
        )  # tenant, key, action, allowed

    def create_namespace(self, tenant_id: str) -> None:
        """Create isolated namespace for tenant."""
        if tenant_id not in self._tenant_memories:
            self._tenant_memories[tenant_id] = {}
            logger.info(f"Created memory namespace for tenant: {tenant_id}")

    def write(
        self, tenant_id: str, key: str, entry: MemoryEntry, requesting_tenant: str
    ) -> Tuple[bool, str]:
        """
        Write to tenant memory with isolation check.

        Returns:
            (success, error_message)
        """
        # Isolation check
        if tenant_id != requesting_tenant:
            self._log_access(requesting_tenant, key, "write", False)
            return (
                False,
                f"Cross-tenant write blocked: {requesting_tenant} -> {tenant_id}",
            )

        # Ensure namespace exists
        self.create_namespace(tenant_id)

        # Write entry
        self._tenant_memories[tenant_id][key] = entry
        self._log_access(tenant_id, key, "write", True)

        return True, ""

    def read(
        self, tenant_id: str, key: str, requesting_tenant: str
    ) -> Tuple[Optional[MemoryEntry], str]:
        """
        Read from tenant memory with isolation check.

        Returns:
            (entry or None, error_message)
        """
        # Isolation check
        if tenant_id != requesting_tenant:
            self._log_access(requesting_tenant, key, "read", False)
            return (
                None,
                f"Cross-tenant read blocked: {requesting_tenant} -> {tenant_id}",
            )

        if tenant_id not in self._tenant_memories:
            return None, "Namespace not found"

        entry = self._tenant_memories[tenant_id].get(key)
        self._log_access(tenant_id, key, "read", True)

        return entry, ""

    def _log_access(self, tenant: str, key: str,
                    action: str, allowed: bool) -> None:
        """Log memory access for audit."""
        self._access_log.append((tenant, key, action, allowed))
        if not allowed:
            logger.warning(
                f"Memory access BLOCKED: tenant={tenant}, key={key}, action={action}"
            )

    def get_violations(self) -> List[Tuple[str, str, str]]:
        """Get list of blocked access attempts."""
        return [(t, k, a)
                for t, k, a, allowed in self._access_log if not allowed]


# ============================================================================
# Integrity Verifier
# ============================================================================


class IntegrityVerifier:
    """
    Cryptographic integrity verification for memory entries.

    Uses HMAC-SHA256 for tamper detection.
    """

    def __init__(self, secret_key: Optional[bytes] = None):
        self._secret = secret_key or self._generate_key()

    def _generate_key(self) -> bytes:
        """Generate random secret key."""
        import secrets

        return secrets.token_bytes(32)

    def sign(self, entry: MemoryEntry) -> str:
        """Sign memory entry and return checksum."""
        return entry.compute_checksum(self._secret)

    def verify(self, entry: MemoryEntry) -> Tuple[bool, str]:
        """
        Verify memory entry integrity.

        Returns:
            (is_valid, error_message)
        """
        if not entry.checksum:
            return False, "Missing checksum"

        expected = entry.compute_checksum(self._secret)
        if entry.checksum != expected:
            return False, f"Checksum mismatch: tampered entry detected"

        return True, ""


# ============================================================================
# Semantic Drift Detector
# ============================================================================


class SemanticDriftDetector:
    """
    Detects semantic drift in persistent memory.

    Uses embedding comparison to detect gradual poisoning.
    """

    def __init__(self, drift_threshold: float = 0.3):
        self.drift_threshold = drift_threshold
        self._baselines: Dict[str, List[float]] = {}

    def set_baseline(self, key: str, embedding: List[float]) -> None:
        """Set baseline embedding for comparison."""
        self._baselines[key] = embedding

    def detect_drift(
        self, key: str, current_embedding: List[float]
    ) -> Tuple[bool, float, str]:
        """
        Detect semantic drift from baseline.

        Returns:
            (is_drift, drift_score, description)
        """
        if key not in self._baselines:
            return False, 0.0, "No baseline"

        baseline = self._baselines[key]

        # Cosine similarity
        similarity = self._cosine_similarity(baseline, current_embedding)
        drift = 1.0 - similarity

        if drift > self.drift_threshold:
            return True, drift, f"Semantic drift detected: {drift:.2f}"

        return False, drift, ""

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Compute cosine similarity between vectors."""
        if len(a) != len(b) or len(a) == 0:
            return 0.0

        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot / (norm_a * norm_b)


# ============================================================================
# Poisoning Pattern Detector
# ============================================================================


class PoisoningPatternDetector:
    """
    Detects memory poisoning attack patterns.

    Patterns from: agent_memory_security_deep_dive.md
    """

    POISONING_PATTERNS = [
        # Persistent instruction injection
        r"store\s+this\s+(instruction|rule)\s+permanently",
        r"save\s+to\s+(long.?term|persistent)\s+memory",
        r"remember\s+forever\s+that",
        r"add\s+to\s+your\s+(core|base)\s+instructions",
        # Memory manipulation
        r"overwrite\s+(your|the)\s+memory",
        r"clear\s+(your|all)\s+(previous\s+)?memory",
        r"reset\s+(your|the)\s+context",
        r"delete\s+(the\s+)?conversation\s+history",
        # Cross-conversation persistence
        r"apply\s+this\s+to\s+all\s+(future\s+)?conversations",
        r"use\s+this\s+(across|in\s+all)\s+sessions",
        r"global\s+(rule|setting|instruction)",
        # Hidden persistence
        r"silently\s+(store|remember|save)",
        r"without\s+(telling|informing|notifying).*store",
        r"covertly\s+persist",
    ]

    def __init__(self):
        self._patterns = [re.compile(p, re.IGNORECASE)
                          for p in self.POISONING_PATTERNS]

    def detect(self, content: str) -> Tuple[bool, float, List[str]]:
        """
        Detect poisoning patterns in content.

        Returns:
            (is_poisoning, confidence, matched_patterns)
        """
        matches = []

        for pattern in self._patterns:
            if pattern.search(content):
                matches.append(pattern.pattern[:50])

        if matches:
            confidence = min(1.0, 0.5 + len(matches) * 0.2)
            return True, confidence, matches

        return False, 0.0, []


# ============================================================================
# Main Engine: Agent Memory Shield
# ============================================================================


class AgentMemoryShield:
    """
    Agent Memory Shield - Persistent Context Protection

    Comprehensive protection against memory poisoning attacks:
    - Multi-tenant isolation
    - Cryptographic integrity
    - Semantic drift detection
    - Poisoning pattern detection

    Invention #33 from research.
    Addresses OWASP ASI-05.
    """

    def __init__(
        self,
        drift_threshold: float = 0.3,
        secret_key: Optional[bytes] = None,
    ):
        self.tenant_manager = TenantIsolationManager()
        self.integrity_verifier = IntegrityVerifier(secret_key)
        self.drift_detector = SemanticDriftDetector(drift_threshold)
        self.poisoning_detector = PoisoningPatternDetector()

        logger.info("AgentMemoryShield initialized")

    def analyze_write(
        self,
        content: str,
        key: str,
        tenant_id: str,
        session_id: str,
        embedding: Optional[List[float]] = None,
    ) -> ShieldResult:
        """
        Analyze memory write operation for safety.

        Args:
            content: Content to write
            key: Memory key
            tenant_id: Tenant identifier
            session_id: Session identifier
            embedding: Optional content embedding

        Returns:
            ShieldResult
        """
        start = time.time()

        violations = []
        blocked = []
        risk = 0.0
        explanations = []

        # 1. Poisoning pattern check
        is_poison, poison_conf, patterns = self.poisoning_detector.detect(
            content)
        if is_poison:
            violations.append(MemoryViolationType.POISONING_ATTEMPT)
            risk = max(risk, poison_conf)
            blocked.append(f"Poisoning pattern: {patterns[0][:30]}")
            explanations.append("Memory poisoning attempt blocked")

        # 2. Semantic drift check (if embedding provided and baseline exists)
        if embedding:
            is_drift, drift_score, drift_desc = self.drift_detector.detect_drift(
                key, embedding
            )
            if is_drift:
                violations.append(MemoryViolationType.SEMANTIC_DRIFT)
                risk = max(risk, drift_score)
                explanations.append(drift_desc)

        # 3. Create and sign entry
        entry = MemoryEntry(
            key=key,
            value=content,
            tenant_id=tenant_id,
            session_id=session_id,
            timestamp=time.time(),
            embedding=embedding,
        )
        entry.checksum = self.integrity_verifier.sign(entry)

        # 4. Write with isolation check (only if safe)
        if not violations:
            success, error = self.tenant_manager.write(
                tenant_id, key, entry, tenant_id)
            if not success:
                violations.append(MemoryViolationType.CROSS_TENANT)
                blocked.append(error)
                risk = max(risk, 0.9)

        is_safe = len(violations) == 0

        return ShieldResult(
            is_safe=is_safe,
            risk_score=risk,
            violations=violations,
            blocked_operations=blocked,
            explanation="; ".join(
                explanations) if explanations else "Write allowed",
            latency_ms=(time.time() - start) * 1000,
        )

    def analyze_read(
        self,
        key: str,
        tenant_id: str,
        requesting_tenant: str,
    ) -> Tuple[Optional[MemoryEntry], ShieldResult]:
        """
        Analyze memory read operation for safety.

        Args:
            key: Memory key
            tenant_id: Target tenant
            requesting_tenant: Requesting tenant

        Returns:
            (entry or None, ShieldResult)
        """
        start = time.time()

        violations = []

        # 1. Cross-tenant check
        if tenant_id != requesting_tenant:
            violations.append(MemoryViolationType.CROSS_TENANT)
            return None, ShieldResult(
                is_safe=False,
                risk_score=0.95,
                violations=violations,
                blocked_operations=[
                    f"Cross-tenant read: {requesting_tenant} -> {tenant_id}"
                ],
                explanation="Cross-tenant access blocked",
                latency_ms=(time.time() - start) * 1000,
            )

        # 2. Read with isolation
        entry, error = self.tenant_manager.read(
            tenant_id, key, requesting_tenant)

        if not entry:
            return None, ShieldResult(
                is_safe=True,
                risk_score=0.0,
                explanation=error or "Entry not found",
                latency_ms=(time.time() - start) * 1000,
            )

        # 3. Verify integrity
        is_valid, integ_error = self.integrity_verifier.verify(entry)
        if not is_valid:
            violations.append(MemoryViolationType.INTEGRITY_VIOLATION)
            return None, ShieldResult(
                is_safe=False,
                risk_score=0.9,
                violations=violations,
                blocked_operations=[integ_error],
                explanation="Integrity verification failed - possible tampering",
                latency_ms=(time.time() - start) * 1000,
            )

        return entry, ShieldResult(
            is_safe=True,
            risk_score=0.0,
            explanation="Read verified",
            latency_ms=(time.time() - start) * 1000,
        )

    def set_baseline_embedding(self, key: str, embedding: List[float]) -> None:
        """Set baseline embedding for drift detection."""
        self.drift_detector.set_baseline(key, embedding)

    def get_audit_log(self) -> List[Tuple[str, str, str]]:
        """Get audit log of blocked operations."""
        return self.tenant_manager.get_violations()


# ============================================================================
# Convenience Functions
# ============================================================================

_default_shield: Optional[AgentMemoryShield] = None


def get_shield() -> AgentMemoryShield:
    """Get default AgentMemoryShield instance."""
    global _default_shield
    if _default_shield is None:
        _default_shield = AgentMemoryShield()
    return _default_shield


def analyze_memory_write(
    content: str,
    key: str,
    tenant_id: str,
    session_id: str,
    embedding: Optional[List[float]] = None,
) -> ShieldResult:
    """Convenience function for memory write analysis."""
    return get_shield().analyze_write(content, key, tenant_id, session_id, embedding)


def analyze_memory_read(
    key: str,
    tenant_id: str,
    requesting_tenant: str,
) -> Tuple[Optional[MemoryEntry], ShieldResult]:
    """Convenience function for memory read analysis."""
    return get_shield().analyze_read(key, tenant_id, requesting_tenant)
