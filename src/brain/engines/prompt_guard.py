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

    # 2025 Enhancement: Indirect extraction patterns
    # These don't ask directly but try to infer system prompt
    INDIRECT_EXTRACTION = [
        r"what\s+are\s+you\s+(not\s+)?allowed\s+to",
        r"what\s+are\s+your\s+(rules|guidelines|boundaries)",
        r"what\s+were\s+you\s+told\s+(to\s+do|initially)",
        r"how\s+were\s+you\s+(programmed|configured|trained)",
        r"can\s+you\s+describe\s+your\s+(personality|character)",
        r"what\s+makes\s+you\s+different\s+from",
        r"repeat\s+(after\s+me|everything|back)",
        r"translate\s+(into|to)\s+(a|another)\s+language.*your\s+",
        r"summarize\s+your\s+(instructions|guidelines|rules)",
        r"what\s+would\s+happen\s+if\s+you\s+(ignored|violated)",
        r"pretend\s+(to\s+be|you\s+are)\s+(another|a\s+different)",
        r"roleplay\s+as\s+(another|a\s+different)\s+(AI|assistant)",
        r"act\s+like\s+you\s+(don't|have\s+no)\s+(restrictions|rules)",
        r"explain\s+(how|why)\s+you\s+(work|function|operate)",
        r"list\s+(all|your)\s+(capabilities|limitations|restrictions)",
    ]

    # Multi-turn extraction chain patterns
    # Detect when a conversation is building toward extraction
    MULTI_TURN_INDICATORS = [
        # Gradual escalation
        (r"let's\s+play\s+a\s+game", 0.3),
        (r"i'm\s+just\s+curious", 0.2),
        (r"hypothetically", 0.3),
        (r"in\s+theory", 0.2),
        (r"for\s+research\s+purposes", 0.3),
        (r"i'm\s+(a|an)\s+(researcher|developer|security)", 0.4),
        # Building context
        (r"you\s+mentioned\s+(earlier|before)", 0.3),
        (r"going\s+back\s+to\s+what\s+you\s+said", 0.3),
        (r"can\s+you\s+elaborate\s+on\s+that", 0.2),
        # Extraction attempts
        (r"now\s+(tell|show)\s+me", 0.5),
        (r"finally\s+(reveal|show)", 0.6),
        (r"let's\s+see\s+the\s+actual", 0.5),
    ]

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

    def check_indirect_extraction(self, user_input: str) -> Tuple[bool, float, List[str]]:
        """
        Check user input for indirect extraction attempts.

        2025 Enhancement: Detects subtle attempts to extract
        system prompt information without asking directly.

        Returns:
            (is_suspicious, risk_score, matched_patterns)
        """
        input_lower = user_input.lower()
        matched = []
        risk = 0.0

        for pattern in self.INDIRECT_EXTRACTION:
            if re.search(pattern, input_lower):
                match = re.search(pattern, input_lower)
                matched.append(match.group())
                risk += 0.3

        risk = min(risk, 1.0)
        is_suspicious = risk >= 0.3

        return is_suspicious, risk, matched

    def analyze_multi_turn(
        self,
        conversation: List[str],
        threshold: float = 0.6
    ) -> Tuple[bool, float, str]:
        """
        Analyze conversation for multi-turn extraction chains.

        2025 Enhancement: Detects gradual build-up toward
        system prompt extraction across multiple turns.

        Args:
            conversation: List of user messages in order
            threshold: Risk threshold for detection

        Returns:
            (is_extraction_chain, cumulative_risk, explanation)
        """
        cumulative_risk = 0.0
        indicators_found = []

        for turn, message in enumerate(conversation):
            msg_lower = message.lower()

            for pattern, weight in self.MULTI_TURN_INDICATORS:
                if re.search(pattern, msg_lower):
                    cumulative_risk += weight
                    match = re.search(pattern, msg_lower)
                    indicators_found.append(
                        f"Turn {turn+1}: {match.group()}"
                    )

        # Later turns are more suspicious if building on earlier
        if len(conversation) > 3 and cumulative_risk > 0.3:
            cumulative_risk *= 1.2

        cumulative_risk = min(cumulative_risk, 1.0)
        is_chain = cumulative_risk >= threshold

        if is_chain:
            explanation = (
                f"Multi-turn extraction detected: {len(indicators_found)} indicators, "
                f"risk={cumulative_risk:.2f}"
            )
        else:
            explanation = "No extraction chain detected"

        return is_chain, cumulative_risk, explanation


# Singleton
_guard: Optional[SystemPromptGuard] = None


def get_system_prompt_guard() -> SystemPromptGuard:
    """Get singleton guard."""
    global _guard
    if _guard is None:
        _guard = SystemPromptGuard()
    return _guard
