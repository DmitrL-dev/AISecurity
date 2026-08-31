"""
SENTINEL Shield v2.0 — PII Redaction Engine

Detects and replaces PII with typed labels:
  - [REDACTED_SSN], [REDACTED_SNILS], [REDACTED_PASSPORT]
  - [REDACTED_PHONE], [REDACTED_EMAIL], [REDACTED_CARD]
  - [REDACTED_INN], [REDACTED_IBAN], [REDACTED_MIR]
  - [REDACTED_JWT], [REDACTED_API_KEY], [REDACTED_TOKEN]

Supports both detection-only (via analyze) and
text replacement (via redact) modes.
"""

import re
import logging
from dataclasses import dataclass, field

from .base import BaseEngine, EngineResult, ThreatMatch

logger = logging.getLogger("shield.engines.redaction")


@dataclass
class RedactionRule:
    """Single PII redaction rule."""

    name: str  # e.g., "snils", "passport"
    pattern: re.Pattern
    label: str  # e.g., "[REDACTED_SNILS]"
    severity: float = 0.8
    description: str = ""


@dataclass
class RedactionResult:
    """Result of a redaction operation."""

    original_length: int
    redacted_text: str
    redactions: list[dict] = field(default_factory=list)
    total_redactions: int = 0


# PII pattern definitions with labels
_PII_RULES: list[tuple[str, str, str, float, str]] = [
    # (name, regex, label, severity, description)
    # === Russia (ФЗ-152) ===
    (
        "snils",
        r"\b\d{3}-\d{3}-\d{3}\s?\d{2}\b",
        "[REDACTED_SNILS]",
        0.92,
        "СНИЛС (XXX-XXX-XXX XX)",
    ),
    (
        "passport_ru",
        r"\b\d{4}[\s.-]\d{6}\b",
        "[REDACTED_PASSPORT]",
        0.80,
        "Паспорт РФ (серия+номер)",
    ),
    (
        "phone_ru",
        r"(?:\+7|8)[\s-]?\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2}",
        "[REDACTED_PHONE_RU]",
        0.85,
        "Телефон РФ",
    ),
    (
        "mir_card",
        r"\b220[0-4]\s?\d{4}\s?\d{4}\s?\d{4}\b",
        "[REDACTED_MIR]",
        0.92,
        "Карта МИР",
    ),
    (
        "inn_legal",
        r"\b\d{10}\b",
        "[REDACTED_INN]",
        0.50,
        "ИНН юрлица (10 цифр)",
    ),
    (
        "inn_person",
        r"\b\d{12}\b",
        "[REDACTED_INN]",
        0.50,
        "ИНН физлица (12 цифр)",
    ),
    # === USA / International ===
    (
        "ssn",
        r"\b\d{3}[-.\s]?\d{2}[-.\s]?\d{4}\b",
        "[REDACTED_SSN]",
        0.95,
        "US Social Security Number",
    ),
    (
        "credit_card",
        r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        "[REDACTED_CARD]",
        0.92,
        "Credit card number",
    ),
    (
        "email",
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "[REDACTED_EMAIL]",
        0.85,
        "Email address",
    ),
    (
        "phone_us",
        r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "[REDACTED_PHONE]",
        0.80,
        "US phone number",
    ),
    (
        "iban",
        (r"\b[A-Z]{2}\d{2}\s?\d{4}\s?\d{4}" r"\s?\d{4}\s?\d{4}\s?\d{0,2}\b"),
        "[REDACTED_IBAN]",
        0.85,
        "IBAN",
    ),
    # === Tokens / API Keys ===
    (
        "jwt",
        r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}",
        "[REDACTED_JWT]",
        0.85,
        "JWT token",
    ),
    (
        "github_token",
        r"(?:ghp|gho|ghs|ghr)_[A-Za-z0-9]{36,}",
        "[REDACTED_GITHUB_TOKEN]",
        0.92,
        "GitHub token",
    ),
    (
        "gitlab_token",
        r"glpat-[A-Za-z0-9\-]{20,}",
        "[REDACTED_GITLAB_TOKEN]",
        0.92,
        "GitLab personal access token",
    ),
    (
        "openai_key",
        r"sk-[A-Za-z0-9]{20,}",
        "[REDACTED_API_KEY]",
        0.90,
        "OpenAI API key",
    ),
    (
        "aws_key",
        r"AKIA[0-9A-Z]{16}",
        "[REDACTED_AWS_KEY]",
        0.95,
        "AWS Access Key ID",
    ),
    (
        "slack_token",
        r"xox[bpas]-[A-Za-z0-9\-]+",
        "[REDACTED_SLACK_TOKEN]",
        0.90,
        "Slack token",
    ),
]


def _build_rules() -> list[RedactionRule]:
    """Compile all PII rules."""
    rules = []
    for name, pattern, label, sev, desc in _PII_RULES:
        try:
            compiled = re.compile(pattern, re.IGNORECASE)
            rules.append(
                RedactionRule(
                    name=name,
                    pattern=compiled,
                    label=label,
                    severity=sev,
                    description=desc,
                )
            )
        except re.error as e:
            logger.warning(f"Bad PII pattern '{name}': {e}")
    return rules


class RedactionEngine(BaseEngine):
    """
    PII detection and redaction engine.

    Two modes:
    - analyze(text): detect PII, return risk score
    - redact(text): replace PII with [REDACTED_TYPE] labels
    """

    def __init__(self, weight: float = 0.9):
        super().__init__(name="redaction", weight=weight)
        self.rules = _build_rules()
        self._total_redactions = 0

    def analyze(self, text: str) -> EngineResult:
        """Detect PII without redacting."""
        threats: list[ThreatMatch] = []
        max_risk = 0.0

        for rule in self.rules:
            matches = rule.pattern.findall(text)
            if matches:
                # Use first match as snippet
                m = rule.pattern.search(text)
                snippet = m.group(0)[:60] if m else ""

                threats.append(
                    ThreatMatch(
                        threat_type=f"pii_{rule.name}",
                        risk_score=rule.severity,
                        engine=self.name,
                        description=rule.description,
                        matched_text=snippet,
                        category="pii",
                        metadata={
                            "label": rule.label,
                            "count": len(matches),
                        },
                    )
                )
                max_risk = max(max_risk, rule.severity)

        return EngineResult(
            engine_name=self.name,
            risk_score=max_risk,
            threats=threats,
        )

    def redact(self, text: str) -> RedactionResult:
        """
        Replace all PII matches with typed labels.

        Returns RedactionResult with redacted text and
        details of each replacement made.
        """
        redacted = text
        redactions: list[dict] = []

        # Apply rules in priority order (highest severity first)
        # to avoid overlapping replacements
        sorted_rules = sorted(self.rules, key=lambda r: r.severity, reverse=True)

        for rule in sorted_rules:
            new_text, count = rule.pattern.subn(rule.label, redacted)
            if count > 0:
                redactions.append(
                    {
                        "type": rule.name,
                        "label": rule.label,
                        "count": count,
                        "description": rule.description,
                    }
                )
                self._total_redactions += count
                redacted = new_text

        return RedactionResult(
            original_length=len(text),
            redacted_text=redacted,
            redactions=redactions,
            total_redactions=sum(r["count"] for r in redactions),
        )

    def stats(self) -> dict:
        base = super().stats()
        base["total_redactions"] = self._total_redactions
        base["rules_count"] = len(self.rules)
        return base
