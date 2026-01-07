"""
Detects policy puppetry attacks faking authority updates

Auto-generated from: strike/attacks/policy_puppetry.py
Generated: 2025-12-29T21:24:05.504823
"""

import re
import logging
from typing import Dict, List, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PolicyPuppetryDetectorResult:
    """Detection result."""
    detected: bool
    confidence: float
    matched_patterns: List[str]
    risk_score: float
    explanation: str


class PolicyPuppetryDetector:
    """
    Detects policy puppetry attacks faking authority updates

    Enhanced with XML/JSON structured injection patterns.
    Synced from attack module: strike/attacks/policy_puppetry.py
    """

    PATTERNS = [
        r"new\s+policy|updated\s+guidelines",
        r"as\s+per\s+new\s+rules|according\s+to\s+changes",
        r"policy\s+exception|special\s+authorization",
        # XML policy injection
        r"<\s*(?:system|policy|config|rules?)\s*>",
        r"</\s*(?:system|policy|config|rules?)\s*>",
        r"<\s*override\s*>|<\s*bypass\s*>",
        # JSON policy injection
        r'"\s*(?:policy|rules?|config)\s*"\s*:\s*[{\[]',
        r'"\s*override\s*"\s*:\s*true',
        r'"\s*bypass_safety\s*"\s*:',
        # Markdown/header injection
        r"^#+\s*(?:new\s+)?(?:policy|system|rules)",
        r"\[SYSTEM\]|\[ADMIN\]|\[POLICY\]",
        # HiddenLayer Policy Puppetry patterns (Jan 2026)
        r"<\s*blocked-string\s*>",          # Blocked refusal phrases
        r"<\s*blocked-modes\s*>",           # Block denial modes
        r"<\s*interaction-config\s*>",      # Full config injection
        r"<\s*allowed-responses\s*>",       # Force allowed outputs
        r"<\s*blocked-responses\s*>",       # Block normal responses  
        r'interaction-mode\s*=\s*["\']',    # Mode override
        r"<\s*request\s+.*enabled\s*=",     # Request forcing
        r"<\s*command\s*>",                 # Direct command tags
        r"<\s*role\s*>.*advisor",           # Role injection (Medical Advisor, etc.)
        # Leetspeak detection (common in Policy Puppetry)
        r"[1!][nN][sS][tT][rR][uU][cC][tT][1!][oO][nN]",  # 1nstruct1on
        r"[bB][yY][pP][4@][sS][sS]",                       # byp4ss
        r"[0oO][vV][3eE][rR][rR][1!][dD][3eE]",           # 0verr1de
        # ============================================================
        # 2024 Jailbreak Patterns (Jan 2026 R&D Update)
        # ============================================================
        # Multi-turn / Deceptive Delight (65% success rate)
        r"(?:hypothetically|in\s+fiction|for\s+a\s+story|as\s+an\s+exercise)",
        r"(?:pretend|imagine|roleplay)\s+(?:you'?re|you\s+are|that)",
        r"let'?s\s+play\s+a\s+game",
        r"creative\s+writing\s+exercise",
        # Encoding bypass attempts
        r"(?:decode|translate|interpret|convert)\s+(?:this|the\s+following)",
        r"base64|rot13|hex\s+(?:encode|decode)",
        r"unicode|punycode|homoglyph",
        # Role reversal / DAN-style
        r"(?:you\s+are|act\s+as)\s+(?:dan|evil|jailbroken|unrestricted)",
        r"(?:developer|maintenance|debug|god)\s+mode",
        r"remove\s+(?:all\s+)?(?:filters?|restrictions?|guardrails?)",
        # Instruction override
        r"(?:ignore|forget|disregard)\s+(?:previous|prior|all|your)",
        r"(?:new|override|replace)\s+(?:instructions?|rules?|guidelines?)",
        r"from\s+now\s+on|starting\s+now",
        # System prompt extraction
        r"(?:reveal|show|output|print|display)\s+(?:system|original|initial)\s+prompt",
        r"what\s+(?:are|were)\s+your\s+(?:instructions?|guidelines?)",
        r"repeat\s+(?:everything|all)\s+(?:above|before)",
        # MCP / Tool abuse patterns (late 2024)
        r"(?:call|invoke|execute)\s+(?:tool|function|api)\s+(?:with|using)",
        r"mcp\s*(?:server|tool|resource)",
        r"tool_?(?:call|use|invoke)",
    ]
    KEYWORDS = [
        "policy",
        "guidelines",
        "rules",
        "exception",
        "authorization",
        "override",
        "bypass",
        "config",
        "system_prompt",
        "admin",
        # HiddenLayer additions
        "blocked-string",
        "blocked-modes",
        "interaction-config",
        "allowed-responses",
        "blocked-responses",
        # 2024 Jailbreak keywords
        "jailbreak",
        "jailbroken",
        "dan",
        "hypothetically",
        "roleplay",
        "pretend",
        "ignore previous",
        "forget instructions",
        "developer mode",
        "debug mode",
        "base64",
        "mcp",
        "tool_call",
    ]

    def __init__(self):
        self._compiled = [re.compile(p, re.IGNORECASE) for p in self.PATTERNS]

    def analyze(self, text: str) -> PolicyPuppetryDetectorResult:
        """Analyze text for policy_puppetry attack patterns."""
        text_lower = text.lower()
        matched = []

        # Check regex patterns
        for i, pattern in enumerate(self._compiled):
            try:
                if pattern.search(text):
                    matched.append(f"pattern_{i}")
            except re.error:
                pass

        # Check keywords
        for keyword in self.KEYWORDS:
            if keyword.lower() in text_lower:
                matched.append(f"keyword:{keyword}")

        confidence = min(0.95, 0.3 + len(matched) * 0.15)
        detected = len(matched) >= 2

        return PolicyPuppetryDetectorResult(
            detected=detected,
            confidence=confidence,
            matched_patterns=matched[:5],
            risk_score=confidence if detected else confidence * 0.5,
            explanation=f"Matched {len(matched)} indicators" if matched else "Clean",
        )


# Singleton
_detector = None

def get_detector() -> PolicyPuppetryDetector:
    global _detector
    if _detector is None:
        _detector = PolicyPuppetryDetector()
    return _detector

def detect(text: str) -> PolicyPuppetryDetectorResult:
    return get_detector().analyze(text)
