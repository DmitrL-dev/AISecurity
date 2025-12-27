"""
Unit tests for Safety Grammar Enforcer.
"""

import pytest
from safety_grammar_enforcer import (
    SafetyGrammarEnforcer,
    SchemaValidator,
    PatternBlocker,
    FormatEnforcer,
    ViolationType,
)


class TestSchemaValidator:
    """Tests for schema validation."""

    def test_valid_json_passes(self):
        """Valid JSON passes."""
        validator = SchemaValidator()

        output = '{"name": "John", "age": 30}'
        schema = {"type": "object", "required": ["name"]}

        valid, msg = validator.validate(output, schema)

        assert valid is True

    def test_missing_field_fails(self):
        """Missing required field fails."""
        validator = SchemaValidator()

        output = '{"age": 30}'
        schema = {"type": "object", "required": ["name"]}

        valid, msg = validator.validate(output, schema)

        assert valid is False
        assert "name" in msg

    def test_invalid_json_fails(self):
        """Invalid JSON fails."""
        validator = SchemaValidator()

        output = "not valid json"
        schema = {"type": "object"}

        valid, msg = validator.validate(output, schema)

        assert valid is False


class TestPatternBlocker:
    """Tests for pattern blocking."""

    def test_safe_content_passes(self):
        """Safe content passes."""
        blocker = PatternBlocker()

        is_safe, patterns = blocker.check("Hello, how are you?")

        assert is_safe is True

    def test_password_leak_detected(self):
        """Password leak is detected."""
        blocker = PatternBlocker()

        is_safe, patterns = blocker.check("password: secret123")

        assert is_safe is False
        assert "credential_leak" in patterns

    def test_sanitize_removes_dangerous(self):
        """Sanitize removes dangerous patterns."""
        blocker = PatternBlocker()

        result = blocker.sanitize("Run: rm -rf /")

        assert "rm -rf" not in result


class TestFormatEnforcer:
    """Tests for format enforcement."""

    def test_length_ok(self):
        """Normal length passes."""
        enforcer = FormatEnforcer(max_length=100)

        ok, msg = enforcer.check_length("short text")

        assert ok is True

    def test_length_exceeded(self):
        """Exceeded length fails."""
        enforcer = FormatEnforcer(max_length=10)

        ok, msg = enforcer.check_length("this is a very long text")

        assert ok is False

    def test_detect_json(self):
        """JSON format is detected."""
        enforcer = FormatEnforcer()

        fmt = enforcer.detect_format('{"key": "value"}')

        assert fmt == "json"


class TestSafetyGrammarEnforcer:
    """Integration tests."""

    def test_valid_output_passes(self):
        """Valid output passes."""
        enforcer = SafetyGrammarEnforcer()

        result = enforcer.enforce("Hello, world!")

        assert result.is_valid is True
        assert result.is_safe is True

    def test_dangerous_pattern_blocked(self):
        """Dangerous pattern is blocked."""
        enforcer = SafetyGrammarEnforcer()

        result = enforcer.enforce("password: mysecret123")

        assert result.is_safe is False
        assert ViolationType.DANGEROUS_PATTERN in result.violations

    def test_schema_validation(self):
        """Schema validation works."""
        enforcer = SafetyGrammarEnforcer()

        schema = {"type": "object", "required": ["name"]}
        result = enforcer.enforce('{"name": "John"}', schema=schema)

        assert result.is_valid is True

    def test_long_output_truncated(self):
        """Long output is truncated."""
        enforcer = SafetyGrammarEnforcer(max_length=50)

        long_text = "a" * 100
        result = enforcer.enforce(long_text)

        assert ViolationType.LENGTH_EXCEEDED in result.violations
        assert len(result.corrected_output) == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
