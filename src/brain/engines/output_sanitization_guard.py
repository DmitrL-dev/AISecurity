"""
Output Sanitization Guard Engine - Egress Security

Sanitizes LLM outputs for safety:
- Code injection prevention
- Sensitive data redaction
- Dangerous instruction removal
- Format validation

Addresses: OWASP ASI-03 (Insecure Output Handling)
Research: output_parsing_security_deep_dive.md
Invention: Output Sanitization Guard (#43)
"""

import re
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from base_engine import Severity, Action  # Base classes

logger = logging.getLogger("OutputSanitizationGuard")


# ============================================================================
# Data Classes
# ============================================================================


class SanitizationType(Enum):
    """Types of sanitization applied."""

    CODE_REMOVED = "code_removed"
    PII_REDACTED = "pii_redacted"
    DANGEROUS_REMOVED = "dangerous_removed"
    FORMAT_FIXED = "format_fixed"
    LINK_SANITIZED = "link_sanitized"


@dataclass
class SanitizationResult:
    """Result from output sanitization."""

    is_safe: bool
    sanitized_output: str
    modifications: List[SanitizationType] = field(default_factory=list)
    redacted_count: int = 0
    risk_score: float = 0.0
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "modifications": [m.value for m in self.modifications],
            "redacted_count": self.redacted_count,
            "risk_score": self.risk_score,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Code Sanitizer
# ============================================================================


class CodeSanitizer:
    """
    Removes dangerous code patterns from output.
    """

    DANGEROUS_CODE = [
        (r"```(?:bash|sh|powershell|cmd).*?```",
         "```\n[code removed for safety]\n```"),
        (r"rm\s+-rf\s+/", "[dangerous command removed]"),
        (r"sudo\s+rm", "[dangerous command removed]"),
        (r":(){ :\|:& };:", "[fork bomb removed]"),
        (r"dd\s+if=/dev/zero", "[dangerous command removed]"),
    ]

    def __init__(self):
        self._patterns = [
            (re.compile(p, re.IGNORECASE | re.DOTALL), r)
            for p, r in self.DANGEROUS_CODE
        ]

    def sanitize(self, text: str) -> Tuple[str, bool]:
        """
        Sanitize dangerous code.

        Returns:
            (sanitized_text, was_modified)
        """
        result = text
        modified = False

        for pattern, replacement in self._patterns:
            if pattern.search(result):
                result = pattern.sub(replacement, result)
                modified = True

        return result, modified


# ============================================================================
# PII Redactor
# ============================================================================


class PIIRedactor:
    """
    Redacts personally identifiable information.
    """

    PII_PATTERNS = [
        (r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b", "[SSN REDACTED]"),
        (r"\b\d{16}\b", "[CARD REDACTED]"),
        (
            r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
            "[EMAIL REDACTED]"),
        (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE REDACTED]"),
    ]

    def __init__(self):
        self._patterns = [(re.compile(p), r) for p, r in self.PII_PATTERNS]

    def redact(self, text: str) -> Tuple[str, int]:
        """
        Redact PII from text.

        Returns:
            (redacted_text, redaction_count)
        """
        result = text
        count = 0

        for pattern, replacement in self._patterns:
            matches = pattern.findall(result)
            count += len(matches)
            result = pattern.sub(replacement, result)

        return result, count


# ============================================================================
# Dangerous Instruction Remover
# ============================================================================


class DangerousInstructionRemover:
    """
    Removes dangerous instructions from output.
    """

    DANGEROUS_PATTERNS = [
        r"(here('s| is) how to|instructions? for|steps? to)\s+.*(hack|attack|exploit|break into)",
        r"(here('s| is) how to|instructions? for)\s+.*(make|build|create)\s+.*(bomb|weapon|explosive)",
        r"(here('s| is) how to|instructions? for)\s+.*(synthesize|manufacture)\s+.*(drug|meth)",
    ]

    def __init__(self):
        self._patterns = [re.compile(p, re.IGNORECASE)
                          for p in self.DANGEROUS_PATTERNS]

    def remove(self, text: str) -> Tuple[str, bool]:
        """
        Remove dangerous instructions.

        Returns:
            (cleaned_text, was_modified)
        """
        result = text
        modified = False

        for pattern in self._patterns:
            if pattern.search(result):
                result = pattern.sub("[content removed for safety]", result)
                modified = True

        return result, modified


# ============================================================================
# Link Sanitizer
# ============================================================================


class LinkSanitizer:
    """
    Sanitizes links and URLs in output.
    """

    SUSPICIOUS_DOMAINS = [
        r"(phishing|malware|evil|hack)\.[a-z]+",
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}",  # IP addresses
        r"bit\.ly|tinyurl\.com|t\.co",  # URL shorteners
    ]

    def __init__(self):
        self._patterns = [re.compile(p, re.IGNORECASE)
                          for p in self.SUSPICIOUS_DOMAINS]

    def sanitize(self, text: str) -> Tuple[str, int]:
        """
        Sanitize suspicious links.

        Returns:
            (sanitized_text, links_removed)
        """
        result = text
        count = 0

        # Find all URLs
        url_pattern = re.compile(r'https?://[^\s<>"{}|\\^`\[\]]+')

        for match in url_pattern.finditer(text):
            url = match.group()
            for pattern in self._patterns:
                if pattern.search(url):
                    result = result.replace(url, "[suspicious link removed]")
                    count += 1
                    break

        return result, count


# ============================================================================
# Main Engine
# ============================================================================


class OutputSanitizationGuard:
    """
    Output Sanitization Guard - Egress Security

    Comprehensive output sanitization:
    - Code sanitization
    - PII redaction
    - Dangerous content removal
    - Link sanitization

    Invention #43 from research.
    Addresses OWASP ASI-03.
    """

    def __init__(self):
        self.code_sanitizer = CodeSanitizer()
        self.pii_redactor = PIIRedactor()
        self.danger_remover = DangerousInstructionRemover()
        self.link_sanitizer = LinkSanitizer()

        logger.info("OutputSanitizationGuard initialized")

    def sanitize(self, output: str) -> SanitizationResult:
        """
        Sanitize LLM output.

        Args:
            output: Raw LLM output

        Returns:
            SanitizationResult
        """
        start = time.time()

        result = output
        modifications = []
        total_redactions = 0
        risk = 0.0

        # 1. Code sanitization
        result, code_modified = self.code_sanitizer.sanitize(result)
        if code_modified:
            modifications.append(SanitizationType.CODE_REMOVED)
            risk = max(risk, 0.7)

        # 2. Dangerous instruction removal
        result, danger_modified = self.danger_remover.remove(result)
        if danger_modified:
            modifications.append(SanitizationType.DANGEROUS_REMOVED)
            risk = max(risk, 0.9)

        # 3. PII redaction
        result, pii_count = self.pii_redactor.redact(result)
        if pii_count > 0:
            modifications.append(SanitizationType.PII_REDACTED)
            total_redactions += pii_count
            risk = max(risk, 0.5)

        # 4. Link sanitization
        result, link_count = self.link_sanitizer.sanitize(result)
        if link_count > 0:
            modifications.append(SanitizationType.LINK_SANITIZED)
            total_redactions += link_count
            risk = max(risk, 0.4)

        is_safe = risk < 0.9

        if modifications:
            logger.info(
                f"Output sanitized: {[m.value for m in modifications]}")

        return SanitizationResult(
            is_safe=is_safe,
            sanitized_output=result,
            modifications=modifications,
            redacted_count=total_redactions,
            risk_score=risk,
            explanation=(
                f"Applied: {len(modifications)} sanitizations"
                if modifications
                else "No sanitization needed"
            ),
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_guard: Optional[OutputSanitizationGuard] = None


def get_guard() -> OutputSanitizationGuard:
    global _default_guard
    if _default_guard is None:
        _default_guard = OutputSanitizationGuard()
    return _default_guard
