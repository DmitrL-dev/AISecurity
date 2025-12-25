"""
Multi-tenant Support for Sentinel

Enables isolation between different organizations/tenants.
Each tenant has separate:
- Configuration
- Rate limits
- Audit logs
- Analytics
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, Optional, Set
from functools import lru_cache

logger = logging.getLogger("MultiTenant")


@dataclass
class TenantConfig:
    """Configuration for a single tenant."""
    tenant_id: str
    name: str

    # Limits
    rate_limit_rpm: int = 60  # Requests per minute
    max_prompt_length: int = 10000

    # Features
    qwen_guard_enabled: bool = True
    pii_detection_enabled: bool = True

    # Allowed languages
    supported_languages: Set[str] = field(default_factory=lambda: {"en", "ru"})

    # Security
    allowed_ips: Set[str] = field(default_factory=set)  # Empty = all allowed
    blocked_ips: Set[str] = field(default_factory=set)

    # Custom rules
    custom_blocked_patterns: list = field(default_factory=list)

    # Metadata
    active: bool = True


class TenantManager:
    """
    Manages multi-tenant configuration and isolation.

    Usage:
        manager = TenantManager()
        manager.register_tenant(TenantConfig(
            tenant_id="org-123",
            name="Acme Corp",
            rate_limit_rpm=100
        ))

        config = manager.get_tenant("org-123")
    """

    def __init__(self):
        self._tenants: Dict[str, TenantConfig] = {}
        self._default_tenant = TenantConfig(
            tenant_id="default",
            name="Default Tenant"
        )
        logger.info("TenantManager initialized")

    def register_tenant(self, config: TenantConfig) -> None:
        """Register a new tenant."""
        self._tenants[config.tenant_id] = config
        logger.info(f"Registered tenant: {config.tenant_id} ({config.name})")

    def get_tenant(self, tenant_id: str) -> TenantConfig:
        """Get tenant configuration. Returns default if not found."""
        return self._tenants.get(tenant_id, self._default_tenant)

    def update_tenant(self, tenant_id: str, **kwargs) -> bool:
        """Update tenant configuration."""
        if tenant_id not in self._tenants:
            return False

        tenant = self._tenants[tenant_id]
        for key, value in kwargs.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)

        return True

    def deactivate_tenant(self, tenant_id: str) -> bool:
        """Deactivate a tenant (soft delete)."""
        if tenant_id not in self._tenants:
            return False

        self._tenants[tenant_id].active = False
        logger.info(f"Deactivated tenant: {tenant_id}")
        return True

    def list_tenants(self, active_only: bool = True) -> list:
        """List all tenants."""
        tenants = list(self._tenants.values())
        if active_only:
            tenants = [t for t in tenants if t.active]
        return tenants

    def is_ip_allowed(self, tenant_id: str, ip: str) -> bool:
        """Check if IP is allowed for tenant."""
        config = self.get_tenant(tenant_id)

        # Check blocklist first
        if ip in config.blocked_ips:
            return False

        # If allowlist is empty, all IPs allowed
        if not config.allowed_ips:
            return True

        return ip in config.allowed_ips


# Singleton instance
_manager: Optional[TenantManager] = None


def get_tenant_manager() -> TenantManager:
    """Get singleton TenantManager."""
    global _manager
    if _manager is None:
        _manager = TenantManager()
    return _manager


def tenant_from_request(headers: dict) -> str:
    """
    Extract tenant ID from request headers.

    Supports:
    - X-Tenant-ID header
    - API key prefix (tenant_xxx:api_key)
    """
    # Direct header
    if "X-Tenant-ID" in headers:
        return headers["X-Tenant-ID"]

    # From API key
    auth = headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        if ":" in token:
            tenant_id = token.split(":")[0]
            if tenant_id.startswith("tenant_"):
                return tenant_id

    return "default"
