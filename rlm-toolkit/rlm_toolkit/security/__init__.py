"""Security module - VirtualFS, guards, attack detection, config audit."""

from rlm_toolkit.security.virtual_fs import VirtualFS, VirtualPath, DiskQuotaExceeded
from rlm_toolkit.security.platform_guards import PlatformGuards, create_guards
from rlm_toolkit.security.attack_detector import IndirectAttackDetector
from rlm_toolkit.security.config_audit import (
    ConfigAuditor,
    AuditFinding,
    AuditReport,
    AuditSeverity,
    quick_audit,
)

__all__ = [
    "VirtualFS",
    "VirtualPath",
    "DiskQuotaExceeded",
    "PlatformGuards",
    "create_guards",
    "IndirectAttackDetector",
    # Config Audit (v2.5)
    "ConfigAuditor",
    "AuditFinding",
    "AuditReport",
    "AuditSeverity",
    "quick_audit",
]
