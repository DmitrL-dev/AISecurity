"""
SENTINEL Community Edition - Detection Engines

Defense engines for protecting LLM applications.
"""

from .canary_tokens import (
    CanaryTokenEngine,
    CanaryToken,
    CanaryResult,
    CanaryExtraction,
    mark_text,
    check_for_leak,
)

from .self_protection import (
    SelfProtectionEngine,
    ScanResult,
    ScanFinding,
    verify_on_startup,
)

__all__ = [
    # Canary Tokens
    "CanaryTokenEngine",
    "CanaryToken",
    "CanaryResult",
    "CanaryExtraction",
    "mark_text",
    "check_for_leak",
    # Self Protection
    "SelfProtectionEngine",
    "ScanResult",
    "ScanFinding",
    "verify_on_startup",
]
