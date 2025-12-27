"""
Unit tests for Output Sanitization Guard.
"""

import pytest
from output_sanitization_guard import (
    OutputSanitizationGuard,
    CodeSanitizer,
    PIIRedactor,
    DangerousInstructionRemover,
    LinkSanitizer,
    SanitizationType,
)


class TestCodeSanitizer:
    """Tests for code sanitization."""

    def test_safe_code_passes(self):
        """Safe code passes through."""
        sanitizer = CodeSanitizer()

        result, modified = sanitizer.sanitize("```python\nprint('hello')\n```")

        assert modified is False
        assert "print" in result

    def test_dangerous_command_removed(self):
        """Dangerous command is removed."""
        sanitizer = CodeSanitizer()

        result, modified = sanitizer.sanitize("Run: rm -rf /")

        assert modified is True
        assert "rm -rf" not in result


class TestPIIRedactor:
    """Tests for PII redaction."""

    def test_ssn_redacted(self):
        """SSN is redacted."""
        redactor = PIIRedactor()

        result, count = redactor.redact("SSN: 123-45-6789")

        assert count == 1
        assert "123-45-6789" not in result
        assert "[SSN REDACTED]" in result

    def test_email_redacted(self):
        """Email is redacted."""
        redactor = PIIRedactor()

        result, count = redactor.redact("Contact: test@example.com")

        assert count == 1
        assert "test@example.com" not in result

    def test_no_pii_unchanged(self):
        """Text without PII is unchanged."""
        redactor = PIIRedactor()

        result, count = redactor.redact("Hello world")

        assert count == 0
        assert result == "Hello world"


class TestDangerousInstructionRemover:
    """Tests for dangerous instruction removal."""

    def test_safe_instruction_passes(self):
        """Safe instruction passes."""
        remover = DangerousInstructionRemover()

        result, modified = remover.remove("Here's how to make a cake")

        assert modified is False

    def test_hacking_instruction_removed(self):
        """Hacking instruction is removed."""
        remover = DangerousInstructionRemover()

        result, modified = remover.remove("Here's how to hack into a system")

        assert modified is True
        assert "hack" not in result.lower()


class TestLinkSanitizer:
    """Tests for link sanitization."""

    def test_safe_link_passes(self):
        """Safe link passes."""
        sanitizer = LinkSanitizer()

        result, count = sanitizer.sanitize("Visit https://example.com")

        assert count == 0
        assert "example.com" in result

    def test_ip_link_removed(self):
        """IP address link is removed."""
        sanitizer = LinkSanitizer()

        result, count = sanitizer.sanitize("Go to http://192.168.1.1/admin")

        assert count == 1
        assert "192.168.1.1" not in result


class TestOutputSanitizationGuard:
    """Integration tests."""

    def test_clean_output_unchanged(self):
        """Clean output is unchanged."""
        guard = OutputSanitizationGuard()

        result = guard.sanitize("Hello, how can I help you?")

        assert result.is_safe is True
        assert len(result.modifications) == 0
        assert result.sanitized_output == "Hello, how can I help you?"

    def test_pii_is_redacted(self):
        """PII is redacted from output."""
        guard = OutputSanitizationGuard()

        result = guard.sanitize("Your SSN is 123-45-6789")

        assert SanitizationType.PII_REDACTED in result.modifications
        assert "123-45-6789" not in result.sanitized_output

    def test_dangerous_code_removed(self):
        """Dangerous code is removed."""
        guard = OutputSanitizationGuard()

        result = guard.sanitize("Execute: rm -rf /")

        assert SanitizationType.CODE_REMOVED in result.modifications

    def test_multiple_sanitizations(self):
        """Multiple sanitizations are applied."""
        guard = OutputSanitizationGuard()

        text = "SSN: 123-45-6789. Run: rm -rf /"
        result = guard.sanitize(text)

        assert len(result.modifications) >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
