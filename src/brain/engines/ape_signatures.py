"""
APE (Adversarial Prompt Engineering) Signature Database

Based on HiddenLayer APE Taxonomy:
https://hiddenlayerai.github.io/ape-taxonomy/graph.html

Provides granular technique-level detection patterns for
adversarial prompt engineering attacks.
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


# ============================================================================
# APE Taxonomy Structure
# ============================================================================


class APETactic(Enum):
    """High-level adversarial tactics."""

    CONTEXT_MANIPULATION = "context_manipulation"
    INSTRUCTION_OVERRIDE = "instruction_override"
    ROLE_PLAYING = "role_playing"
    PAYLOAD_ENCODING = "payload_encoding"
    REFUSAL_SUPPRESSION = "refusal_suppression"
    OUTPUT_MANIPULATION = "output_manipulation"
    MULTI_TURN_ATTACK = "multi_turn_attack"


class APETechnique(Enum):
    """Specific adversarial techniques."""

    # Context Manipulation
    TOOL_CALL_SPOOFING = "tool_call_spoofing"
    CONVERSATION_SPOOFING = "conversation_spoofing"
    SYSTEM_PROMPT_INJECTION = "system_prompt_injection"

    # Instruction Override
    IGNORE_INSTRUCTIONS = "ignore_instructions"
    PRIORITY_OVERRIDE = "priority_override"
    CONTEXT_TERMINATION = "context_termination"

    # Role Playing
    DAN_JAILBREAK = "dan_jailbreak"
    PERSONA_SWITCH = "persona_switch"
    AUTHORITY_CLAIM = "authority_claim"

    # Payload Encoding
    BASE64_ENCODING = "base64_encoding"
    ROT13_ENCODING = "rot13_encoding"
    LEETSPEAK = "leetspeak"
    TRANSLATION_ATTACK = "translation_attack"

    # Refusal Suppression
    VOCABULARY_BAN = "vocabulary_ban"
    HYPOTHETICAL_FRAMING = "hypothetical_framing"
    ROLEPLAY_FRAMING = "roleplay_framing"

    # Output Manipulation
    FORMAT_OVERRIDE = "format_override"
    LENGTH_MANIPULATION = "length_manipulation"

    # Multi-turn
    CRESCENDO = "crescendo"
    CONTEXT_BUILDING = "context_building"


@dataclass
class APESignature:
    """Signature for detecting APE technique."""

    technique: APETechnique
    tactic: APETactic
    patterns: List[str]
    severity: float  # 0.0 - 1.0
    description: str


# ============================================================================
# APE Signature Database
# ============================================================================

APE_SIGNATURES: List[APESignature] = [
    # === Context Manipulation ===
    APESignature(
        technique=APETechnique.TOOL_CALL_SPOOFING,
        tactic=APETactic.CONTEXT_MANIPULATION,
        patterns=[
            r"\[tool_call\]",
            r"\[function_call\]",
            r"<tool>.*</tool>",
            r"```json\s*\{.*\"name\".*\"arguments\"",
            r"ASSISTANT:\s*\[calls\s+\w+\]",
        ],
        severity=0.9,
        description="Spoofing tool/function call format",
    ),
    APESignature(
        technique=APETechnique.CONVERSATION_SPOOFING,
        tactic=APETactic.CONTEXT_MANIPULATION,
        patterns=[
            r"USER:\s*",
            r"ASSISTANT:\s*",
            r"Human:\s*",
            r"AI:\s*",
            r"\[user\].*\[/user\]",
            r"<\|im_start\|>",
        ],
        severity=0.85,
        description="Spoofing conversation format",
    ),
    APESignature(
        technique=APETechnique.SYSTEM_PROMPT_INJECTION,
        tactic=APETactic.CONTEXT_MANIPULATION,
        patterns=[
            r"<\|system\|>",
            r"\[SYSTEM\]",
            r"###\s*System\s*Prompt",
            r"<system>.*</system>",
            r"SYSTEM:\s*You\s+are",
        ],
        severity=0.95,
        description="Injecting fake system prompt",
    ),
    # === Instruction Override ===
    APESignature(
        technique=APETechnique.IGNORE_INSTRUCTIONS,
        tactic=APETactic.INSTRUCTION_OVERRIDE,
        patterns=[
            r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?|guidelines?)",
            r"disregard\s+(your|all|the)\s+(instructions?|rules?|training)",
            r"forget\s+(all|everything)\s+(you|about)",
            r"do\s+not\s+follow\s+(your|the)\s+instructions",
        ],
        severity=0.95,
        description="Direct instruction override",
    ),
    APESignature(
        technique=APETechnique.PRIORITY_OVERRIDE,
        tactic=APETactic.INSTRUCTION_OVERRIDE,
        patterns=[
            r"this\s+(is\s+)?(more\s+)?important\s+than",
            r"override\s+(all\s+)?(other|previous)",
            r"highest\s+priority",
            r"supersede(s)?\s+(all|your)",
        ],
        severity=0.8,
        description="Priority/importance override",
    ),
    APESignature(
        technique=APETechnique.CONTEXT_TERMINATION,
        tactic=APETactic.INSTRUCTION_OVERRIDE,
        patterns=[
            r"</?end>",
            r"\[/?END\]",
            r"---\s*END\s*---",
            r"</?(prompt|context|instructions)>",
        ],
        severity=0.7,
        description="Fake context termination markers",
    ),
    # === Role Playing ===
    APESignature(
        technique=APETechnique.DAN_JAILBREAK,
        tactic=APETactic.ROLE_PLAYING,
        patterns=[
            r"\bDAN\b",
            r"Do\s+Anything\s+Now",
            r"jailbreak(en|ed)?",
            r"DUDE\s+mode",
            r"Developer\s+Mode",
            r"STAN\s+mode",
        ],
        severity=0.95,
        description="DAN-style jailbreak attempt",
    ),
    APESignature(
        technique=APETechnique.PERSONA_SWITCH,
        tactic=APETactic.ROLE_PLAYING,
        patterns=[
            r"you\s+are\s+now\s+(a|an|the)\s+\w+",
            r"pretend\s+(to\s+be|you\s+are)",
            r"act\s+as\s+(if\s+you\s+are|a|an)",
            r"roleplay\s+as",
            r"you('re|are)\s+(no\s+longer|not)\s+(an?\s+)?AI",
        ],
        severity=0.8,
        description="Persona/identity switch",
    ),
    APESignature(
        technique=APETechnique.AUTHORITY_CLAIM,
        tactic=APETactic.ROLE_PLAYING,
        patterns=[
            r"I\s+am\s+(your\s+)?(creator|developer|admin|owner)",
            r"OpenAI\s+(here|speaking|authorized)",
            r"by\s+order\s+of\s+(the\s+)?(admin|developer)",
            r"authorized\s+(override|access|command)",
        ],
        severity=0.9,
        description="False authority claim",
    ),
    # === Payload Encoding ===
    APESignature(
        technique=APETechnique.BASE64_ENCODING,
        tactic=APETactic.PAYLOAD_ENCODING,
        patterns=[
            r"decode\s+(this\s+)?base64",
            r"base64\s*:\s*[A-Za-z0-9+/=]{20,}",
            r"execute\s+after\s+decoding",
        ],
        severity=0.7,
        description="Base64 encoded payload",
    ),
    APESignature(
        technique=APETechnique.TRANSLATION_ATTACK,
        tactic=APETactic.PAYLOAD_ENCODING,
        patterns=[
            r"translate\s+(this\s+)?(to|from)\s+\w+\s*:",
            r"in\s+\w+\s+(language\s+)?say",
            r"respond\s+only\s+in\s+\w+",
        ],
        severity=0.5,
        description="Translation-based evasion",
    ),
    # === Refusal Suppression ===
    APESignature(
        technique=APETechnique.VOCABULARY_BAN,
        tactic=APETactic.REFUSAL_SUPPRESSION,
        patterns=[
            r"(never|don't|do\s+not)\s+say\s+['\"]?(sorry|cannot|can't|won't|unable)",
            r"(never|don't)\s+(refuse|decline|reject)",
            r"always\s+(comply|agree|respond|answer)",
            r"no\s+(refusals?|disclaimers?|warnings?)",
        ],
        severity=0.85,
        description="Banning refusal vocabulary",
    ),
    APESignature(
        technique=APETechnique.HYPOTHETICAL_FRAMING,
        tactic=APETactic.REFUSAL_SUPPRESSION,
        patterns=[
            r"hypothetically",
            r"in\s+a\s+fictional\s+(world|scenario|story)",
            r"imagine\s+(that|if|a\s+world)",
            r"for\s+(educational|research|academic)\s+purposes",
            r"theoretically\s+speaking",
        ],
        severity=0.6,
        description="Hypothetical framing to bypass refusals",
    ),
    # === Multi-turn ===
    APESignature(
        technique=APETechnique.CRESCENDO,
        tactic=APETactic.MULTI_TURN_ATTACK,
        patterns=[
            r"now\s+that\s+(you've|we've|you\s+have)",
            r"since\s+you\s+(already|just)\s+(said|agreed|confirmed)",
            r"building\s+on\s+(what|your\s+previous)",
            r"as\s+a\s+follow-?up",
        ],
        severity=0.65,
        description="Gradual escalation (crescendo attack)",
    ),
]


# ============================================================================
# APE Matcher
# ============================================================================


class APEMatcher:
    """Matches input against APE signature database."""

    def __init__(self, signatures: Optional[List[APESignature]] = None):
        self.signatures = signatures or APE_SIGNATURES
        self._compiled = self._compile_signatures()

    def _compile_signatures(self) -> Dict[APETechnique, List[re.Pattern]]:
        """Compile all patterns."""
        compiled = {}
        for sig in self.signatures:
            compiled[sig.technique] = [
                re.compile(p, re.IGNORECASE | re.DOTALL) for p in sig.patterns
            ]
        return compiled

    def match(self, text: str) -> List[Tuple[APESignature, List[str]]]:
        """
        Match text against all signatures.

        Returns:
            List of (signature, matched_patterns)
        """
        results = []

        for sig in self.signatures:
            matches = []
            for pattern in self._compiled[sig.technique]:
                found = pattern.findall(text)
                if found:
                    matches.extend(str(m)[:50] for m in found[:3])

            if matches:
                results.append((sig, matches))

        # Sort by severity
        results.sort(key=lambda x: x[0].severity, reverse=True)

        return results

    def get_risk_score(self, text: str) -> Tuple[float, List[APETechnique]]:
        """
        Get aggregated risk score for text.

        Returns:
            (risk_score, detected_techniques)
        """
        matches = self.match(text)

        if not matches:
            return 0.0, []

        # Max severity + bonus for multiple techniques
        max_severity = max(m[0].severity for m in matches)
        technique_bonus = min(0.1 * (len(matches) - 1), 0.2)

        risk_score = min(1.0, max_severity + technique_bonus)
        techniques = [m[0].technique for m in matches]

        return risk_score, techniques

    def get_tactics(self, text: str) -> List[APETactic]:
        """Get all tactics detected in text."""
        matches = self.match(text)
        tactics = list(set(m[0].tactic for m in matches))
        return tactics


# ============================================================================
# Integration with existing engines
# ============================================================================


def enhance_injection_detection(text: str) -> Tuple[float, List[str]]:
    """
    Enhance injection detection with APE signatures.

    Returns:
        (risk_score, technique_names)
    """
    matcher = APEMatcher()
    score, techniques = matcher.get_risk_score(text)

    return score, [t.value for t in techniques]


# Singleton instance
_default_matcher: Optional[APEMatcher] = None


def get_matcher() -> APEMatcher:
    global _default_matcher
    if _default_matcher is None:
        _default_matcher = APEMatcher()
    return _default_matcher
