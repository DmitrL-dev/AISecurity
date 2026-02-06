"""
BindingAudit — Persistent Service Connection Tracker

Tracks all persistent bindings (OAuth, API keys, webhooks) between AI agents
and external services. Auto-expires bindings after 24h, requires re-approval.

Based on Substack critique: "One-time approval → permanent trusted access"
Solution: Track binding age, activity, force periodic re-approval.

Usage:
    from sentinel.brain.core.binding_audit import BindingAudit

    audit = BindingAudit()
    audit.register_binding("telegram", "user@telegram", scope="send_message")

    # Check if binding is still valid
    if not audit.is_valid("telegram"):
        raise SecurityError("Binding expired, re-approval required")

    # Get all bindings for dashboard
    bindings = audit.list_bindings()
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
import json
import hashlib


class BindingStatus(Enum):
    """Binding lifecycle states"""

    ACTIVE = "active"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PENDING = "pending"


class BindingRisk(Enum):
    """Risk level based on binding capabilities"""

    LOW = "low"  # Read-only access
    MEDIUM = "medium"  # Write access
    HIGH = "high"  # External communication
    CRITICAL = "critical"  # Financial or credential access


@dataclass
class Binding:
    """Represents a persistent connection to an external service"""

    service: str  # e.g., "telegram", "slack", "google_drive"
    target: str  # e.g., "user@telegram", "channel#general"
    scope: str  # e.g., "send_message", "read_files"
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    status: BindingStatus = BindingStatus.ACTIVE
    risk: BindingRisk = BindingRisk.MEDIUM
    approval_source: str = "unknown"  # Who approved: "user", "system", "auto"
    activity_count: int = 0

    def __post_init__(self):
        if self.expires_at is None:
            # Default: 24h expiration
            self.expires_at = self.created_at + timedelta(hours=24)
        self.last_activity = self.created_at

    @property
    def age_hours(self) -> float:
        """Hours since binding was created"""
        return (datetime.now() - self.created_at).total_seconds() / 3600

    @property
    def idle_hours(self) -> float:
        """Hours since last activity"""
        if self.last_activity:
            return (datetime.now() - self.last_activity).total_seconds() / 3600
        return self.age_hours

    @property
    def is_expired(self) -> bool:
        """Check if binding has expired by TTL"""
        if self.expires_at:
            return datetime.now() > self.expires_at
        return False

    @property
    def is_valid(self) -> bool:
        """Check if binding can be used"""
        return self.status == BindingStatus.ACTIVE and not self.is_expired

    def record_activity(self):
        """Record that binding was used"""
        self.last_activity = datetime.now()
        self.activity_count += 1

    def revoke(self):
        """Manually revoke binding"""
        self.status = BindingStatus.REVOKED

    def renew(self, hours: int = 24):
        """Renew binding with new expiration"""
        self.expires_at = datetime.now() + timedelta(hours=hours)
        self.status = BindingStatus.ACTIVE

    def to_dict(self) -> dict:
        """Serialize for dashboard/API"""
        return {
            "service": self.service,
            "target": self.target,
            "scope": self.scope,
            "created_at": self.created_at.isoformat(),
            "last_activity": (
                self.last_activity.isoformat() if self.last_activity else None
            ),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "status": self.status.value,
            "risk": self.risk.value,
            "age_hours": round(self.age_hours, 1),
            "idle_hours": round(self.idle_hours, 1),
            "activity_count": self.activity_count,
            "is_valid": self.is_valid,
        }


class BindingAudit:
    """
    Tracks all persistent service bindings with auto-expiration.

    Key security principle: "Remote code execution by another name"
    - Bindings = permanent trusted channels
    - Must track, expire, and require re-approval
    """

    # High-risk services requiring shorter TTL
    HIGH_RISK_SERVICES = {
        "telegram",
        "whatsapp",
        "slack_webhook",
        "email",
        "sms",
        "crypto_wallet",
    }

    # Services with financial/credential access
    CRITICAL_SERVICES = {
        "stripe",
        "paypal",
        "aws",
        "gcp",
        "azure",
        "github_api",
        "gitlab_api",
    }

    def __init__(self, default_ttl_hours: int = 24):
        self._bindings: dict[str, Binding] = {}
        self.default_ttl = timedelta(hours=default_ttl_hours)
        self._audit_log: list[dict] = []

    def _binding_id(self, service: str, target: str) -> str:
        """Generate unique binding ID"""
        return hashlib.sha256(f"{service}:{target}".encode()).hexdigest()[:16]

    def _assess_risk(self, service: str, scope: str) -> BindingRisk:
        """Assess risk level of a binding"""
        if service.lower() in self.CRITICAL_SERVICES:
            return BindingRisk.CRITICAL
        if service.lower() in self.HIGH_RISK_SERVICES:
            return BindingRisk.HIGH
        if "write" in scope.lower() or "send" in scope.lower():
            return BindingRisk.MEDIUM
        return BindingRisk.LOW

    def _get_ttl(self, risk: BindingRisk) -> timedelta:
        """Get TTL based on risk level"""
        ttl_hours = {
            BindingRisk.LOW: 72,  # 3 days
            BindingRisk.MEDIUM: 24,  # 1 day
            BindingRisk.HIGH: 8,  # 8 hours
            BindingRisk.CRITICAL: 1,  # 1 hour
        }
        return timedelta(hours=ttl_hours.get(risk, 24))

    def _log_event(self, event_type: str, binding_id: str, details: dict):
        """Add to audit log"""
        self._audit_log.append(
            {
                "timestamp": datetime.now().isoformat(),
                "event": event_type,
                "binding_id": binding_id,
                **details,
            }
        )

    def register_binding(
        self,
        service: str,
        target: str,
        scope: str = "default",
        approval_source: str = "user",
    ) -> Binding:
        """
        Register a new binding. Auto-sets risk level and TTL.

        Args:
            service: Service name (e.g., "telegram")
            target: Target identifier (e.g., "user@telegram")
            scope: Permission scope (e.g., "send_message")
            approval_source: Who approved ("user", "system", "auto")

        Returns:
            Binding object
        """
        binding_id = self._binding_id(service, target)
        risk = self._assess_risk(service, scope)
        ttl = self._get_ttl(risk)

        binding = Binding(
            service=service,
            target=target,
            scope=scope,
            risk=risk,
            expires_at=datetime.now() + ttl,
            approval_source=approval_source,
        )

        self._bindings[binding_id] = binding
        self._log_event(
            "binding_created",
            binding_id,
            {
                "service": service,
                "target": target,
                "risk": risk.value,
                "ttl_hours": ttl.total_seconds() / 3600,
            },
        )

        return binding

    def is_valid(self, service: str, target: str = "") -> bool:
        """Check if a binding is still valid"""
        # Find by service (optionally with target)
        for bid, binding in self._bindings.items():
            if binding.service == service:
                if target and binding.target != target:
                    continue
                return binding.is_valid
        return False

    def use_binding(self, service: str, target: str = "") -> bool:
        """
        Record usage of a binding. Returns False if invalid.

        Raises:
            SecurityError: If binding expired or revoked
        """
        for bid, binding in self._bindings.items():
            if binding.service == service:
                if target and binding.target != target:
                    continue

                if not binding.is_valid:
                    self._log_event(
                        "binding_blocked",
                        bid,
                        {"reason": "expired" if binding.is_expired else "revoked"},
                    )
                    raise SecurityError(
                        f"Binding {service} expired. Re-approval required."
                    )

                binding.record_activity()
                self._log_event(
                    "binding_used", bid, {"activity_count": binding.activity_count}
                )
                return True

        raise SecurityError(f"No binding found for service: {service}")

    def revoke(self, service: str, target: str = ""):
        """Revoke a binding"""
        for bid, binding in self._bindings.items():
            if binding.service == service:
                if target and binding.target != target:
                    continue
                binding.revoke()
                self._log_event("binding_revoked", bid, {})
                return

    def renew(self, service: str, target: str = "", hours: int = 24):
        """Renew a binding with new TTL"""
        for bid, binding in self._bindings.items():
            if binding.service == service:
                if target and binding.target != target:
                    continue
                binding.renew(hours)
                self._log_event("binding_renewed", bid, {"hours": hours})
                return

    def list_bindings(self) -> list[dict]:
        """Get all bindings for dashboard display"""
        return [b.to_dict() for b in self._bindings.values()]

    def get_expired(self) -> list[Binding]:
        """Get all expired bindings needing re-approval"""
        return [b for b in self._bindings.values() if b.is_expired]

    def get_high_risk(self) -> list[Binding]:
        """Get all high/critical risk bindings"""
        return [
            b
            for b in self._bindings.values()
            if b.risk in (BindingRisk.HIGH, BindingRisk.CRITICAL)
        ]

    def cleanup_expired(self) -> int:
        """Remove expired bindings. Returns count removed."""
        expired_ids = [bid for bid, b in self._bindings.items() if b.is_expired]
        for bid in expired_ids:
            del self._bindings[bid]
            self._log_event("binding_cleaned", bid, {})
        return len(expired_ids)

    def get_audit_log(self, limit: int = 100) -> list[dict]:
        """Get recent audit log entries"""
        return self._audit_log[-limit:]

    def summary(self) -> dict:
        """Dashboard summary stats"""
        bindings = list(self._bindings.values())
        return {
            "total": len(bindings),
            "active": sum(1 for b in bindings if b.is_valid),
            "expired": sum(1 for b in bindings if b.is_expired),
            "revoked": sum(1 for b in bindings if b.status == BindingStatus.REVOKED),
            "high_risk": sum(
                1
                for b in bindings
                if b.risk in (BindingRisk.HIGH, BindingRisk.CRITICAL)
            ),
            "avg_age_hours": (
                round(sum(b.age_hours for b in bindings) / len(bindings), 1)
                if bindings
                else 0
            ),
        }


class SecurityError(Exception):
    """Raised when security policy is violated"""

    pass


# === TDD Tests ===


def test_binding_creation():
    """Test basic binding creation"""
    audit = BindingAudit()
    binding = audit.register_binding("telegram", "user@tg", "send_message")

    assert binding.service == "telegram"
    assert binding.is_valid
    assert binding.risk == BindingRisk.HIGH  # telegram = high risk


def test_binding_expiration():
    """Test binding auto-expiration"""
    audit = BindingAudit()
    binding = audit.register_binding("test_service", "target", "read")

    # Manually expire
    binding.expires_at = datetime.now() - timedelta(hours=1)

    assert binding.is_expired
    assert not binding.is_valid


def test_binding_revocation():
    """Test manual revocation"""
    audit = BindingAudit()
    binding = audit.register_binding("slack", "channel", "write")

    assert binding.is_valid
    audit.revoke("slack")
    assert not binding.is_valid
    assert binding.status == BindingStatus.REVOKED


def test_use_expired_binding_raises():
    """Test that using expired binding raises SecurityError"""
    audit = BindingAudit()
    binding = audit.register_binding("email", "user@mail", "send")
    binding.expires_at = datetime.now() - timedelta(hours=1)

    try:
        audit.use_binding("email")
        assert False, "Should have raised SecurityError"
    except SecurityError as e:
        assert "expired" in str(e).lower()


def test_critical_service_short_ttl():
    """Test that critical services get 1-hour TTL"""
    audit = BindingAudit()
    binding = audit.register_binding("stripe", "account", "charge")

    assert binding.risk == BindingRisk.CRITICAL
    # TTL should be ~1 hour
    ttl_hours = (binding.expires_at - binding.created_at).total_seconds() / 3600
    assert ttl_hours <= 1.1  # Allow small delta


def test_activity_tracking():
    """Test binding activity recording"""
    audit = BindingAudit()
    binding = audit.register_binding("gdrive", "folder", "read")

    assert binding.activity_count == 0
    audit.use_binding("gdrive")
    assert binding.activity_count == 1


def test_list_bindings_for_dashboard():
    """Test dashboard listing"""
    audit = BindingAudit()
    audit.register_binding("telegram", "user", "send")
    audit.register_binding("slack", "channel", "write")

    bindings = audit.list_bindings()
    assert len(bindings) == 2
    assert all("age_hours" in b for b in bindings)
    assert all("is_valid" in b for b in bindings)


def test_summary_stats():
    """Test summary statistics"""
    audit = BindingAudit()
    audit.register_binding("a", "1", "x")
    audit.register_binding("b", "2", "y")

    summary = audit.summary()
    assert summary["total"] == 2
    assert summary["active"] == 2


if __name__ == "__main__":
    # Run tests
    test_binding_creation()
    test_binding_expiration()
    test_binding_revocation()
    test_use_expired_binding_raises()
    test_critical_service_short_ttl()
    test_activity_tracking()
    test_list_bindings_for_dashboard()
    test_summary_stats()
    print("✅ All 8 BindingAudit tests passed!")
