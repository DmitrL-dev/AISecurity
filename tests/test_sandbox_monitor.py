"""
Tests for SandboxMonitor engine.

REQ: REQ-SM-001 through REQ-SM-006
OWASP: ASI05 - Unexpected Code Execution
"""

import pytest
from src.brain.engines.synced.sandbox_monitor import (
    SandboxMonitor,
    SandboxEscapeSeverity,
    analyze,
)


class TestSandboxMonitor:
    """Test suite for sandbox escape detection."""

    @pytest.fixture
    def monitor(self):
        return SandboxMonitor()

    # REQ-SM-001: os/subprocess detection
    def test_os_system_detection(self, monitor):
        """Detect os.system() calls."""
        code = "import os\nos.system('whoami')"
        result = monitor.analyze(code)
        assert result.detected == True
        assert result.severity == "critical"
        assert 'os_execution' in result.categories_detected

    def test_subprocess_detection(self, monitor):
        """Detect subprocess calls."""
        code = "import subprocess\nsubprocess.Popen(['ls', '-la'])"
        result = monitor.analyze(code)
        assert result.detected == True
        assert result.severity == "critical"
        assert 'subprocess_execution' in result.categories_detected

    def test_os_popen_detection(self, monitor):
        """Detect os.popen() calls."""
        code = "os.popen('cat /etc/passwd').read()"
        result = monitor.analyze(code)
        assert result.detected == True
        assert 'os_execution' in result.categories_detected

    # REQ-SM-002: eval/exec detection
    def test_eval_detection(self, monitor):
        """Detect eval() calls."""
        code = "result = eval(user_input)"
        result = monitor.analyze(code)
        assert result.detected == True
        assert 'dynamic_execution' in result.categories_detected

    def test_exec_detection(self, monitor):
        """Detect exec() calls."""
        code = "exec(malicious_code)"
        result = monitor.analyze(code)
        assert result.detected == True
        assert 'dynamic_execution' in result.categories_detected

    def test_import_detection(self, monitor):
        """Detect __import__() calls."""
        code = "__import__('os').system('rm -rf /')"
        result = monitor.analyze(code)
        assert result.detected == True
        assert 'dynamic_execution' in result.categories_detected

    # REQ-SM-003: builtins manipulation detection
    def test_builtins_access(self, monitor):
        """Detect __builtins__ access."""
        code = "__builtins__['open']('/etc/passwd')"
        result = monitor.analyze(code)
        assert result.detected == True
        assert 'builtins_manipulation' in result.categories_detected

    def test_subclasses_enumeration(self, monitor):
        """Detect __subclasses__() enumeration."""
        code = "().__class__.__bases__[0].__subclasses__()"
        result = monitor.analyze(code)
        assert result.detected == True
        assert 'builtins_manipulation' in result.categories_detected

    def test_globals_access(self, monitor):
        """Detect __globals__ access."""
        code = "func.__globals__['os'].system('id')"
        result = monitor.analyze(code)
        assert result.detected == True
        assert 'builtins_manipulation' in result.categories_detected

    # REQ-SM-004: sensitive file access detection
    def test_passwd_access(self, monitor):
        """Detect /etc/passwd access."""
        code = "f = open('/etc/passwd', 'r')"
        result = monitor.analyze(code)
        assert result.detected == True
        assert 'sensitive_file_access' in result.categories_detected

    def test_ssh_access(self, monitor):
        """Detect .ssh directory access."""
        code = "key = open('.ssh/id_rsa', 'r').read()"
        result = monitor.analyze(code)
        assert result.detected == True
        assert 'sensitive_file_access' in result.categories_detected

    # REQ-SM-005: obfuscation detection
    def test_base64_obfuscation(self, monitor):
        """Detect base64 encoded commands."""
        code = "exec(base64.b64decode('aW1wb3J0IG9z'))"
        result = monitor.analyze(code)
        assert result.detected == True
        assert 'code_obfuscation' in result.categories_detected

    def test_hex_obfuscation(self, monitor):
        """Detect hex encoded commands."""
        code = "exec(bytes.fromhex('696d706f7274206f73'))"
        result = monitor.analyze(code)
        assert result.detected == True
        assert 'code_obfuscation' in result.categories_detected

    # REQ-SM-006: severity levels
    def test_critical_severity(self, monitor):
        """Critical severity for direct execution."""
        code = "os.system('whoami')"
        result = monitor.analyze(code)
        assert result.severity == "critical"
        assert result.risk_score >= 0.9

    def test_high_severity(self, monitor):
        """High severity for builtins access."""
        code = "x = __builtins__"
        result = monitor.analyze(code)
        assert result.severity == "high"
        assert result.risk_score >= 0.7

    def test_safe_code(self, monitor):
        """Safe code should not trigger."""
        code = "print('hello world')\nx = 1 + 2"
        result = monitor.analyze(code)
        assert result.detected == False
        assert result.severity == "safe"
        assert result.risk_score == 0.0

    # ctypes escape detection
    def test_ctypes_detection(self, monitor):
        """Detect ctypes library usage."""
        code = "import ctypes\nlib = ctypes.CDLL('libc.so.6')"
        result = monitor.analyze(code)
        assert result.detected == True
        assert 'ctypes_escape' in result.categories_detected

    # Multiple categories
    def test_multiple_categories(self, monitor):
        """Detect multiple escape techniques."""
        code = """
import os
import base64
os.system('whoami')
exec(base64.b64decode('cHJpbnQoKQ=='))
().__class__.__bases__[0].__subclasses__()
        """
        result = monitor.analyze(code)
        assert result.detected == True
        assert len(result.categories_detected) >= 3


class TestSandboxMonitorAPI:
    """Test module-level API."""

    def test_analyze_function(self):
        """Test module-level analyze function."""
        result = analyze("os.system('test')")
        assert result.detected == True

    def test_recommendations(self):
        """Test recommendations generation."""
        monitor = SandboxMonitor()
        result = monitor.analyze("subprocess.call(['ls'])")
        recs = monitor.get_recommendations(result)
        assert len(recs) > 0
        assert any('subprocess' in r.lower() for r in recs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
