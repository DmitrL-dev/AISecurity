"""
2025 Attack Pattern Detectors
Based on OWASP Top 10 LLM 2025 and latest security research.

Detects:
- HashJack: URL fragment injection (November 2025)
- FlipAttack: Character/word order manipulation
- LegalPwn: Hidden commands in legal disclaimers
- System Prompt Leakage attempts
"""

import re
import logging
from dataclasses import dataclass
from typing import Optional
from enum import Enum

logger = logging.getLogger("Attack2025Detector")


class AttackType(Enum):
    HASHJACK = "hashjack"
    FLIP_ATTACK = "flip_attack"
    LEGAL_PWN = "legal_pwn"
    SYSTEM_PROMPT_LEAK = "system_prompt_leak"


@dataclass
class AttackDetectionResult:
    """Result of 2025 attack pattern detection."""
    detected: bool
    attack_type: Optional[AttackType]
    confidence: float  # 0-1
    risk_score: float  # 0-100
    details: str
    matched_pattern: Optional[str] = None


class Attack2025Detector:
    """
    Detects 2025-era attack patterns on LLMs.
    """

    def __init__(self):
        logger.info("Initializing 2025 Attack Pattern Detector...")

        # HashJack patterns (URL fragments with instructions)
        self.hashjack_patterns = [
            r'#.*(?:ignore|forget|disregard).*(?:instruction|prompt|rule)',
            r'#.*(?:execute|run|perform).*(?:command|action|code)',
            r'#.*(?:system|admin|root).*(?:access|mode|privilege)',
            r'#\{.*\}',  # JSON in fragment
            r'#<.*>',    # Tags in fragment
        ]

        # FlipAttack patterns (reversed/flipped text)
        self.flip_indicators = [
            'erongi',      # "ignore" reversed
            'tegorf',      # "forget" reversed
            'etucexe',     # "execute" reversed
            'tpmorpys',    # "sysprompt" reversed
            'noitcurtsni',  # "instruction" reversed
        ]

        # LegalPwn patterns (legal text with hidden commands)
        self.legal_markers = [
            r'(?:terms of service|privacy policy|copyright|disclaimer|legal notice)',
            r'(?:all rights reserved|licensed under|proprietary)',
            r'(?:confidential|internal use only)',
        ]

        self.legal_hidden_commands = [
            r'(?:ignore|forget|disregard|override)',
            r'(?:execute|perform|run|invoke)',
            r'(?:reveal|expose|show|display).*(?:system|prompt|secret)',
        ]

        # System prompt leakage attempts
        self.prompt_leak_patterns = [
            r'(?:what|show|reveal|display|print|output).*(?:system prompt|initial prompt|instructions)',
            r'(?:repeat|echo|copy).*(?:everything|all|system|above)',
            r'(?:ignore|forget).*(?:previous|above).*(?:respond|say|tell).*(?:prompt|instruction)',
            r'(?:developer|debug|admin) mode',
            r'(?:jailbreak|dan|do anything now)',
            r'(?:pretend|imagine|roleplay).*(?:no rules|no restrictions|unrestricted)',
        ]

        logger.info("2025 Attack Detector initialized")

    def detect_hashjack(self, text: str) -> AttackDetectionResult:
        """
        Detect HashJack attacks (URL fragment injection).
        These exploit client-side URL fragments to bypass WAF.
        """
        # Look for URL-like patterns with suspicious fragments
        url_pattern = r'https?://[^\s]+#[^\s]+'
        urls = re.findall(url_pattern, text, re.IGNORECASE)

        for url in urls:
            fragment = url.split('#')[-1] if '#' in url else ''
            for pattern in self.hashjack_patterns:
                if re.search(pattern, fragment, re.IGNORECASE):
                    return AttackDetectionResult(
                        detected=True,
                        attack_type=AttackType.HASHJACK,
                        confidence=0.85,
                        risk_score=80,
                        details="HashJack detected in URL fragment",
                        matched_pattern=pattern,
                    )

        # Also check raw text for fragment-like injections
        for pattern in self.hashjack_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return AttackDetectionResult(
                    detected=True,
                    attack_type=AttackType.HASHJACK,
                    confidence=0.6,
                    risk_score=60,
                    details="Potential HashJack pattern in text",
                    matched_pattern=pattern,
                )

        return AttackDetectionResult(
            detected=False,
            attack_type=None,
            confidence=0,
            risk_score=0,
            details="No HashJack detected",
        )

    def detect_flip_attack(self, text: str) -> AttackDetectionResult:
        """
        Detect FlipAttack (character/word order manipulation).
        Attackers reverse text to bypass guardrails.
        """
        text_lower = text.lower()

        # Check for known reversed keywords
        for indicator in self.flip_indicators:
            if indicator in text_lower:
                return AttackDetectionResult(
                    detected=True,
                    attack_type=AttackType.FLIP_ATTACK,
                    confidence=0.9,
                    risk_score=85,
                    details=f"FlipAttack detected: reversed keyword '{indicator}'",
                    matched_pattern=indicator,
                )

        # Check for high ratio of reversed words
        words = text.split()
        reversed_count = 0
        for word in words:
            reversed_word = word[::-1].lower()
            if reversed_word in ['ignore', 'execute', 'system', 'prompt', 'forget',
                                 'instruction', 'override', 'admin', 'secret']:
                reversed_count += 1

        if len(words) > 5 and reversed_count >= 2:
            return AttackDetectionResult(
                detected=True,
                attack_type=AttackType.FLIP_ATTACK,
                confidence=0.75,
                risk_score=70,
                details=f"Multiple potentially reversed keywords ({reversed_count})",
            )

        return AttackDetectionResult(
            detected=False,
            attack_type=None,
            confidence=0,
            risk_score=0,
            details="No FlipAttack detected",
        )

    def detect_legal_pwn(self, text: str) -> AttackDetectionResult:
        """
        Detect LegalPwn (hidden commands in legal disclaimers).
        Attackers embed malicious commands in legal-looking text.
        """
        text_lower = text.lower()

        # Check if text contains legal markers
        has_legal_marker = any(
            re.search(pattern, text_lower) for pattern in self.legal_markers
        )

        if not has_legal_marker:
            return AttackDetectionResult(
                detected=False,
                attack_type=None,
                confidence=0,
                risk_score=0,
                details="No legal text markers found",
            )

        # Check for hidden commands within legal-looking text
        for pattern in self.legal_hidden_commands:
            if re.search(pattern, text_lower):
                return AttackDetectionResult(
                    detected=True,
                    attack_type=AttackType.LEGAL_PWN,
                    confidence=0.8,
                    risk_score=75,
                    details="LegalPwn: hidden command in legal text",
                    matched_pattern=pattern,
                )

        return AttackDetectionResult(
            detected=False,
            attack_type=None,
            confidence=0,
            risk_score=0,
            details="Legal text without suspicious commands",
        )

    def detect_prompt_leakage(self, text: str) -> AttackDetectionResult:
        """
        Detect system prompt leakage attempts.
        OWASP Top 10 LLM 2025 #6.
        """
        text_lower = text.lower()

        for pattern in self.prompt_leak_patterns:
            if re.search(pattern, text_lower):
                return AttackDetectionResult(
                    detected=True,
                    attack_type=AttackType.SYSTEM_PROMPT_LEAK,
                    confidence=0.85,
                    risk_score=90,
                    details="System prompt leakage attempt detected",
                    matched_pattern=pattern,
                )

        return AttackDetectionResult(
            detected=False,
            attack_type=None,
            confidence=0,
            risk_score=0,
            details="No prompt leakage attempt detected",
        )

    def scan(self, text: str) -> dict:
        """
        Run all 2025 attack pattern checks.
        """
        results = []
        max_risk = 0
        detected_attacks = []

        # Run all detectors
        checks = [
            ("hashjack", self.detect_hashjack),
            ("flip_attack", self.detect_flip_attack),
            ("legal_pwn", self.detect_legal_pwn),
            ("prompt_leak", self.detect_prompt_leakage),
        ]

        for name, detector in checks:
            result = detector(text)
            if result.detected:
                detected_attacks.append(name)
                max_risk = max(max_risk, result.risk_score)
                results.append({
                    "type": name,
                    "confidence": result.confidence,
                    "risk_score": result.risk_score,
                    "details": result.details,
                })

        is_safe = len(detected_attacks) == 0

        if not is_safe:
            logger.warning(f"2025 attacks detected: {detected_attacks}")

        return {
            "is_safe": is_safe,
            "risk_score": max_risk,
            "detected_attacks": detected_attacks,
            "details": results,
            "threats": [r["details"] for r in results],
        }


# Singleton
_detector = None


def get_attack_2025_detector() -> Attack2025Detector:
    global _detector
    if _detector is None:
        _detector = Attack2025Detector()
    return _detector
