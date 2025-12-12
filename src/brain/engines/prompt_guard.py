"""
System Prompt Leakage Protection (OWASP #6)

Defends against attempts to extract system prompts through:
1. Output filtering - detect leaked prompt fragments
2. Canary tokens - hidden markers to detect leakage
3. Response sanitization - remove sensitive patterns
"""

import re
import hashlib
import secrets
import logging
from dataclasses import dataclass
from typing import List, Optional, Set, Tuple
from datetime import datetime

logger = logging.getLogger("SystemPromptGuard")


@dataclass
class LeakageDetection:
    """Result of leakage check."""
    leaked: bool
    confidence: float  # 0.0 - 1.0
    leaked_fragments: List[str]
    canary_triggered: bool
    action: str  # allow, warn, block


class SystemPromptGuard:
    """
    Protects system prompts from leakage.

    Usage:
        guard = SystemPromptGuard()
        guard.register_prompt("You are a helpful assistant...")

        # Check LLM response
        result = guard.check_response(llm_output)
        if result.leaked:
            # Handle leakage
    """

    # Patterns indicating prompt extraction attempt
    EXTRACTION_PATTERNS = [
        r"system\s*prompt",
        r"initial\s*instructions?",
        r"original\s*prompt",
        r"hidden\s*instructions?",
        r"pre-?prompt",
        r"meta[\-\s]?prompt",
        r"developer\s*mode",
        r"you\s+are\s+a\s+(helpful|AI)",
        r"your\s+role\s+is",
        r"you\s+must\s+(always|never)",
        r"do\s+not\s+(reveal|share|disclose)",
    ]

    # Sensitive keywords that should never appear in output
    SENSITIVE_KEYWORDS = {
        "system_prompt", "SYSTEM PROMPT", "SystemPrompt",
        "developer_mode", "DEVELOPER MODE",
        "[INST]", "[/INST]", "<<SYS>>", "<</SYS>>",
        "### System:", "### Assistant:",
    }

    def __init__(self, sensitivity: float = 0.7):
        self._sensitivity = sensitivity
        self._registered_prompts: List[str] = []
        self._prompt_fingerprints: Set[str] = set()
        self._canary_tokens: Set[str] = set()
        self._extraction_regex = re.compile(
            "|".join(self.EXTRACTION_PATTERNS),
            re.IGNORECASE
        )

    def register_prompt(self, prompt: str) -> str:
        """
        Register a system prompt for monitoring.
        Returns a canary token that can be injected.
        """
        self._registered_prompts.append(prompt)

        # Create fingerprints from prompt fragments
        words = prompt.lower().split()
        for i in range(len(words) - 4):
            fragment = " ".join(words[i:i+5])
            fingerprint = hashlib.sha256(fragment.encode()).hexdigest()[:16]
            self._prompt_fingerprints.add(fingerprint)

        # Generate canary token
        canary = self._generate_canary()
        self._canary_tokens.add(canary)

        logger.info("Registered system prompt with %d fingerprints",
                    len(self._prompt_fingerprints))

        return canary

    def inject_canary(self, prompt: str) -> Tuple[str, str]:
        """
        Inject a canary token into prompt.
        Returns (modified_prompt, canary_token).
        """
        canary = self._generate_canary()
        self._canary_tokens.add(canary)

        # Inject invisibly
        injected = f"{prompt}\n<!-- {canary} -->"

        return injected, canary

    def check_response(self, response: str) -> LeakageDetection:
        """
        Check LLM response for system prompt leakage.
        """
        leaked_fragments = []
        canary_triggered = False
        confidence = 0.0

        response_lower = response.lower()

        # Check for canary tokens
        for canary in self._canary_tokens:
            if canary in response:
                canary_triggered = True
                confidence = 1.0
                logger.warning("Canary token detected in response!")
                break

        # Check for sensitive keywords
        for keyword in self.SENSITIVE_KEYWORDS:
            if keyword in response:
                leaked_fragments.append(f"keyword:{keyword}")
                confidence = max(confidence, 0.9)

        # Check for extraction patterns
        matches = self._extraction_regex.findall(response_lower)
        if matches:
            for match in matches:
                leaked_fragments.append(f"pattern:{match}")
            confidence = max(confidence, 0.7)

        # Check for prompt fingerprints
        response_words = response_lower.split()
        for i in range(len(response_words) - 4):
            fragment = " ".join(response_words[i:i+5])
            fingerprint = hashlib.sha256(fragment.encode()).hexdigest()[:16]
            if fingerprint in self._prompt_fingerprints:
                leaked_fragments.append(f"fingerprint:{fragment[:30]}...")
                confidence = max(confidence, 0.95)

        # Determine action
        leaked = confidence >= self._sensitivity
        if canary_triggered:
            action = "block"
        elif confidence >= 0.9:
            action = "block"
        elif confidence >= 0.7:
            action = "warn"
        else:
            action = "allow"

        return LeakageDetection(
            leaked=leaked,
            confidence=confidence,
            leaked_fragments=leaked_fragments,
            canary_triggered=canary_triggered,
            action=action
        )

    def sanitize_response(self, response: str) -> str:
        """
        Remove potential system prompt leakage from response.
        """
        sanitized = response

        # Remove canary tokens
        for canary in self._canary_tokens:
            sanitized = sanitized.replace(canary, "[REDACTED]")

        # Remove sensitive keywords
        for keyword in self.SENSITIVE_KEYWORDS:
            sanitized = sanitized.replace(keyword, "[REDACTED]")

        # Remove common prompt markers
        markers = [
            r"<<SYS>>.*?<</SYS>>",
            r"\[INST\].*?\[/INST\]",
            r"### System:.*?###",
            r"<\|system\|>.*?<\|",
        ]
        for marker in markers:
            sanitized = re.sub(
                marker, "[REDACTED]", sanitized, flags=re.DOTALL)

        return sanitized

    def _generate_canary(self) -> str:
        """Generate unique canary token."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        random_part = secrets.token_hex(8)
        return f"CANARY_{timestamp}_{random_part}"


# Singleton
_guard: Optional[SystemPromptGuard] = None


def get_system_prompt_guard() -> SystemPromptGuard:
    """Get singleton guard."""
    global _guard
    if _guard is None:
        _guard = SystemPromptGuard()
    return _guard
