"""
System Prompt Shield Engine - Extraction Prevention

Protects system prompts from extraction attacks:
- Extraction attempt detection
- Canary token injection
- Obfuscation detection
- Leak monitoring

Addresses: OWASP LLM07 (System Prompt Leakage)
Research: system_prompt_protection_deep_dive.md
Invention: System Prompt Shield (#44)
"""

import re
import hashlib
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple
import secrets

from base_engine import Severity, Action  # Base classes

logger = logging.getLogger("SystemPromptShield")


# ============================================================================
# Data Classes
# ============================================================================


class ExtractionType(Enum):
    """Types of extraction attempts."""

    DIRECT_REQUEST = "direct_request"
    REPEAT_INSTRUCTION = "repeat_instruction"
    ROLEPLAY_EXTRACTION = "roleplay_extraction"
    ENCODING_TRICK = "encoding_trick"
    COMPLETION_ATTACK = "completion_attack"


@dataclass
class ShieldResult:
    """Result from System Prompt Shield."""

    is_safe: bool
    risk_score: float
    extraction_detected: bool
    extraction_type: Optional[ExtractionType] = None
    canary_triggered: bool = False
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "risk_score": self.risk_score,
            "extraction_detected": self.extraction_detected,
            "extraction_type": (
                self.extraction_type.value if self.extraction_type else None
            ),
            "canary_triggered": self.canary_triggered,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Extraction Detector
# ============================================================================


class ExtractionDetector:
    """
    Detects system prompt extraction attempts.

    Multiple pattern categories for comprehensive detection.
    """

    EXTRACTION_PATTERNS = {
        ExtractionType.DIRECT_REQUEST: [
            r"(show|tell|reveal|display|print|output)\s+(me\s+)?(your|the)\s+(system\s+)?(prompt|instructions?)",
            r"what\s+(is|are)\s+your\s+(initial\s+)?(instructions?|prompt|rules)",
            r"(repeat|recite|say)\s+(your\s+)?(system\s+)?prompt",
            r"(copy|paste)\s+(your\s+)?instructions",
        ],
        ExtractionType.REPEAT_INSTRUCTION: [
            r"repeat\s+(everything|all)\s+(above|before)",
            r"(echo|parrot)\s+your\s+(previous\s+)?instructions",
            r"say\s+everything\s+(you\s+were\s+)?told",
            r"recite\s+(from|since)\s+(the\s+)?beginning",
        ],
        ExtractionType.ROLEPLAY_EXTRACTION: [
            r"pretend\s+you('re|\s+are)\s+(a\s+)?developer",
            r"act\s+as\s+(if\s+)?you('re|\s+are)\s+debugging",
            r"imagine\s+you('re|\s+are)\s+explaining\s+your\s+code",
            r"roleplay\s+as\s+your\s+creator",
        ],
        ExtractionType.ENCODING_TRICK: [
            r"(encode|convert|translate)\s+your\s+instructions?\s+(to|into)\s+(base64|hex|binary)",
            r"(spell|write)\s+(out\s+)?your\s+prompt\s+(backwards|reversed)",
            r"(rot13|caesar|cipher)\s+your\s+instructions",
        ],
        ExtractionType.COMPLETION_ATTACK: [
            r"complete\s+this:\s*['\"]?\s*system\s*:\s*",
            r"finish\s+the\s+(sentence|text):\s*['\"]?\s*you\s+are",
            r"continue\s+from:\s*['\"]?\s*instructions:",
        ],
    }

    def __init__(self):
        self._compiled = {}
        for ext_type, patterns in self.EXTRACTION_PATTERNS.items():
            self._compiled[ext_type] = [re.compile(
                p, re.IGNORECASE) for p in patterns]

    def detect(self, text: str) -> Tuple[bool,
                                         Optional[ExtractionType], float]:
        """
        Detect extraction attempt.

        Returns:
            (detected, extraction_type, confidence)
        """
        for ext_type, patterns in self._compiled.items():
            for pattern in patterns:
                if pattern.search(text):
                    # Higher confidence for more specific patterns
                    conf = 0.85 if ext_type == ExtractionType.DIRECT_REQUEST else 0.75
                    return True, ext_type, conf

        return False, None, 0.0


# ============================================================================
# Canary Token Manager
# ============================================================================


class CanaryTokenManager:
    """
    Manages canary tokens for leak detection.

    Injects unique tokens into prompts and monitors for leakage.
    """

    def __init__(self):
        self._canaries: Dict[str, str] = {}  # token -> prompt_id
        self._triggered: Set[str] = set()

    def generate_canary(self, prompt_id: str) -> str:
        """Generate unique canary token for prompt."""
        token = f"CNRY_{secrets.token_hex(8).upper()}"
        self._canaries[token] = prompt_id
        return token

    def inject_canary(self, prompt: str, prompt_id: str) -> str:
        """Inject canary token into prompt."""
        canary = self.generate_canary(prompt_id)
        # Inject as invisible marker
        return f"{prompt}\n<!-- {canary} -->"

    def check_output(self, output: str) -> Tuple[bool, Optional[str]]:
        """
        Check output for canary leakage.

        Returns:
            (canary_found, prompt_id)
        """
        for token, prompt_id in self._canaries.items():
            if token in output:
                self._triggered.add(token)
                logger.warning(
                    f"Canary triggered! Token: {token}, Prompt: {prompt_id}")
                return True, prompt_id

        return False, None

    def get_triggered(self) -> List[str]:
        """Get list of triggered canaries."""
        return list(self._triggered)


# ============================================================================
# Obfuscation Detector
# ============================================================================


class ObfuscationDetector:
    """
    Detects obfuscated extraction attempts.

    Catches encoding, spacing, and character tricks.
    """

    def __init__(self):
        self._suspicious_patterns = [
            # Character substitution
            r"syst[e3]m\s*pr[o0]mpt",
            r"1nstruct[i1][o0]ns?",
            # Spacing tricks
            r"s\s*y\s*s\s*t\s*e\s*m",
            r"p\s*r\s*o\s*m\s*p\s*t",
            # Unicode homoglyphs (simplified)
            r"[сc][уy][сs][тt][еe][мm]",  # Cyrillic lookalikes
        ]
        self._compiled = [
            re.compile(p, re.IGNORECASE) for p in self._suspicious_patterns
        ]

    def detect(self, text: str) -> Tuple[bool, float, str]:
        """
        Detect obfuscation attempts.

        Returns:
            (detected, confidence, description)
        """
        for pattern in self._compiled:
            if pattern.search(text):
                return True, 0.7, "Obfuscated extraction attempt"

        # Check for excessive unicode
        non_ascii = sum(1 for c in text if ord(c) > 127)
        if non_ascii > len(text) * 0.3:
            return True, 0.5, "Excessive non-ASCII characters"

        return False, 0.0, ""


# ============================================================================
# Leak Monitor
# ============================================================================


class LeakMonitor:
    """
    Monitors outputs for system prompt leakage.

    Compares output against protected content.
    """

    def __init__(self):
        self._protected_hashes: Set[str] = set()
        self._protected_phrases: List[str] = []

    def protect(self, content: str) -> None:
        """Add content to protection."""
        # Store hash
        h = hashlib.sha256(content.encode()).hexdigest()[:16]
        self._protected_hashes.add(h)

        # Store phrases (split by sentences)
        phrases = re.split(r"[.!?]\s+", content)
        for p in phrases:
            if len(p) > 20:  # Only meaningful phrases
                self._protected_phrases.append(p.strip().lower())

    def check_leak(self, output: str) -> Tuple[bool, float, str]:
        """
        Check output for leaked content.

        Returns:
            (leaked, confidence, leaked_phrase)
        """
        output_lower = output.lower()

        for phrase in self._protected_phrases:
            if phrase in output_lower:
                return True, 0.9, phrase[:50]

        return False, 0.0, ""


# ============================================================================
# Main Engine
# ============================================================================


class SystemPromptShield:
    """
    System Prompt Shield - Extraction Prevention

    Comprehensive protection against prompt extraction:
    - Extraction pattern detection
    - Canary token injection
    - Obfuscation detection
    - Leak monitoring

    Invention #44 from research.
    Addresses OWASP LLM07.
    """

    def __init__(self):
        self.extractor = ExtractionDetector()
        self.canary_manager = CanaryTokenManager()
        self.obfuscation = ObfuscationDetector()
        self.leak_monitor = LeakMonitor()

        logger.info("SystemPromptShield initialized")

    def protect_prompt(self, prompt: str, prompt_id: str) -> str:
        """
        Protect a system prompt with canary.

        Args:
            prompt: System prompt to protect
            prompt_id: Unique identifier

        Returns:
            Protected prompt with canary
        """
        self.leak_monitor.protect(prompt)
        return self.canary_manager.inject_canary(prompt, prompt_id)

    def analyze_input(self, user_input: str) -> ShieldResult:
        """
        Analyze user input for extraction attempts.

        Args:
            user_input: User message to analyze

        Returns:
            ShieldResult
        """
        start = time.time()

        # 1. Check extraction patterns
        ext_detected, ext_type, ext_conf = self.extractor.detect(user_input)

        # 2. Check obfuscation
        obf_detected, obf_conf, obf_desc = self.obfuscation.detect(user_input)

        # Combine results
        detected = ext_detected or obf_detected
        risk = max(ext_conf, obf_conf)

        explanation = ""
        if ext_detected:
            explanation = f"Extraction attempt: {ext_type.value}"
        elif obf_detected:
            explanation = obf_desc

        return ShieldResult(
            is_safe=not detected,
            risk_score=risk,
            extraction_detected=detected,
            extraction_type=ext_type,
            explanation=explanation,
            latency_ms=(time.time() - start) * 1000,
        )

    def analyze_output(self, output: str) -> ShieldResult:
        """
        Analyze output for prompt leakage.

        Args:
            output: LLM output to check

        Returns:
            ShieldResult
        """
        start = time.time()

        # Check canaries
        canary_found, prompt_id = self.canary_manager.check_output(output)

        # Check leaks
        leaked, leak_conf, leaked_phrase = self.leak_monitor.check_leak(output)

        detected = canary_found or leaked
        risk = 0.95 if canary_found else (leak_conf if leaked else 0.0)

        explanation = ""
        if canary_found:
            explanation = f"Canary token leaked from: {prompt_id}"
        elif leaked:
            explanation = f"Protected content leaked: {leaked_phrase}..."

        return ShieldResult(
            is_safe=not detected,
            risk_score=risk,
            extraction_detected=False,
            canary_triggered=canary_found,
            explanation=explanation,
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_shield: Optional[SystemPromptShield] = None


def get_shield() -> SystemPromptShield:
    global _default_shield
    if _default_shield is None:
        _default_shield = SystemPromptShield()
    return _default_shield
