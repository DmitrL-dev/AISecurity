"""
Secure Hierarchical Memory for SENTINEL Integration
====================================================

H-MEM with security features:
- Memory encryption at rest
- Access control and audit logging
- Trust zones for agent isolation
- Memory sanitization

Based on SENTINEL Shield security patterns.
"""

from __future__ import annotations

import time
import hashlib
import threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Callable
from enum import Enum
from enum import Enum

from rlm_toolkit.memory.hierarchical import (
    HierarchicalMemory,
    HMEMConfig,
    MemoryEntry,
    MemoryLevel,
)


class TrustLevel(Enum):
    """Trust levels for memory access."""

    PUBLIC = 0  # Any agent can access
    INTERNAL = 1  # Same trust zone only
    CONFIDENTIAL = 2  # Explicit grant required
    SECRET = 3  # Single agent only, encrypted


class AccessType(Enum):
    """Types of memory access."""

    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    CONSOLIDATE = "consolidate"


@dataclass
class AccessLogEntry:
    """Audit log entry for memory access."""

    timestamp: float
    agent_id: str
    access_type: AccessType
    memory_id: Optional[str]
    trust_zone: str
    success: bool
    details: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "agent_id": self.agent_id,
            "access_type": self.access_type.value,
            "memory_id": self.memory_id,
            "trust_zone": self.trust_zone,
            "success": self.success,
            "details": self.details,
        }


@dataclass
class SecurityPolicy:
    """Security policy for memory access."""

    default_trust_level: TrustLevel = TrustLevel.INTERNAL
    encrypt_at_rest: bool = True
    log_all_access: bool = True
    max_access_log_entries: int = 10000
    require_agent_id: bool = True
    allowed_trust_zones: Optional[Set[str]] = None  # None = all zones

    # Content filtering
    sanitize_content: bool = True
    blocked_patterns: List[str] = field(
        default_factory=lambda: [
            # Sensitive data patterns
            r"\b\d{16}\b",  # Credit card numbers
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"password\s*[:=]\s*\S+",  # Passwords
        ]
    )


class SecureHierarchicalMemory(HierarchicalMemory):
    """
    Security-enhanced Hierarchical Memory.

    Extends H-MEM with:
    - Trust zones for agent isolation
    - Memory encryption at rest
    - Access control and audit logging
    - Content sanitization

    Example:
        >>> from rlm_toolkit.memory.secure import SecureHierarchicalMemory, SecurityPolicy
        >>>
        >>> policy = SecurityPolicy(encrypt_at_rest=True)
        >>> smem = SecureHierarchicalMemory(
        ...     agent_id="agent-001",
        ...     trust_zone="zone-a",
        ...     security_policy=policy
        ... )
        >>> smem.add_episode("User asked about secrets")
        >>> smem.get_access_log()  # Audit trail
    """

    def __init__(
        self,
        agent_id: str,
        trust_zone: str = "default",
        security_policy: Optional[SecurityPolicy] = None,
        encryption_key: Optional[bytes] = None,
        config: Optional[HMEMConfig] = None,
    ):
        """
        Initialize secure H-MEM.

        Args:
            agent_id: Unique identifier for the agent
            trust_zone: Trust zone this memory belongs to
            security_policy: Security configuration
            encryption_key: Key for encryption (auto-generated if None)
            config: Standard HMEMConfig
        """
        super().__init__(config)

        self.agent_id = agent_id
        self.trust_zone = trust_zone
        self.security_policy = security_policy or SecurityPolicy()

        # Generate encryption key if not provided
        if encryption_key:
            self._encryption_key = encryption_key
        else:
            # Simple key derivation (use proper KDF in production)
            key_material = f"{agent_id}:{trust_zone}:{time.time()}"
            self._encryption_key = hashlib.sha256(key_material.encode()).digest()

        # Access control
        self._access_log: List[AccessLogEntry] = []
        self._access_log_lock = threading.Lock()

        # Trust zone grants (agent_id -> granted trust zones)
        self._trust_grants: Dict[str, Set[str]] = {}

    def _log_access(
        self,
        access_type: AccessType,
        memory_id: Optional[str] = None,
        success: bool = True,
        details: Optional[str] = None,
    ) -> None:
        """Log memory access for audit."""
        if not self.security_policy.log_all_access:
            return

        with self._access_log_lock:
            entry = AccessLogEntry(
                timestamp=time.time(),
                agent_id=self.agent_id,
                access_type=access_type,
                memory_id=memory_id,
                trust_zone=self.trust_zone,
                success=success,
                details=details,
            )
            self._access_log.append(entry)

            # Trim log if over limit
            if len(self._access_log) > self.security_policy.max_access_log_entries:
                self._access_log = self._access_log[
                    -self.security_policy.max_access_log_entries :
                ]

    def _encrypt_content(self, content: str) -> str:
        """Encrypt content using AES-256-GCM."""
        if not self.security_policy.encrypt_at_rest:
            return content

        # Use AES-256-GCM from crypto module (REQUIRED)
        from .crypto import SecureEncryption, is_aes_available

        if not is_aes_available():
            raise RuntimeError(
                "cryptography package required for encryption. "
                "Install with: pip install cryptography"
            )

        crypto = SecureEncryption(self._encryption_key)
        return crypto.encrypt_string(content)

    def _decrypt_content(self, encrypted: str) -> str:
        """Decrypt content."""
        if not self.security_policy.encrypt_at_rest:
            return encrypted

        from .crypto import SecureEncryption, is_aes_available

        if not is_aes_available():
            raise RuntimeError(
                "cryptography package required for decryption. "
                "Install with: pip install cryptography"
            )

        crypto = SecureEncryption(self._encryption_key)
        return crypto.decrypt_string(encrypted)

    # XOR fallback methods REMOVED (Security Audit T5.1)
    # These triggered AV heuristics and were never used in production

    def _sanitize_content(self, content: str) -> str:
        """Remove sensitive patterns from content."""
        if not self.security_policy.sanitize_content:
            return content

        import re

        sanitized = content
        for pattern in self.security_policy.blocked_patterns:
            sanitized = re.sub(pattern, "[REDACTED]", sanitized, flags=re.IGNORECASE)

        return sanitized

    def _check_access(
        self,
        access_type: AccessType,
        target_zone: Optional[str] = None,
    ) -> bool:
        """Check if current agent can perform access."""
        target = target_zone or self.trust_zone

        # Check allowed zones
        if self.security_policy.allowed_trust_zones:
            if target not in self.security_policy.allowed_trust_zones:
                return False

        # Same zone always allowed
        if target == self.trust_zone:
            return True

        # Check explicit grants
        if self.agent_id in self._trust_grants:
            if target in self._trust_grants[self.agent_id]:
                return True

        return False

    def add_episode(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ) -> str:
        """Add episode with security features."""
        # Sanitize content
        sanitized = self._sanitize_content(content)

        # Encrypt for storage
        encrypted = self._encrypt_content(sanitized)

        # Add security metadata
        sec_metadata = metadata or {}
        sec_metadata["_trust_level"] = self.security_policy.default_trust_level.value
        sec_metadata["_trust_zone"] = self.trust_zone
        sec_metadata["_agent_id"] = self.agent_id
        sec_metadata["_encrypted"] = self.security_policy.encrypt_at_rest

        # Log access
        entry_id = super().add_episode(encrypted, sec_metadata, embedding)
        self._log_access(AccessType.WRITE, entry_id, True)

        return entry_id

    def retrieve(
        self,
        query: str,
        levels: Optional[List[MemoryLevel]] = None,
        top_k: Optional[int] = None,
        include_children: bool = True,
        decrypt: bool = True,
    ) -> List[MemoryEntry]:
        """Retrieve with decryption and access logging."""
        # Check access
        if not self._check_access(AccessType.READ):
            self._log_access(AccessType.READ, None, False, "Access denied")
            return []

        # Retrieve entries
        entries = super().retrieve(query, levels, top_k, include_children)

        # Decrypt content
        if decrypt:
            for entry in entries:
                if entry.metadata.get("_encrypted"):
                    entry.content = self._decrypt_content(entry.content)

        # Log access
        for entry in entries:
            self._log_access(AccessType.READ, entry.id, True)

        return entries

    def grant_access(self, agent_id: str, trust_zone: str) -> None:
        """Grant an agent access to a trust zone."""
        if agent_id not in self._trust_grants:
            self._trust_grants[agent_id] = set()
        self._trust_grants[agent_id].add(trust_zone)

        self._log_access(
            AccessType.WRITE,
            None,
            True,
            f"Granted {agent_id} access to zone {trust_zone}",
        )

    def revoke_access(self, agent_id: str, trust_zone: str) -> None:
        """Revoke an agent's access to a trust zone."""
        if agent_id in self._trust_grants:
            self._trust_grants[agent_id].discard(trust_zone)

        self._log_access(
            AccessType.DELETE,
            None,
            True,
            f"Revoked {agent_id} access to zone {trust_zone}",
        )

    def get_access_log(
        self,
        limit: Optional[int] = None,
        access_type: Optional[AccessType] = None,
    ) -> List[AccessLogEntry]:
        """Get access audit log."""
        with self._access_log_lock:
            entries = self._access_log.copy()

            if access_type:
                entries = [e for e in entries if e.access_type == access_type]

            if limit:
                entries = entries[-limit:]

            return entries

    def get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics."""
        with self._access_log_lock:
            return {
                "agent_id": self.agent_id,
                "trust_zone": self.trust_zone,
                "total_access_events": len(self._access_log),
                "failed_access_events": sum(
                    1 for e in self._access_log if not e.success
                ),
                "encryption_enabled": self.security_policy.encrypt_at_rest,
                "trust_grants": {k: list(v) for k, v in self._trust_grants.items()},
                "memory_stats": self.get_stats(),
            }

    def clear_with_audit(self, levels: Optional[List[MemoryLevel]] = None) -> int:
        """Clear memories with audit logging."""
        stats_before = self.get_stats()
        self.clear(levels)
        stats_after = self.get_stats()

        cleared = sum(
            stats_before["level_counts"][level]
            - stats_after["level_counts"].get(level, 0)
            for level in stats_before["level_counts"]
        )

        self._log_access(
            AccessType.DELETE,
            None,
            True,
            f"Cleared {cleared} memories from levels {levels or 'all'}",
        )

        return cleared


# Convenience factory
def create_secure_memory(
    agent_id: str, trust_zone: str = "default", encrypt: bool = True, **config_kwargs
) -> SecureHierarchicalMemory:
    """
    Create secure H-MEM with sensible defaults.

    Args:
        agent_id: Agent identifier
        trust_zone: Trust zone name
        encrypt: Enable encryption at rest
        **config_kwargs: Additional HMEMConfig options

    Returns:
        Configured SecureHierarchicalMemory
    """
    policy = SecurityPolicy(encrypt_at_rest=encrypt)
    config = HMEMConfig(**config_kwargs) if config_kwargs else None

    return SecureHierarchicalMemory(
        agent_id=agent_id,
        trust_zone=trust_zone,
        security_policy=policy,
        config=config,
    )
