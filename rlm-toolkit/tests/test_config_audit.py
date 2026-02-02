"""
Tests for Configuration Security Audit.
"""

import os
import tempfile
from pathlib import Path

import pytest

from rlm_toolkit.security.config_audit import (
    ConfigAuditor,
    AuditFinding,
    AuditReport,
    AuditSeverity,
    quick_audit,
)


class TestAuditFinding:
    """Tests for AuditFinding dataclass."""

    def test_create_finding(self):
        """Test basic finding creation."""
        finding = AuditFinding(
            category="test",
            severity=AuditSeverity.CRITICAL,
            message="Test message",
            recommendation="Fix it",
        )

        assert finding.category == "test"
        assert finding.severity == AuditSeverity.CRITICAL

    def test_to_dict(self):
        """Test serialization."""
        finding = AuditFinding(
            category="test",
            severity=AuditSeverity.WARNING,
            message="Warning",
            recommendation="Review",
            metadata={"key": "value"},
        )

        data = finding.to_dict()
        assert data["severity"] == "warning"
        assert data["metadata"] == {"key": "value"}


class TestAuditReport:
    """Tests for AuditReport."""

    def test_empty_report(self):
        """Test empty report."""
        report = AuditReport()

        assert len(report.findings) == 0
        assert not report.has_critical
        assert not report.has_warnings

    def test_report_with_findings(self):
        """Test report classification."""
        report = AuditReport(findings=[
            AuditFinding("a", AuditSeverity.CRITICAL, "c", "r"),
            AuditFinding("b", AuditSeverity.WARNING, "w", "r"),
            AuditFinding("c", AuditSeverity.INFO, "i", "r"),
        ])

        assert report.has_critical
        assert report.has_warnings
        assert len(report.critical_findings) == 1
        assert len(report.warning_findings) == 1
        assert len(report.info_findings) == 1

    def test_summary(self):
        """Test report summary."""
        report = AuditReport(findings=[
            AuditFinding("a", AuditSeverity.CRITICAL, "c", "r"),
        ])

        summary = report.summary()

        assert summary["critical"] == 1
        assert summary["passed"] == False
        assert "timestamp" in summary

    def test_to_dict(self):
        """Test full serialization."""
        report = AuditReport()
        data = report.to_dict()

        assert "summary" in data
        assert "findings" in data


class TestConfigAuditor:
    """Tests for ConfigAuditor."""

    def test_audit_empty_dir(self):
        """Test auditing empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            auditor = ConfigAuditor(config_dir=tmpdir)
            report = auditor.audit()

            assert isinstance(report, AuditReport)
            assert report.duration_ms > 0

    def test_audit_nonexistent_dir(self):
        """Test auditing nonexistent directory."""
        auditor = ConfigAuditor(config_dir="/nonexistent/path/12345")
        report = auditor.audit()

        # Should not crash
        assert isinstance(report, AuditReport)

    def test_detect_api_key_in_file(self):
        """Test detection of API keys in config files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config file with API key
            config_path = Path(tmpdir) / "config.py"
            config_path.write_text('API_KEY = "sk-abcdef123456"')

            auditor = ConfigAuditor(config_dir=tmpdir)
            report = auditor.audit()

            # Should find the API key exposure
            secrets_findings = [
                f for f in report.findings
                if f.category == "secrets"
            ]
            assert len(secrets_findings) >= 1

    def test_detect_debug_mode(self):
        """Test detection of debug mode."""
        with tempfile.TemporaryDirectory() as tmpdir:
            env_path = Path(tmpdir) / ".env"
            env_path.write_text("DEBUG=true\n")

            auditor = ConfigAuditor(config_dir=tmpdir)
            report = auditor.audit()

            config_findings = [
                f for f in report.findings
                if f.category == "config"
            ]
            assert len(config_findings) >= 1

    def test_env_variable_weak_value(self):
        """Test detection of weak env variable values."""
        # Set weak value
        os.environ["RLM_SECRET_KEY"] = "weak"

        try:
            auditor = ConfigAuditor()
            report = auditor.audit()

            env_findings = [
                f for f in report.findings
                if f.category == "environment"
            ]
            # Should detect weak value
            assert any("weak value" in f.message for f in env_findings)
        finally:
            del os.environ["RLM_SECRET_KEY"]

    def test_env_variable_placeholder(self):
        """Test detection of placeholder values."""
        os.environ["RLM_API_KEY"] = "changeme"

        try:
            auditor = ConfigAuditor()
            report = auditor.audit()

            critical = [
                f for f in report.findings
                if f.category == "environment" and f.severity == AuditSeverity.CRITICAL
            ]
            assert len(critical) >= 1
        finally:
            del os.environ["RLM_API_KEY"]

    def test_gateway_http_warning(self):
        """Test HTTP warning for remote endpoints."""
        os.environ["RLM_API_URL"] = "http://api.example.com"

        try:
            auditor = ConfigAuditor()
            report = auditor.audit()

            gateway_findings = [
                f for f in report.findings
                if f.category == "gateway"
            ]
            assert any("HTTP" in f.message for f in gateway_findings)
        finally:
            del os.environ["RLM_API_URL"]

    def test_add_custom_check(self):
        """Test adding custom audit check."""
        auditor = ConfigAuditor()

        def custom_check():
            return [AuditFinding(
                category="custom",
                severity=AuditSeverity.INFO,
                message="Custom check ran",
                recommendation="None",
            )]

        auditor.add_check(custom_check)
        report = auditor.audit()

        custom = [f for f in report.findings if f.category == "custom"]
        assert len(custom) == 1

    def test_run_single_check(self):
        """Test running single category."""
        auditor = ConfigAuditor()

        # Should not raise
        findings = auditor.run_single_check("config")
        assert isinstance(findings, list)

        # Unknown category should raise
        with pytest.raises(ValueError):
            auditor.run_single_check("unknown_category")

    def test_custom_env_prefix(self):
        """Test custom environment prefix."""
        os.environ["MYAPP_SECRET_KEY"] = "test"

        try:
            auditor = ConfigAuditor(env_prefix="MYAPP_")
            # Should use custom prefix
            assert auditor.env_prefix == "MYAPP_"
        finally:
            del os.environ["MYAPP_SECRET_KEY"]


class TestQuickAudit:
    """Tests for quick_audit helper."""

    def test_quick_audit(self):
        """Test quick audit function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            report = quick_audit(tmpdir)
            assert isinstance(report, AuditReport)

    def test_quick_audit_default_dir(self):
        """Test quick audit with default directory."""
        report = quick_audit()
        assert isinstance(report, AuditReport)
