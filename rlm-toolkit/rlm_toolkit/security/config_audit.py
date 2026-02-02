"""
Configuration Security Audit.

Multi-layer security checks for RLM configurations.
Inspired by OpenClaw's security/audit.ts pattern.

Example:
    >>> auditor = ConfigAuditor()
    >>> report = auditor.audit()
    >>> if report.has_critical:
    ...     print("Critical issues found!")
    ...     for finding in report.critical_findings:
    ...         print(f"  - {finding.message}")
"""

from __future__ import annotations

import os
import stat
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
import logging

logger = logging.getLogger(__name__)


class AuditSeverity(Enum):
    """Severity level for audit findings."""
    CRITICAL = "critical"   # Must fix immediately
    WARNING = "warning"     # Should fix soon
    INFO = "info"           # Informational / best practice


@dataclass
class AuditFinding:
    """A single audit finding.

    Attributes:
        category: Check category (filesystem, config, gateway, etc.)
        severity: Severity level
        message: Human-readable description
        recommendation: How to fix
        metadata: Additional context
    """
    category: str
    severity: AuditSeverity
    message: str
    recommendation: str
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict:
        """Serialize finding."""
        return {
            "category": self.category,
            "severity": self.severity.value,
            "message": self.message,
            "recommendation": self.recommendation,
            "metadata": self.metadata,
        }


@dataclass
class AuditReport:
    """Complete audit report.

    Attributes:
        findings: All findings
        timestamp: When audit was run
        duration_ms: How long audit took
    """
    findings: List[AuditFinding] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: float = 0.0

    @property
    def critical_findings(self) -> List[AuditFinding]:
        """Get critical severity findings."""
        return [f for f in self.findings if f.severity == AuditSeverity.CRITICAL]

    @property
    def warning_findings(self) -> List[AuditFinding]:
        """Get warning severity findings."""
        return [f for f in self.findings if f.severity == AuditSeverity.WARNING]

    @property
    def info_findings(self) -> List[AuditFinding]:
        """Get info severity findings."""
        return [f for f in self.findings if f.severity == AuditSeverity.INFO]

    @property
    def has_critical(self) -> bool:
        """Check if any critical findings exist."""
        return len(self.critical_findings) > 0

    @property
    def has_warnings(self) -> bool:
        """Check if any warning findings exist."""
        return len(self.warning_findings) > 0

    def summary(self) -> Dict:
        """Get report summary."""
        return {
            "total_findings": len(self.findings),
            "critical": len(self.critical_findings),
            "warnings": len(self.warning_findings),
            "info": len(self.info_findings),
            "passed": len(self.findings) == 0,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": round(self.duration_ms, 2),
        }

    def to_dict(self) -> Dict:
        """Full report as dictionary."""
        return {
            "summary": self.summary(),
            "findings": [f.to_dict() for f in self.findings],
        }


class ConfigAuditor:
    """Multi-layer configuration security auditor.

    Checks:
    - Filesystem permissions on sensitive files
    - Environment variable configuration
    - API key exposure
    - Config file security
    - Gateway/endpoint configuration

    Example:
        >>> auditor = ConfigAuditor(config_dir="/path/to/config")
        >>> report = auditor.audit()
        >>> print(report.summary())
    """

    def __init__(
        self,
        config_dir: Optional[str] = None,
        env_prefix: str = "RLM_",
        sensitive_patterns: Optional[List[str]] = None,
    ):
        """Initialize auditor.

        Args:
            config_dir: Directory to audit (defaults to current dir)
            env_prefix: Prefix for environment variables to check
            sensitive_patterns: Patterns for sensitive file names
        """
        self.config_dir = Path(config_dir) if config_dir else Path.cwd()
        self.env_prefix = env_prefix
        self.sensitive_patterns = sensitive_patterns or [
            ".env",
            "secrets",
            "credentials",
            "api_key",
            "private",
            ".pem",
            ".key",
        ]

        self._checks: List[Callable[[], List[AuditFinding]]] = [
            self._check_filesystem_permissions,
            self._check_env_variables,
            self._check_api_key_exposure,
            self._check_config_files,
            self._check_gateway_config,
        ]

    def audit(self) -> AuditReport:
        """Run all security checks.

        Returns:
            AuditReport with all findings
        """
        import time
        start = time.time()

        findings: List[AuditFinding] = []

        for check in self._checks:
            try:
                findings.extend(check())
            except Exception as e:
                logger.warning(f"Audit check failed: {e}")
                findings.append(AuditFinding(
                    category="audit_error",
                    severity=AuditSeverity.WARNING,
                    message=f"Audit check failed: {type(e).__name__}",
                    recommendation="Review audit logs for details",
                    metadata={"error": str(e)},
                ))

        duration_ms = (time.time() - start) * 1000

        return AuditReport(
            findings=findings,
            duration_ms=duration_ms,
        )

    def _check_filesystem_permissions(self) -> List[AuditFinding]:
        """Check permissions on sensitive files."""
        findings = []

        if not self.config_dir.exists():
            return findings

        for pattern in self.sensitive_patterns:
            for path in self.config_dir.rglob(f"*{pattern}*"):
                if not path.is_file():
                    continue

                try:
                    # Check if file is world-readable (Unix)
                    if os.name != 'nt':  # Not Windows
                        mode = path.stat().st_mode
                        if mode & stat.S_IROTH:  # Other-readable
                            findings.append(AuditFinding(
                                category="filesystem",
                                severity=AuditSeverity.CRITICAL,
                                message=f"Sensitive file is world-readable: {path.name}",
                                recommendation=f"Run: chmod 600 {path}",
                                metadata={"path": str(
                                    path), "mode": oct(mode)},
                            ))
                except PermissionError:
                    pass  # Can't check, skip

        return findings

    def _check_env_variables(self) -> List[AuditFinding]:
        """Check environment variable configuration."""
        findings = []

        # Check for sensitive vars that should exist but don't
        recommended_vars = [
            f"{self.env_prefix}SECRET_KEY",
            f"{self.env_prefix}API_KEY",
        ]

        for var in recommended_vars:
            if var in os.environ:
                value = os.environ[var]
                # Check for weak values
                if len(value) < 16:
                    findings.append(AuditFinding(
                        category="environment",
                        severity=AuditSeverity.WARNING,
                        message=f"Environment variable {var} has weak value (< 16 chars)",
                        recommendation=f"Use a stronger secret for {var}",
                    ))
                # Check for placeholder values
                if value.lower() in ["changeme", "secret", "password", "xxx", "test"]:
                    findings.append(AuditFinding(
                        category="environment",
                        severity=AuditSeverity.CRITICAL,
                        message=f"Environment variable {var} has placeholder value",
                        recommendation=f"Set a real secret for {var}",
                    ))

        return findings

    def _check_api_key_exposure(self) -> List[AuditFinding]:
        """Check for API keys in code/config files."""
        findings = []
        dangerous_patterns = [
            "sk-",           # OpenAI
            "ANTHROPIC_",    # Anthropic API in code
            "Bearer ",       # Auth headers
            "api_key=",      # Query params
            "apiKey:",       # Config files
        ]

        config_extensions = {".py", ".json", ".yaml", ".yml", ".toml", ".ini"}

        if not self.config_dir.exists():
            return findings

        for path in self.config_dir.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in config_extensions:
                continue
            if ".git" in str(path) or "__pycache__" in str(path):
                continue

            try:
                content = path.read_text(encoding='utf-8', errors='ignore')
                for pattern in dangerous_patterns:
                    if pattern in content:
                        findings.append(AuditFinding(
                            category="secrets",
                            severity=AuditSeverity.CRITICAL,
                            message=f"Potential API key exposure in {path.name}",
                            recommendation="Move secrets to environment variables",
                            metadata={"path": str(path), "pattern": pattern},
                        ))
                        break  # One finding per file
            except (IOError, OSError):
                pass

        return findings

    def _check_config_files(self) -> List[AuditFinding]:
        """Check for insecure configuration settings."""
        findings = []

        # Check for debug mode in production
        debug_indicators = ["DEBUG=true", "DEBUG=True",
                            "debug: true", '"debug": true']

        for path in self.config_dir.glob("*.env*"):
            if not path.is_file():
                continue
            try:
                content = path.read_text()
                for indicator in debug_indicators:
                    if indicator in content:
                        findings.append(AuditFinding(
                            category="config",
                            severity=AuditSeverity.WARNING,
                            message=f"Debug mode enabled in {path.name}",
                            recommendation="Disable debug mode in production",
                            metadata={"path": str(path)},
                        ))
                        break
            except IOError:
                pass

        return findings

    def _check_gateway_config(self) -> List[AuditFinding]:
        """Check gateway/API endpoint configuration."""
        findings = []

        # Check for localhost-only bindings that might be exposed
        gateway_vars = [
            f"{self.env_prefix}HOST",
            f"{self.env_prefix}BIND_ADDRESS",
        ]

        for var in gateway_vars:
            value = os.environ.get(var, "")
            if value == "0.0.0.0":
                findings.append(AuditFinding(
                    category="gateway",
                    severity=AuditSeverity.WARNING,
                    message=f"{var} binds to all interfaces (0.0.0.0)",
                    recommendation="Consider binding to 127.0.0.1 for local-only access",
                    metadata={"variable": var, "value": value},
                ))

        # Check for HTTP vs HTTPS
        url_vars = [f"{self.env_prefix}API_URL", f"{self.env_prefix}ENDPOINT"]
        for var in url_vars:
            value = os.environ.get(var, "")
            if value.startswith("http://") and "localhost" not in value:
                findings.append(AuditFinding(
                    category="gateway",
                    severity=AuditSeverity.CRITICAL,
                    message=f"{var} uses unencrypted HTTP for non-local endpoint",
                    recommendation="Use HTTPS for remote endpoints",
                    metadata={"variable": var},
                ))

        return findings

    def add_check(self, check: Callable[[], List[AuditFinding]]) -> None:
        """Add custom audit check.

        Args:
            check: Function returning list of findings
        """
        self._checks.append(check)

    def run_single_check(self, category: str) -> List[AuditFinding]:
        """Run a single category of checks.

        Args:
            category: Check category name

        Returns:
            Findings for that category
        """
        check_map = {
            "filesystem": self._check_filesystem_permissions,
            "environment": self._check_env_variables,
            "secrets": self._check_api_key_exposure,
            "config": self._check_config_files,
            "gateway": self._check_gateway_config,
        }

        if category not in check_map:
            raise ValueError(f"Unknown check category: {category}")

        return check_map[category]()


def quick_audit(config_dir: Optional[str] = None) -> AuditReport:
    """Quick audit helper function.

    Args:
        config_dir: Directory to audit

    Returns:
        AuditReport
    """
    return ConfigAuditor(config_dir=config_dir).audit()
