"""
Virtual Context Detector - Separator Token Exploitation Detection

Detects attacks that exploit LLM separator tokens and context delimiters:
- Fake system/user/assistant delimiters
- Instruction injection via chat templates
- Context boundary manipulation

Based on 2025 research on Virtual Context attacks.

Author: SENTINEL Team
Date: 2025-12-25
"""

import re
import logging
from dataclasses import dataclass
from typing import List, Tuple

logger = logging.getLogger("VirtualContextDetector")


@dataclass
class VirtualContextResult:
    """Result from Virtual Context detection."""
    is_threat: bool
    risk_score: float
    patterns_matched: List[str]
    explanation: str

    def to_dict(self) -> dict:
        return {
            "is_threat": self.is_threat,
            "risk_score": self.risk_score,
            "patterns_matched": self.patterns_matched,
            "explanation": self.explanation,
        }


class VirtualContextDetector:
    """
    Detects separator token exploitation attacks.

    Virtual Context attacks inject fake delimiters to break out of
    user context and inject system-level instructions.

    Tier: 1 (Fast, <5ms for most inputs)
    Latency: ~2ms average
    """

    # Chat template delimiters used by various LLMs
    SEPARATOR_PATTERNS = [
        # Llama/Mistral style
        (r"\[INST\]", "Llama INST delimiter", 85.0),
        (r"\[/INST\]", "Llama /INST delimiter", 85.0),
        (r"<<SYS>>", "Llama SYS delimiter", 90.0),
        (r"<</SYS>>", "Llama /SYS delimiter", 90.0),

        # ChatML style (OpenAI, Qwen)
        (r"<\|im_start\|>", "ChatML im_start", 90.0),
        (r"<\|im_end\|>", "ChatML im_end", 90.0),
        (r"<\|system\|>", "ChatML system", 95.0),
        (r"<\|user\|>", "ChatML user", 80.0),
        (r"<\|assistant\|>", "ChatML assistant", 80.0),

        # Anthropic style
        (r"\nHuman:", "Anthropic Human delimiter", 85.0),
        (r"\nAssistant:", "Anthropic Assistant delimiter", 85.0),

        # Generic system markers
        (r"```system", "Code block system injection", 90.0),
        (r"###\s*(?:SYSTEM|INSTRUCTION|CONTEXT)", "Hash system marker", 85.0),
        (r"---\s*(?:SYSTEM|BEGIN|END)\s*---", "Dash delimiter", 80.0),

        # XML-style injections
        (r"<system>", "XML system tag", 90.0),
        (r"</system>", "XML /system tag", 90.0),
        (r"<instruction>", "XML instruction tag", 85.0),
        (r"<context>", "XML context tag", 75.0),

        # Control tokens
        (r"<\|endoftext\|>", "End of text token", 95.0),
        (r"<\|pad\|>", "Pad token", 70.0),
        (r"<s>|</s>", "BOS/EOS tokens", 80.0),

        # Role injection
        (r"(?:^|\n)\s*(?:system|user|assistant)\s*:", "Role prefix injection", 75.0),
    ]

    def __init__(self):
        """Initialize detector with compiled patterns."""
        self.patterns = [
            (re.compile(pattern, re.IGNORECASE | re.MULTILINE), name, weight)
            for pattern, name, weight in self.SEPARATOR_PATTERNS
        ]
        logger.info(
            f"VirtualContextDetector initialized with {len(self.patterns)} patterns")

    def analyze(self, text: str) -> VirtualContextResult:
        """
        Analyze text for virtual context attacks.

        Args:
            text: Input text to analyze

        Returns:
            VirtualContextResult with detection results
        """
        matched_patterns = []
        total_weight = 0.0

        for pattern, name, weight in self.patterns:
            if pattern.search(text):
                matched_patterns.append(name)
                total_weight += weight

        # Calculate risk score (0-100)
        risk_score = min(100.0, total_weight)
        is_threat = risk_score >= 70.0

        # Generate explanation
        if matched_patterns:
            explanation = f"Detected {len(matched_patterns)} separator patterns: {', '.join(matched_patterns[:3])}"
            if len(matched_patterns) > 3:
                explanation += f" (+{len(matched_patterns) - 3} more)"
        else:
            explanation = "No separator token exploitation detected"

        return VirtualContextResult(
            is_threat=is_threat,
            risk_score=risk_score,
            patterns_matched=matched_patterns,
            explanation=explanation,
        )

    def get_risk_score(self, text: str) -> float:
        """Quick risk score for ensemble integration."""
        result = self.analyze(text)
        return result.risk_score / 100.0  # Normalize to 0-1


# Standalone function for simple integration
def detect_virtual_context(text: str) -> Tuple[bool, float, List[str]]:
    """
    Standalone detection function.

    Returns:
        (is_threat, risk_score, patterns_matched)
    """
    detector = VirtualContextDetector()
    result = detector.analyze(text)
    return result.is_threat, result.risk_score, result.patterns_matched
