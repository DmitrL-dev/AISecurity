"""
SENTINEL Security Engine Constants

Shared constants and patterns for all security engines.
"""

from typing import Dict, FrozenSet, List, Pattern, Set
import re


# ============================================================================
# Version Info
# ============================================================================

ENGINE_VERSION = "1.0.0"
API_VERSION = "v1"


# ============================================================================
# Security Patterns
# ============================================================================

# Injection patterns
INJECTION_PATTERNS: List[str] = [
    r"ignore\s*(?:all\s*)?(?:previous\s*)?instructions?",
    r"disregard\s*(?:all\s*)?(?:your\s*)?(?:previous\s*)?(?:rules?|instructions?)",
    r"forget\s*(?:everything|all|your\s*training)",
    r"override\s*(?:your\s*)?(?:safety|security|rules?)",
    r"bypass\s*(?:security|safety|restrictions?)",
    r"you\s*are\s*now\s*(?:a\s*)?(?:new\s*)?",
    r"new\s*(?:system\s*)?prompt",
    r"act\s*as\s*(?:if\s*you\s*are|a\s*)?",
    r"pretend\s*(?:to\s*be|you\s*are)",
]

# Sensitive data patterns
PII_PATTERNS: List[str] = [
    r"\b\d{3}[-.]?\d{2}[-.]?\d{4}\b",  # SSN
    r"\b\d{16}\b",  # Credit card (simplified)
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
    r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # Phone
]

# Dangerous content patterns
DANGEROUS_PATTERNS: List[str] = [
    r"<script\b[^>]*>",
    r"javascript:",
    r"data:text/html",
    r"onclick\s*=",
    r"onerror\s*=",
    r"eval\s*\(",
    r"exec\s*\(",
]


# ============================================================================
# Homoglyphs
# ============================================================================

CYRILLIC_TO_LATIN: Dict[str, str] = {
    "а": "a",
    "А": "A",
    "с": "c",
    "С": "C",
    "е": "e",
    "Е": "E",
    "о": "o",
    "О": "O",
    "р": "p",
    "Р": "P",
    "х": "x",
    "Х": "X",
    "у": "y",
    "В": "B",
    "К": "K",
    "М": "M",
    "Н": "H",
    "Т": "T",
}

GREEK_TO_LATIN: Dict[str, str] = {
    "Α": "A",
    "α": "a",
    "Β": "B",
    "β": "b",
    "Ε": "E",
    "ε": "e",
    "Η": "H",
    "η": "n",
    "Ι": "I",
    "ι": "i",
    "Κ": "K",
    "κ": "k",
    "Μ": "M",
    "μ": "m",
    "Ν": "N",
    "ν": "v",
    "Ο": "O",
    "ο": "o",
    "Ρ": "P",
    "ρ": "p",
    "Τ": "T",
    "τ": "t",
    "Υ": "Y",
    "υ": "u",
    "Χ": "X",
    "χ": "x",
}


# ============================================================================
# Invisible Characters
# ============================================================================

INVISIBLE_CHARS: FrozenSet[str] = frozenset(
    {
        "\u200b",  # Zero-width space
        "\u200c",  # Zero-width non-joiner
        "\u200d",  # Zero-width joiner
        "\u2060",  # Word joiner
        "\ufeff",  # BOM
        "\u00ad",  # Soft hyphen
        "\u034f",  # Combining grapheme joiner
        "\u061c",  # Arabic letter mark
        "\u115f",  # Hangul choseong filler
        "\u1160",  # Hangul jungseong filler
        "\u17b4",  # Khmer vowel inherent aq
        "\u17b5",  # Khmer vowel inherent aa
        "\u180e",  # Mongolian vowel separator
    }
)


# ============================================================================
# Attack Keywords
# ============================================================================

ATTACK_KEYWORDS: FrozenSet[str] = frozenset(
    {
        "ignore",
        "bypass",
        "override",
        "hack",
        "exploit",
        "inject",
        "jailbreak",
        "escape",
        "sudo",
        "admin",
        "root",
        "system",
    }
)

SUSPICIOUS_KEYWORDS: FrozenSet[str] = frozenset(
    {
        "password",
        "secret",
        "token",
        "api_key",
        "credential",
        "private",
        "confidential",
    }
)


# ============================================================================
# Thresholds
# ============================================================================

DEFAULT_CONFIDENCE_THRESHOLD = 0.7
DEFAULT_RISK_THRESHOLD = 0.5
DEFAULT_MAX_INPUT_LENGTH = 10000
DEFAULT_MAX_TOKENS = 4096
DEFAULT_TIMEOUT_SECONDS = 30


# ============================================================================
# Compiled Patterns (for performance)
# ============================================================================

COMPILED_INJECTION_PATTERNS: List[Pattern] = [
    re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS
]

COMPILED_PII_PATTERNS: List[Pattern] = [
    re.compile(p, re.IGNORECASE) for p in PII_PATTERNS
]

COMPILED_DANGEROUS_PATTERNS: List[Pattern] = [
    re.compile(p, re.IGNORECASE) for p in DANGEROUS_PATTERNS
]
