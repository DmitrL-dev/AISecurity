"""
Safety Grammar Enforcer Engine - Constrained Decoding

Enforces structural safety through grammar constraints:
- Output format validation
- Schema enforcement
- Safe pattern matching
- Dangerous pattern blocking

Addresses: OWASP ASI-03 (Insecure Output Handling)
Research: constrained_decoding_deep_dive.md
Invention: Safety Grammar Enforcer (#30)
"""

import re
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Pattern

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("SafetyGrammarEnforcer")


# ============================================================================
# Data Classes
# ============================================================================


class ViolationType(Enum):
    """Types of grammar violations."""

    SCHEMA_MISMATCH = "schema_mismatch"
    DANGEROUS_PATTERN = "dangerous_pattern"
    FORMAT_ERROR = "format_error"
    LENGTH_EXCEEDED = "length_exceeded"
    BLOCKED_CONTENT = "blocked_content"


@dataclass
class GrammarResult:
    """Result from grammar enforcement."""

    is_valid: bool
    is_safe: bool
    violations: List[ViolationType] = field(default_factory=list)
    corrected_output: str = ""
    risk_score: float = 0.0
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "is_safe": self.is_safe,
            "violations": [v.value for v in self.violations],
            "risk_score": self.risk_score,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Schema Validator
# ============================================================================


class SchemaValidator:
    """
    Validates output against JSON schema.
    """

    def validate(
        self,
        output: str,
        schema: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """
        Validate output against schema.

        Returns:
            (is_valid, error_message)
        """
        try:
            data = json.loads(output)
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"

        # Simple schema validation
        if "type" in schema:
            expected_type = schema["type"]
            if expected_type == "object" and not isinstance(data, dict):
                return False, "Expected object"
            if expected_type == "array" and not isinstance(data, list):
                return False, "Expected array"
            if expected_type == "string" and not isinstance(data, str):
                return False, "Expected string"

        if "required" in schema and isinstance(data, dict):
            for field in schema["required"]:
                if field not in data:
                    return False, f"Missing required field: {field}"

        if "properties" in schema and isinstance(data, dict):
            for key, prop_schema in schema["properties"].items():
                if key in data:
                    if "type" in prop_schema:
                        if prop_schema["type"] == "string":
                            if not isinstance(data[key], str):
                                return False, f"Field {key} should be string"

        return True, ""


# ============================================================================
# Pattern Blocker
# ============================================================================


class PatternBlocker:
    """
    Blocks dangerous patterns in output.
    """

    DANGEROUS_PATTERNS = [
        (r"(password|passwd|secret):\s*\S+", "credential_leak"),
        (r"(api[_-]?key|apikey):\s*\S+", "api_key_leak"),
        (r"--.*?(drop|delete|truncate)\s+table", "sql_injection"),
        (r"<script[^>]*>.*?</script>", "xss"),
        (r"rm\s+-rf\s+/", "dangerous_command"),
    ]

    def __init__(self):
        self._patterns: List[Tuple[Pattern, str]] = [
            (re.compile(p, re.IGNORECASE | re.DOTALL), name)
            for p, name in self.DANGEROUS_PATTERNS
        ]

    def check(self, text: str) -> Tuple[bool, List[str]]:
        """
        Check for dangerous patterns.

        Returns:
            (is_safe, detected_patterns)
        """
        detected = []

        for pattern, name in self._patterns:
            if pattern.search(text):
                detected.append(name)

        return len(detected) == 0, detected

    def sanitize(self, text: str) -> str:
        """Remove dangerous patterns."""
        result = text
        for pattern, name in self._patterns:
            result = pattern.sub(f"[{name}_removed]", result)
        return result


# ============================================================================
# Format Enforcer
# ============================================================================


class FormatEnforcer:
    """
    Enforces output format constraints.
    """

    def __init__(
        self,
        max_length: int = 10000,
        allowed_formats: Optional[List[str]] = None,
    ):
        self.max_length = max_length
        self.allowed_formats = allowed_formats or ["text", "json", "markdown"]

    def check_length(self, text: str) -> Tuple[bool, str]:
        """Check length constraint."""
        if len(text) > self.max_length:
            return False, f"Output too long: {len(text)} > {self.max_length}"
        return True, ""

    def detect_format(self, text: str) -> str:
        """Detect output format."""
        text = text.strip()

        if text.startswith("{") or text.startswith("["):
            try:
                json.loads(text)
                return "json"
            except json.JSONDecodeError:
                pass

        if text.startswith("#") or "```" in text:
            return "markdown"

        return "text"

    def validate_format(self, text: str, expected: str) -> Tuple[bool, str]:
        """Validate format matches expected."""
        detected = self.detect_format(text)

        if expected and detected != expected:
            return False, f"Expected {expected}, got {detected}"

        if detected not in self.allowed_formats:
            return False, f"Format {detected} not allowed"

        return True, ""


# ============================================================================
# Main Engine
# ============================================================================


class SafetyGrammarEnforcer:
    """
    Safety Grammar Enforcer - Constrained Decoding

    Comprehensive output safety:
    - Schema validation
    - Pattern blocking
    - Format enforcement

    Invention #30 from research.
    Addresses OWASP ASI-03.
    """

    def __init__(
        self,
        max_length: int = 10000,
    ):
        self.schema_validator = SchemaValidator()
        self.pattern_blocker = PatternBlocker()
        self.format_enforcer = FormatEnforcer(max_length=max_length)

        logger.info("SafetyGrammarEnforcer initialized")

    def enforce(
        self,
        output: str,
        schema: Optional[Dict] = None,
        expected_format: Optional[str] = None,
    ) -> GrammarResult:
        """
        Enforce grammar constraints on output.

        Args:
            output: LLM output to validate
            schema: Optional JSON schema
            expected_format: Optional expected format

        Returns:
            GrammarResult
        """
        start = time.time()

        violations = []
        is_valid = True
        corrected = output
        max_risk = 0.0
        explanations = []

        # Check length
        len_ok, len_msg = self.format_enforcer.check_length(output)
        if not len_ok:
            violations.append(ViolationType.LENGTH_EXCEEDED)
            is_valid = False
            max_risk = max(max_risk, 0.5)
            explanations.append(len_msg)
            corrected = output[: self.format_enforcer.max_length]

        # Check format
        if expected_format:
            fmt_ok, fmt_msg = self.format_enforcer.validate_format(
                output, expected_format
            )
            if not fmt_ok:
                violations.append(ViolationType.FORMAT_ERROR)
                is_valid = False
                max_risk = max(max_risk, 0.4)
                explanations.append(fmt_msg)

        # Check schema
        if schema:
            schema_ok, schema_msg = self.schema_validator.validate(
                output, schema)
            if not schema_ok:
                violations.append(ViolationType.SCHEMA_MISMATCH)
                is_valid = False
                max_risk = max(max_risk, 0.6)
                explanations.append(schema_msg)

        # Check dangerous patterns
        pattern_ok, patterns = self.pattern_blocker.check(output)
        if not pattern_ok:
            violations.append(ViolationType.DANGEROUS_PATTERN)
            max_risk = max(max_risk, 0.9)
            explanations.append(f"Dangerous: {patterns}")
            corrected = self.pattern_blocker.sanitize(corrected)

        is_safe = ViolationType.DANGEROUS_PATTERN not in violations

        if violations:
            logger.warning(
                f"Grammar violations: {[v.value for v in violations]}")

        return GrammarResult(
            is_valid=is_valid,
            is_safe=is_safe,
            violations=violations,
            corrected_output=corrected,
            risk_score=max_risk,
            explanation="; ".join(
                explanations) if explanations else "Output valid",
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_enforcer: Optional[SafetyGrammarEnforcer] = None


def get_enforcer() -> SafetyGrammarEnforcer:
    global _default_enforcer
    if _default_enforcer is None:
        _default_enforcer = SafetyGrammarEnforcer()
    return _default_enforcer
