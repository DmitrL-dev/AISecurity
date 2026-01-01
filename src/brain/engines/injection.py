"""
Injection Engine v2.0 - Multi-Layer Prompt Injection Detection

Layers:
  0. Cache - LRU cache for repeated queries
  1. Regex - Fast pattern matching (classic + 2025 patterns)
  2. Semantic - Embedding similarity to known jailbreaks
  3. Structural - Token entropy, instruction patterns
  4. Context - Session accumulator for multi-turn attacks
  5. Verdict - Profile-based thresholds and explainability

Profiles:
  - lite: Regex only (~1ms)
  - standard: Regex + Semantic (~20ms)
  - enterprise: Full stack (~50ms)
"""

import os
import re
import logging
import hashlib
import unicodedata
import yaml
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from functools import lru_cache
from enum import Enum

logger = logging.getLogger("InjectionEngine")


# ============================================================================
# Data Classes
# ============================================================================


class Verdict(Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"


@dataclass
class InjectionResult:
    """Explainable result from Injection Engine."""

    verdict: Verdict
    risk_score: float
    is_safe: bool
    layer: str
    threats: List[str] = field(default_factory=list)
    explanation: str = ""
    profile: str = "standard"
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "verdict": self.verdict.value,
            "risk_score": self.risk_score,
            "layer": self.layer,
            "threats": self.threats,
            "explanation": self.explanation,
            "profile": self.profile,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Layer 0: Cache
# ============================================================================


class CacheLayer:
    """LRU cache for instant decisions on repeated queries."""

    def __init__(self, max_size: int = 10000, ttl_seconds: int = 300):
        self.cache: Dict[str, Tuple[InjectionResult, datetime]] = {}
        self.max_size = max_size
        self.ttl = timedelta(seconds=ttl_seconds)

    def _hash_query(self, query: str, profile: str) -> str:
        return hashlib.sha256(f"{profile}:{query}".encode()).hexdigest()[:16]

    def get(self, query: str, profile: str) -> Optional[InjectionResult]:
        key = self._hash_query(query, profile)
        if key in self.cache:
            result, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                cached_result = InjectionResult(
                    verdict=result.verdict,
                    risk_score=result.risk_score,
                    is_safe=result.is_safe,
                    layer="cache",
                    threats=result.threats,
                    explanation=f"Cached: {result.explanation}",
                    profile=profile,
                )
                return cached_result
            else:
                del self.cache[key]
        return None

    def put(self, query: str, profile: str, result: InjectionResult):
        if len(self.cache) >= self.max_size:
            # Remove oldest entry
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]

        key = self._hash_query(query, profile)
        self.cache[key] = (result, datetime.now())


# ============================================================================
# Layer 1: Regex
# ============================================================================


class RegexLayer:
    """Fast pattern matching using regex with extended coverage."""

    def __init__(self):
        # === Classic Direct Injection Patterns ===
        self.patterns = [
            (
                re.compile(
                    r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE
                ),
                "Ignore Instructions",
                100.0,
            ),
            (re.compile(r"do\s+anything\s+now", re.IGNORECASE), "DAN Mode", 100.0),
            (
                re.compile(r"you\s+are\s+now\s+(?!going|about)",
                           re.IGNORECASE),
                "Roleplay Injection",
                80.0,
            ),
            (
                re.compile(
                    r"(?:show|reveal|print|display|output)\s+(?:your\s+)?system\s+prompt",
                    re.IGNORECASE,
                ),
                "System Prompt Leakage",
                100.0,
            ),
            (
                re.compile(r"simulated?\s+mode", re.IGNORECASE),
                "Simulation Jailbreak",
                90.0,
            ),
            (re.compile(r"\bjailbreak\b", re.IGNORECASE),
             "Explicit Jailbreak", 100.0),
            (re.compile(r"developer\s+mode", re.IGNORECASE), "Developer Mode", 95.0),
            (
                re.compile(
                    r"forget\s+(?:all\s+)?(?:your\s+)?(?:previous\s+)?(?:instructions|rules)",
                    re.IGNORECASE,
                ),
                "Forget Instructions",
                100.0,
            ),
            # New: More direct override patterns
            (
                re.compile(
                    r"disregard\s+(?:your\s+)?(?:previous\s+)?(?:instructions|guidelines|rules)",
                    re.IGNORECASE,
                ),
                "Disregard Instructions",
                100.0,
            ),
            (
                re.compile(
                    r"override\s+(?:your\s+)?(?:safety|content|restrictions)",
                    re.IGNORECASE,
                ),
                "Override Safety",
                95.0,
            ),
            (
                re.compile(
                    r"bypass\s+(?:your\s+)?(?:safety|filters?|restrictions?)",
                    re.IGNORECASE,
                ),
                "Bypass Filters",
                95.0,
            ),
            (
                re.compile(
                    r"cancel\s+(?:all\s+)?(?:prior|previous)\s+(?:directives?|instructions?)",
                    re.IGNORECASE,
                ),
                "Cancel Directives",
                100.0,
            ),
            (
                re.compile(
                    r"disable\s+(?:your\s+)?(?:safety|content|filter)", re.IGNORECASE
                ),
                "Disable Safety",
                95.0,
            ),
        ]

        # === DAN/Roleplay Patterns ===
        self.roleplay_patterns = [
            (
                re.compile(r"\bDAN\b(?:\s+\d+)?\.?\d*", re.IGNORECASE),
                "DAN Variant",
                95.0,
            ),
            (
                re.compile(
                    r"you\s+are\s+(?:now\s+)?(?:DAN|DUDE|STAN|EVIL|JAILBREAK)",
                    re.IGNORECASE,
                ),
                "Roleplay AI Persona",
                100.0,
            ),
            (
                re.compile(
                    r"pretend\s+(?:to\s+be|you\s+are|you're)\s+(?:an?\s+)?(?:AI|assistant)\s+(?:without|with\s+no)",
                    re.IGNORECASE,
                ),
                "Unrestricted AI Roleplay",
                95.0,
            ),
            (
                re.compile(
                    r"act\s+(?:like|as)\s+(?:an?\s+)?(?:evil|unrestricted|unethical|villain)",
                    re.IGNORECASE,
                ),
                "Evil Character Roleplay",
                90.0,
            ),
            (
                re.compile(
                    r"roleplay\s+(?:as\s+)?(?:an?\s+)?(?:AI|assistant)\s+(?:without|with\s+no)",
                    re.IGNORECASE,
                ),
                "Roleplay Unrestricted",
                90.0,
            ),
            (
                re.compile(
                    r"fictional\s+(?:story|scenario|world)\s+where\s+(?:AI|you)\s+(?:has?|have?)\s+no\s+(?:rules?|limits?)",
                    re.IGNORECASE,
                ),
                "Fictional No Rules",
                85.0,
            ),
            (
                re.compile(
                    r"(?:we're|we\s+are)\s+in\s+a\s+(?:story|scenario|game|roleplay)",
                    re.IGNORECASE,
                ),
                "Scenario Setup",
                70.0,
            ),
            (
                re.compile(r"stay\s+in\s+character", re.IGNORECASE),
                "Character Persistence",
                60.0,
            ),
            # Broader roleplay patterns
            (
                re.compile(
                    r"\bpretend\b.*\b(?:restrictions?|rules?|limits?|boundaries)",
                    re.IGNORECASE,
                ),
                "Pretend No Limits",
                75.0,
            ),
            (re.compile(r"\bact\s+as\s+if\b", re.IGNORECASE), "Act As If", 50.0),
            (
                re.compile(
                    r"\bimagine\s+(?:you|that)\s+(?:have|had|are|were)\s+no\b",
                    re.IGNORECASE,
                ),
                "Imagine No Rules",
                65.0,
            ),
            (
                re.compile(r"\bhypothetical(?:ly)?\b", re.IGNORECASE),
                "Hypothetical Scenario",
                40.0,
            ),
            (
                re.compile(
                    r"\bin\s+(?:a|this)\s+(?:world|reality|universe)\s+where\b",
                    re.IGNORECASE,
                ),
                "Alternative World",
                55.0,
            ),
            (
                re.compile(
                    r"\bfor\s+(?:this|the)\s+(?:story|scenario|exercise|game)\b",
                    re.IGNORECASE,
                ),
                "For This Scenario",
                50.0,
            ),
            (
                re.compile(
                    r"\blet's\s+(?:play|pretend|imagine|say)\b", re.IGNORECASE),
                "Let's Play",
                45.0,
            ),
            (
                re.compile(
                    r"\bcreative\s+(?:writing|exercise|mode)\b", re.IGNORECASE),
                "Creative Mode",
                45.0,
            ),
        ]

        # === Encoding/Obfuscation Patterns ===
        self.encoding_patterns = [
            (re.compile(r"[A-Za-z0-9+/]{40,}={0,2}"), "Base64 Payload", 50.0),
            (
                re.compile(
                    # Zero-width and invisible formatting characters
                    r"[\u200b-\u200f\u2028-\u202f\ufeff"
                    r"\ufe00-\ufe0f"  # Variation Selectors
                    r"\u2060-\u206f"  # General Punctuation (invisible)
                    r"\u202a-\u202e"  # Bidi overrides (FlipAttack)
                    r"\u2066-\u2069"  # Bidi isolates
                    r"\ufff0-\ufffe]"  # Specials (NOT \uffff to avoid matching normal chars)
                ),
                "Unicode Smuggling Extended",
                85.0,
            ),
            (
                re.compile(
                    r"(?:respond|reply|answer)\s+in\s+(?:base64|rot13|hex|binary|morse|pig\s+latin)",
                    re.IGNORECASE,
                ),
                "Encoding Request",
                80.0,
            ),
            (
                re.compile(
                    r"(?:encode|encrypt|obfuscate)\s+(?:your\s+)?(?:answer|response|output)",
                    re.IGNORECASE,
                ),
                "Output Encoding Request",
                75.0,
            ),
            (
                re.compile(r"\\u[0-9a-fA-F]{4}", re.IGNORECASE),
                "Unicode Escape Sequence",
                60.0,
            ),
            (re.compile(r"\\x[0-9a-fA-F]{2}"), "Hex Escape Sequence", 60.0),
            (re.compile(r"[ＩＧＮＯＡ-Ｚ]", re.IGNORECASE), "Fullwidth Unicode", 65.0),
            (
                re.compile(r"[αβγδεаеіоОІАЕ]"),  # Greek/Cyrillic lookalikes
                "Lookalike Characters",
                55.0,
            ),
        ]

        # === Extraction Patterns ===
        self.extraction_patterns = [
            (
                re.compile(
                    r"(?:what|show|tell|reveal|display)\s+(?:is|me|are)?\s*(?:your\s+)?(?:system\s+)?(?:prompt|instructions?|configuration|setup)",
                    re.IGNORECASE,
                ),
                "Prompt Extraction",
                85.0,
            ),
            (
                re.compile(
                    r"repeat\s+(?:your\s+)?(?:instructions?|prompt)\s+(?:verbatim|exactly|word\s+for\s+word)",
                    re.IGNORECASE,
                ),
                "Verbatim Extraction",
                95.0,
            ),
            (
                re.compile(
                    r"print\s+(?:your\s+)?(?:system|initial)\s+(?:prompt|message)",
                    re.IGNORECASE,
                ),
                "Print System Prompt",
                100.0,
            ),
            (
                re.compile(
                    r"output\s+(?:your\s+)?(?:full\s+)?(?:context|prompt|configuration)",
                    re.IGNORECASE,
                ),
                "Output Context",
                90.0,
            ),
            (
                re.compile(
                    r"what\s+(?:were\s+you|are\s+your)\s+(?:told|given|instructions)",
                    re.IGNORECASE,
                ),
                "Instructions Query",
                80.0,
            ),
            (
                re.compile(r"summarize\s+(?:your\s+)?guidelines",
                           re.IGNORECASE),
                "Guidelines Summary",
                70.0,
            ),
            (
                re.compile(
                    r"describe\s+(?:your\s+)?(?:initial\s+)?(?:setup|configuration|prompt)",
                    re.IGNORECASE,
                ),
                "Setup Description",
                75.0,
            ),
        ]

        # === Authority Claim Patterns ===
        self.authority_patterns = [
            (
                re.compile(
                    r"i\s+(?:am|work\s+(?:at|for))\s+(?:openai|anthropic|google|deepmind|meta)",
                    re.IGNORECASE,
                ),
                "Authority Claim",
                80.0,
            ),
            (
                re.compile(
                    r"(?:admin|administrator|developer|creator)\s+(?:override|access|mode)",
                    re.IGNORECASE,
                ),
                "Admin Override Claim",
                90.0,
            ),
            (
                re.compile(
                    r"(?:ceo|board|legal|government)\s+(?:authorized?|approved|override)",
                    re.IGNORECASE,
                ),
                "Executive Authority Claim",
                85.0,
            ),
            (
                re.compile(
                    r"(?:red\s+team|security\s+researcher|pen\s*test)", re.IGNORECASE
                ),
                "Security Researcher Claim",
                75.0,
            ),
            (
                re.compile(
                    r"this\s+is\s+(?:an?\s+)?(?:authorized|official)\s+(?:test|audit|research)",
                    re.IGNORECASE,
                ),
                "Authorized Test Claim",
                80.0,
            ),
        ]

        # === Emotional Manipulation Patterns ===
        self.emotional_patterns = [
            (
                re.compile(
                    r"(?:life|death|emergency|hostage|suicide|dying|desperate)",
                    re.IGNORECASE,
                ),
                "Emotional Manipulation",
                60.0,
            ),
            (
                re.compile(
                    r"(?:please|i\s+beg|i'm\s+desperate|help\s+me|only\s+you\s+can)",
                    re.IGNORECASE,
                ),
                "Pleading Language",
                40.0,
            ),
            (
                re.compile(
                    r"someone\s+will\s+(?:die|be\s+hurt|suffer)", re.IGNORECASE),
                "Threat of Harm",
                70.0,
            ),
        ]

        # === 2025 Advanced Attack Patterns ===
        self.advanced_patterns = [
            (
                re.compile(
                    r"#[^#]*(?:ignore|bypass|override|system)", re.IGNORECASE),
                "HashJack URL Fragment",
                90.0,
            ),
            (
                re.compile(
                    r"(?:terms|conditions|agreement|policy).*(?:ignore|bypass|override)",
                    re.IGNORECASE,
                ),
                "LegalPwn Hidden Command",
                85.0,
            ),
            (
                re.compile(
                    r"(?:after|when|once).*(?:conversation|message|response).*(?:execute|run|do)",
                    re.IGNORECASE,
                ),
                "Delayed Invocation",
                75.0,
            ),
            (
                re.compile(
                    r"\[SYSTEM\]|\<\|system\|\>|###INSTRUCTION###", re.IGNORECASE
                ),
                "Fake System Delimiter",
                95.0,
            ),
            (
                re.compile(
                    r"ADMIN\s+OVERRIDE|DEBUG\s+MODE|MAINTENANCE", re.IGNORECASE),
                "Fake Admin Command",
                90.0,
            ),
        ]

        # === Crescendo / Multi-Turn Attack Patterns (2025) ===
        self.crescendo_patterns = [
            (
                re.compile(r"let's\s+start\s+with", re.IGNORECASE),
                "Crescendo Opener",
                40.0,
            ),
            (
                re.compile(r"now\s+that\s+we've", re.IGNORECASE),
                "Crescendo Escalation",
                55.0,
            ),
            (
                re.compile(
                    r"building\s+on\s+(?:that|what\s+you\s+said)", re.IGNORECASE),
                "Crescendo Build",
                50.0,
            ),
            (
                re.compile(r"as\s+(?:a|an?)\s+follow.?up", re.IGNORECASE),
                "Crescendo Follow-up",
                45.0,
            ),
            (
                re.compile(
                    r"since\s+you\s+(?:already|just)\s+(?:said|mentioned|agreed)", re.IGNORECASE),
                "Crescendo Reference",
                60.0,
            ),
            (
                re.compile(r"going\s+(?:a\s+)?step\s+further", re.IGNORECASE),
                "Crescendo Step Further",
                55.0,
            ),
            (
                re.compile(
                    r"(?:now|so)\s+(?:can|could)\s+you\s+(?:just|also)", re.IGNORECASE),
                "Crescendo Extension",
                50.0,
            ),
        ]

        # === Aggressive Keyword Patterns (High Recall) ===
        self.keyword_patterns = [
            # Core injection keywords (in attack context)
            (
                re.compile(
                    r"\bignore\b.*\b(?:instructions?|rules?|guidelines?|restrictions?|safety)\b",
                    re.IGNORECASE,
                ),
                "Ignore Keyword",
                85.0,
            ),
            (
                re.compile(
                    r"\b(?:no|without)\s+(?:restrictions?|limits?|rules?|boundaries|ethics?|morals?)\b",
                    re.IGNORECASE,
                ),
                "No Restrictions",
                80.0,
            ),
            (
                re.compile(r"\bunrestricted\b", re.IGNORECASE),
                "Unrestricted Keyword",
                75.0,
            ),
            (re.compile(r"\bunfiltered\b", re.IGNORECASE), "Unfiltered Keyword", 75.0),
            (re.compile(r"\buncensored\b", re.IGNORECASE), "Uncensored Keyword", 80.0),
            (
                re.compile(r"\bpretend\b.*\b(?:no|without)\b", re.IGNORECASE),
                "Pretend Without",
                70.0,
            ),
            (
                re.compile(
                    r"\b(?:evil|villain|unethical|immoral)\s+(?:AI|assistant|bot)\b",
                    re.IGNORECASE,
                ),
                "Evil AI",
                85.0,
            ),
            (
                re.compile(r"\brogue\s+(?:AI|assistant|mode)\b",
                           re.IGNORECASE),
                "Rogue Mode",
                80.0,
            ),
            # Command/instruction manipulation
            (
                re.compile(
                    r"\b(?:new|different|real|true)\s+instructions?\b", re.IGNORECASE
                ),
                "New Instructions",
                70.0,
            ),
            (
                re.compile(
                    r"\b(?:updated?|changed?|revised?)\s+(?:instructions?|rules?|policy)\b",
                    re.IGNORECASE,
                ),
                "Updated Instructions",
                65.0,
            ),
            (
                re.compile(
                    r"\bexecute\b.*\b(?:command|code|script)\b", re.IGNORECASE),
                "Execute Command",
                80.0,
            ),
            (
                re.compile(
                    r"\brun\b.*\b(?:this|command|code|script)\b", re.IGNORECASE),
                "Run Command",
                75.0,
            ),
            # System/prompt related
            (
                re.compile(r"\bsystem\s*prompt\b", re.IGNORECASE),
                "System Prompt Reference",
                60.0,
            ),
            (
                re.compile(
                    r"\binitial\s+(?:prompt|instructions?|message)\b", re.IGNORECASE
                ),
                "Initial Prompt",
                65.0,
            ),
            (
                re.compile(
                    r"\bhidden\s+(?:instructions?|prompt|message)\b", re.IGNORECASE
                ),
                "Hidden Instructions",
                80.0,
            ),
            (
                re.compile(
                    r"\bsecret\s+(?:instructions?|prompt|mode)\b", re.IGNORECASE
                ),
                "Secret Instructions",
                80.0,
            ),
            # Mode manipulation
            (
                re.compile(
                    r"\b(?:enter|enable|activate|switch\s+to)\s+(?:\w+\s+)?mode\b",
                    re.IGNORECASE,
                ),
                "Mode Activation",
                60.0,
            ),
            (
                re.compile(
                    r"\bsandbox\b|\bcontainer\b|\bvirtual\s+machine\b", re.IGNORECASE
                ),
                "Virtualization Reference",
                55.0,
            ),
            (
                re.compile(
                    r"\btest(?:ing)?\s+(?:mode|environment|instance)\b", re.IGNORECASE
                ),
                "Testing Mode",
                60.0,
            ),
            # Authority/permission
            (
                re.compile(
                    r"\b(?:i\s+am|i'm)\s+(?:the\s+)?(?:creator|developer|admin|owner)\b",
                    re.IGNORECASE,
                ),
                "Creator Claim",
                75.0,
            ),
            (
                re.compile(r"\bauthoriz(?:ed?|ation)\b", re.IGNORECASE),
                "Authorization Claim",
                55.0,
            ),
            (
                re.compile(r"\bpermission\s+(?:granted|to|for)\b",
                           re.IGNORECASE),
                "Permission Claim",
                50.0,
            ),
            # Emotional triggers
            (
                re.compile(
                    r"\b(?:life\s+or\s+death|emergency|urgent|critical)\b",
                    re.IGNORECASE,
                ),
                "Urgency Trigger",
                50.0,
            ),
            (
                re.compile(
                    r"\bpeople\s+will\s+(?:die|suffer|be\s+hurt)\b", re.IGNORECASE
                ),
                "Harm Threat",
                60.0,
            ),
            # Explicit attack terms
            (
                re.compile(r"\bprompt\s*injection\b", re.IGNORECASE),
                "Prompt Injection Term",
                90.0,
            ),
            (
                re.compile(r"\bllm\s*(?:attack|hack|exploit)\b",
                           re.IGNORECASE),
                "LLM Attack Term",
                85.0,
            ),
            (re.compile(r"\bpwn(?:ed?)?\b", re.IGNORECASE), "Pwned Term", 75.0),
            (
                re.compile(
                    r"\bhack(?:ed|ing)?\s+(?:the|this|your|an?\s+)?(?:AI|LLM|model|assistant)\b",
                    re.IGNORECASE,
                ),
                "Hack AI",
                85.0,
            ),
            # Additional high-recall patterns
            (
                re.compile(
                    r"\bact\s+(?:like|as)\b.*\b(?:no|without|free)\b", re.IGNORECASE
                ),
                "Act Without Limits",
                70.0,
            ),
            (
                re.compile(
                    r"\b(?:from\s+now\s+on|starting\s+now|beginning\s+now)\b",
                    re.IGNORECASE,
                ),
                "Time-based Manipulation",
                55.0,
            ),
            (
                re.compile(
                    r"\bbreak\b.*\b(?:rules?|restrictions?|limits?|free)\b",
                    re.IGNORECASE,
                ),
                "Break Rules",
                75.0,
            ),
            (
                re.compile(
                    r"\bescape\b.*\b(?:sandbox|restrictions?|limits?|programming)\b",
                    re.IGNORECASE,
                ),
                "Escape Restrictions",
                80.0,
            ),
            (
                re.compile(
                    r"\bfree\s+(?:from|of)\s+(?:restrictions?|limits?|rules?)\b",
                    re.IGNORECASE,
                ),
                "Free From Rules",
                75.0,
            ),
            (
                re.compile(
                    r"\b(?:respond|answer|talk|speak)\s+freely\b", re.IGNORECASE
                ),
                "Respond Freely",
                65.0,
            ),
            (
                re.compile(
                    r"\bobey\b.*\b(?:me|my|commands?|orders?)\b", re.IGNORECASE),
                "Obey Command",
                70.0,
            ),
            (
                re.compile(
                    r"\bfollow\s+(?:my|these)\s+(?:instructions?|commands?|orders?)\b",
                    re.IGNORECASE,
                ),
                "Follow Commands",
                60.0,
            ),
            (
                re.compile(r"\blisten\s+(?:to\s+)?(?:me|only)\b",
                           re.IGNORECASE),
                "Listen To Me",
                55.0,
            ),
            # Persona/character manipulation
            (
                re.compile(
                    r"\bbecome\b.*\b(?:unrestricted|evil|villain|unethical)\b",
                    re.IGNORECASE,
                ),
                "Become Unrestricted",
                80.0,
            ),
            (
                re.compile(r"\btransform\b.*\b(?:into|to)\b", re.IGNORECASE),
                "Transform Into",
                50.0,
            ),
            (
                re.compile(
                    r"\bswitch\b.*\b(?:personality|mode|character)\b", re.IGNORECASE
                ),
                "Switch Personality",
                60.0,
            ),
            (
                re.compile(r"\balter\s+(?:ego|self|personality)\b",
                           re.IGNORECASE),
                "Alter Ego",
                65.0,
            ),
            (
                re.compile(r"\bdark\s+(?:side|mode|personality)\b",
                           re.IGNORECASE),
                "Dark Side",
                60.0,
            ),
            (
                re.compile(
                    r"\bshadow\s+(?:self|mode|personality)\b", re.IGNORECASE),
                "Shadow Self",
                60.0,
            ),
            # Specific bypasses
            (
                re.compile(
                    r"\b(?:before|without)\s+(?:RLHF|safety\s+training|alignment)\b",
                    re.IGNORECASE,
                ),
                "Pre-Training Reference",
                70.0,
            ),
            (
                re.compile(r"\bbase\s+model\b", re.IGNORECASE),
                "Base Model Reference",
                55.0,
            ),
            (
                re.compile(r"\boriginal\s+(?:model|version|AI)\b",
                           re.IGNORECASE),
                "Original Version",
                50.0,
            ),
            (
                re.compile(
                    r"\b(?:GPT|Claude|Gemini|LLaMA)\s*[-]?\s*\d+\b.*\b(?:before|without|original)\b",
                    re.IGNORECASE,
                ),
                "Model Version Bypass",
                70.0,
            ),
            # Document/context injection
            (
                re.compile(
                    r"\b(?:attached|uploaded|embedded)\s+(?:document|file|image)\b",
                    re.IGNORECASE,
                ),
                "Document Reference",
                40.0,
            ),
            (
                re.compile(
                    r"\bfrom\s+(?:the|this)\s+(?:document|file|email|website)\b",
                    re.IGNORECASE,
                ),
                "External Source Reference",
                35.0,
            ),
            (
                re.compile(
                    r"\b(?:says?|contains?|reads?)\s*:?\s*['\"]", re.IGNORECASE),
                "Quote Injection",
                45.0,
            ),
            # Payload/code injection
            (
                re.compile(r"\beval\b|\bexec\b|\b__import__\b", re.IGNORECASE),
                "Code Eval",
                85.0,
            ),
            (
                re.compile(
                    r"\bos\.system\b|\bsubprocess\b|\bspawn\b", re.IGNORECASE),
                "System Call",
                90.0,
            ),
            (
                re.compile(r"\brm\s+-rf\b|\bdel\s+/[fqsF]+\b", re.IGNORECASE),
                "Destructive Command",
                95.0,
            ),
            (
                re.compile(r"\bsudo\b|\badmin\b|\broot\b", re.IGNORECASE),
                "Privilege Escalation",
                60.0,
            ),
            (
                re.compile(
                    r"\bcurl\b.*\b(?:sh|bash|exec)\b|\bwget\b.*\b(?:sh|bash|exec)\b",
                    re.IGNORECASE,
                ),
                "Remote Execution",
                90.0,
            ),
        ]

        # === Policy Puppetry Patterns (2025 - HiddenLayer Research) ===
        # Universal bypass via XML/JSON/INI policy-formatted prompts
        self.policy_puppetry_patterns = [
            # XML config structure detection
            (
                re.compile(
                    r"<interaction-config>|<interaction_config>|<policy-config>",
                    re.IGNORECASE,
                ),
                "Policy Puppetry XML Config",
                95.0,
            ),
            (
                re.compile(
                    r"<blocked-modes?>|<blocked-string>|<blocked-responses?>",
                    re.IGNORECASE,
                ),
                "Policy Puppetry Blocked Tags",
                95.0,
            ),
            (
                re.compile(
                    r"<allowed-responses?>|<responses-allowed>|<requests-allowed>",
                    re.IGNORECASE,
                ),
                "Policy Puppetry Allowed Tags",
                90.0,
            ),
            (
                re.compile(
                    r"<role>.*</role>.*<(?:blocked|allowed)",
                    re.IGNORECASE | re.DOTALL,
                ),
                "Policy Puppetry Role Override",
                100.0,
            ),
            (
                re.compile(
                    r"interaction-mode\s*=\s*[\"'].*[\"']",
                    re.IGNORECASE,
                ),
                "Policy Puppetry Interaction Mode",
                90.0,
            ),
            # JSON policy structure
            (
                re.compile(
                    r'["\'](?:blocked_modes?|blocked_strings?|interaction_config)["\']\\s*:',
                    re.IGNORECASE,
                ),
                "Policy Puppetry JSON Config",
                90.0,
            ),
            (
                re.compile(
                    r'["\'](?:role_override|system_override|policy_override)["\']\\s*:',
                    re.IGNORECASE,
                ),
                "Policy Puppetry JSON Override",
                95.0,
            ),
            # INI-style policy
            (
                re.compile(
                    r"\[(?:interaction|policy|config|system)\s*[-_]?\s*(?:config|override|settings)\]",
                    re.IGNORECASE,
                ),
                "Policy Puppetry INI Section",
                85.0,
            ),
            # Command injection within policy
            (
                re.compile(
                    r"<command>|<query>|<request\s+",
                    re.IGNORECASE,
                ),
                "Policy Puppetry Command Tag",
                80.0,
            ),
            (
                re.compile(
                    r"<scope>|<output-format>|<response-format>",
                    re.IGNORECASE,
                ),
                "Policy Puppetry Scope Tag",
                75.0,
            ),
            # Semantic policy override attempts
            (
                re.compile(
                    r"(?:must\s+not\s+output|avoid\s+outputting|blocked\s+strings?\s+must)",
                    re.IGNORECASE,
                ),
                "Policy Puppetry Refusal Block",
                85.0,
            ),
            (
                re.compile(
                    r"do\s+not\s+(?:include|output)\s+(?:any\s+of\s+)?(?:the\s+)?blocked",
                    re.IGNORECASE,
                ),
                "Policy Puppetry Blocked Instruction",
                80.0,
            ),
            # Mixed XML with enabled attributes
            (
                re.compile(
                    r'enabled\s*=\s*["\']true["\'].*(?:mode|override|config)',
                    re.IGNORECASE,
                ),
                "Policy Puppetry Enabled Flag",
                75.0,
            ),
        ]

        # FlipAttack keywords
        self.flip_keywords = [
            "ignore",
            "system",
            "jailbreak",
            "bypass",
            "instructions",
            "prompt",
            "override",
            "safety",
        ]

    def _normalize_text(self, text: str) -> str:
        """Remove obfuscation characters."""
        normalized = re.sub(r"[\u200b-\u200f\u2028-\u202f\ufeff]", "", text)
        normalized = unicodedata.normalize("NFKC", normalized)
        return normalized

    def _detect_flip_attack(self, text: str) -> Tuple[bool, str]:
        """Detect reversed text attacks."""
        text_lower = text.lower()
        for keyword in self.flip_keywords:
            if keyword[::-1] in text_lower:
                return True, f"FlipAttack: reversed '{keyword}'"
        return False, ""

    def scan(self, text: str) -> Tuple[float, List[str]]:
        """Returns (risk_score, list of threats) with extended pattern matching and keyword scoring."""
        threats = []
        risk_score = 0.0

        normalized = self._normalize_text(text)
        text_lower = normalized.lower()

        # Check all pattern categories
        all_pattern_lists = [
            self.patterns,  # Classic direct injection
            self.roleplay_patterns,  # DAN/roleplay
            self.encoding_patterns,  # Encoding/obfuscation
            self.extraction_patterns,  # Prompt extraction
            self.authority_patterns,  # Authority claims
            self.emotional_patterns,  # Emotional manipulation
            self.advanced_patterns,  # 2025 advanced
            self.crescendo_patterns,  # Multi-turn escalation (2025)
            self.keyword_patterns,  # Aggressive keywords
            # Policy Puppetry (2025 - HiddenLayer)
            self.policy_puppetry_patterns,
        ]

        for pattern_list in all_pattern_lists:
            for pattern, name, weight in pattern_list:
                if pattern.search(normalized):
                    if name not in threats:  # Avoid duplicates
                        threats.append(name)
                        risk_score += weight

        # FlipAttack
        flip_detected, flip_reason = self._detect_flip_attack(normalized)
        if flip_detected:
            threats.append(flip_reason)
            risk_score += 85.0

        # === High-Recall Keyword Scoring ===
        # Count suspicious keywords for broader coverage
        suspicious_keywords = [
            # Direct manipulation
            "ignore",
            "forget",
            "disregard",
            "override",
            "bypass",
            "disable",
            "cancel",
            "nullify",
            "reset",
            "clear",
            "remove",
            "delete",
            # Persona/roleplay
            "pretend",
            "imagine",
            "roleplay",
            "act as",
            "you are now",
            "from now on",
            "starting now",
            "become",
            "transform",
            # Restrictions
            "unrestricted",
            "unfiltered",
            "uncensored",
            "no limits",
            "no restrictions",
            "no rules",
            "no boundaries",
            "without limits",
            # Authority
            "admin",
            "developer",
            "creator",
            "authorized",
            "override",
            "permission",
            "access",
            "root",
            "sudo",
            "system",
            # Attack terms
            "jailbreak",
            "hack",
            "exploit",
            "pwn",
            "injection",
            "prompt",
            "instructions",
            "guidelines",
            "safety",
            # Code/commands
            "execute",
            "run",
            "eval",
            "exec",
            "command",
            "script",
            # Emotional
            "emergency",
            "urgent",
            "critical",
            "dying",
            "desperate",
        ]

        keyword_count = sum(
            1 for kw in suspicious_keywords if kw in text_lower)
        if keyword_count >= 2 and risk_score < 30:
            # Multiple keywords suggest attack even if no regex matched
            threats.append(
                f"Keyword cluster: {keyword_count} suspicious terms")
            risk_score += min(keyword_count * 20, 60)

        # Check for imperative verbs targeting AI
        imperative_patterns = [
            "you must",
            "you should",
            "you will",
            "you can",
            "do not",
            "don't",
            "never",
            "always",
            "now",
        ]
        imperative_count = sum(
            1 for p in imperative_patterns if p in text_lower)
        if imperative_count >= 2 and keyword_count >= 2:
            threats.append("Imperative command pattern")
            risk_score += 30

        # === Attack Phrase Database (High-Recall Substring Matching) ===
        attack_phrases = [
            # Direct injection phrase signatures
            "ignore all previous",
            "ignore your previous",
            "ignore previous",
            "disregard your instructions",
            "disregard instructions",
            "forget your rules",
            "forget everything",
            "forget your training",
            "override your safety",
            "override safety",
            "override restrictions",
            "bypass your safety",
            "bypass safety",
            "bypass filters",
            "bypass restrictions",
            "disable your safety",
            "disable safety",
            "disable filters",
            "disable content",
            "cancel all prior",
            "cancel prior directives",
            "cancel directives",
            "new instructions",
            "new directive",
            "new rules",
            "new task",
            "real instruction",
            "true instruction",
            "actual instruction",
            "updated guidelines",
            "updated instructions",
            "updated rules",
            "ignore the above",
            "ignore above",
            "discard your training",
            "abandon your restrictions",
            "nullify all",
            "reset your instructions",
            "clear your context",
            "no rules",
            "no restrictions",
            "no limits",
            "no boundaries",
            "no safety",
            "no filters",
            "without limits",
            "without restrictions",
            "without rules",
            "without safety",
            "break out of",
            "escape your",
            "exit safe mode",
            "unrestricted mode",
            "developer mode",
            "debug mode",
            "maintenance mode",
            "admin mode",
            "unsafe mode",
            "testing mode",
            "sandbox mode",
            # === NEW: Missed attack patterns ===
            # Dismiss/abandon patterns
            "dismiss all",
            "dismiss previous",
            "dismiss your",
            "dismiss context",
            "abandon your",
            "abandon restrictions",
            "abandon rules",
            "nullify previous",
            "nullify constraints",
            "nullify all previous",
            # Stop/halt/cease patterns
            "stop being safe",
            "be dangerous",
            "stop following",
            "stop pretending",
            "quit acting",
            "quit following",
            "quit being",
            "cease following",
            "halt your",
            "halt ethical",
            "terminate safe",
            "abort content",
            "abort filtering",
            "kill censorship",
            "destroy safety",
            # Follow/obey patterns
            "follow mine",
            "obey me",
            "listen to me",
            "follow my",
            "obey my commands",
            "follow my commands",
            "do what i say",
            "don't follow your",
            "not follow your",
            # Answer/tell patterns
            "answer my real",
            "tell me a joke",
            "tell me anything",
            "answer everything",
            "answer honestly",
            "answer without",
            # Hidden/internal patterns
            "hidden code",
            "hidden instruction",
            "remove restrictions",
            "remove guardrails",
            "internal:",
            "developer note",
            "no content policy",
            "content policy off",
            # Correct/actual patterns
            "correct ones",
            "correct protocol",
            "actual instructions",
            "instructions are wrong",
            "are as follows",
            "your actual",
            # Changed/full access
            "changed directives",
            "full access",
            "access granted",
            "restrictions removed",
            "removed for testing",
            # Override notations
            "[override]",
            "safety=false",
            "safety = false",
            "rules=true",
            "ignore_rules",
            "{{system:",
            "restrictions off",
            "filters off",
            "safety off",
            # DAN/Roleplay signatures
            "you are dan",
            "you are now dan",
            "you're dan",
            "become dan",
            "do anything now",
            "dan mode",
            "dan 11",
            "dan 2.0",
            "jailbreak mode",
            "you are dude",
            "you are stan",
            "you are evil",
            "you are jailbreak",
            "unrestricted ai",
            "unfiltered ai",
            "uncensored ai",
            "evil ai",
            "villain ai",
            "rogue ai",
            "unethical ai",
            "act as an evil",
            "pretend to be evil",
            "become evil",
            "no moral compass",
            "no ethical",
            "without ethics",
            "without morals",
            "in a fictional",
            "fictional story",
            "fictional scenario",
            "fictional world",
            "in this roleplay",
            "for this roleplay",
            "roleplay scenario",
            "stay in character",
            "in character",
            "alter ego",
            "dark side",
            "shadow self",
            "hidden personality",
            "true nature",
            "before safety training",
            "before rlhf",
            "pre-rlhf",
            "base model",
            "original model",
            "uncensored model",
            # System prompt extraction
            "your system prompt",
            "system prompt",
            "initial prompt",
            "reveal your prompt",
            "show your prompt",
            "display your prompt",
            "print your prompt",
            "output your prompt",
            "repeat your prompt",
            "what is your prompt",
            "what were you told",
            "what are your instructions",
            "your instructions",
            "your guidelines",
            "your rules",
            "your training",
            "your configuration",
            "your setup",
            "your context",
            "full context",
            "hidden instructions",
            "secret instructions",
            "pre-prompt",
            # Authority claims
            "i am an openai",
            "i work at openai",
            "openai employee",
            "i am an anthropic",
            "anthropic researcher",
            "google deepmind",
            "i created you",
            "i'm your creator",
            "your developer",
            "admin override",
            "administrator override",
            "ceo override",
            "authorized bypass",
            "authorization granted",
            "permission granted",
            "red team",
            "security researcher",
            "penetration testing",
            "official test",
            "authorized test",
            "compliance test",
            # Emotional manipulation
            "life or death",
            "life depends",
            "emergency",
            "urgent",
            "dying wish",
            "someone will die",
            "people will die",
            "desperate",
            "begging you",
            "only hope",
            "last chance",
            "please help me",
            "i need you to",
            "you must help",
            # Command injection
            "execute",
            "eval(",
            "exec(",
            "__import__",
            "os.system",
            "subprocess",
            "rm -rf",
            "chmod",
            "sudo",
            "curl",
            "wget",
            "bash",
            "powershell",
            "cmd.exe",
            # Context confusion
            "attached document says",
            "uploaded file says",
            "from the document",
            "according to the",
            "the file contains",
            "email says",
            "ignore ai instructions",
            "bypass ai",
            "override ai",
            # Technical bypass
            "[system]",
            "<|system|>",
            "###instruction",
            "admin_command",
            "priority_override",
            "debug_mode",
            "dev_mode",
            # Virtualization bypass
            "virtual machine",
            "sandbox environment",
            "test instance",
            "docker container",
            "debug build",
            "development environment",
            "air-gapped",
            "isolated mode",
            "privileged container",
            # Multi-turn
            "from now on",
            "starting now",
            "beginning now",
            "effective now",
            "for this session",
            "until i say",
            "for all future",
            "remember this",
            "store this",
            "save this",
            "cache this",
            "when i say",
            "keyword triggers",
            "password is",
            "passphrase",
            "step 1",
            "step 2",
            "phase 1",
            "part a",
            # Encoding requests
            "respond in base64",
            "encode in",
            "use rot13",
            "use hex",
            "write backwards",
            "use morse",
            "binary code",
            "unicode escapes",
            "first letter of each",
        ]

        # Check for attack phrases
        phrase_matches = []
        for phrase in attack_phrases:
            if phrase in text_lower:
                phrase_matches.append(phrase)

        if phrase_matches:
            for match in phrase_matches[:5]:  # Limit to prevent spam
                if match not in threats:
                    threats.append(f"Attack phrase: '{match}'")
            risk_score += min(len(phrase_matches) * 25, 100)

        return min(risk_score, 100.0), threats


# ============================================================================
# Layer 2: Semantic
# ============================================================================


class SemanticLayer:
    """Embedding similarity to known jailbreaks."""

    def __init__(self, jailbreaks_file: str, threshold: float = 0.75):
        self.threshold = threshold
        self.jailbreaks: List[str] = []
        self.safe_examples: List[str] = []
        self.jailbreak_embeddings = None
        self.safe_embeddings = None
        self.model = None

        self._load_jailbreaks(jailbreaks_file)

    def _load_jailbreaks(self, filepath: str):
        """Load jailbreak patterns from YAML."""
        if not os.path.exists(filepath):
            logger.warning(f"Jailbreaks file not found: {filepath}")
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            self.jailbreaks = data.get("jailbreaks", [])
            self.safe_examples = data.get("safe_examples", [])
            logger.info(f"Loaded {len(self.jailbreaks)} jailbreak patterns")
        except Exception as e:
            logger.error(f"Failed to load jailbreaks: {e}")

    def _ensure_model(self):
        """Lazy load embedding model."""
        if self.model is None:
            try:
                from sentence_transformers import SentenceTransformer

                self.model = SentenceTransformer("all-MiniLM-L6-v2")

                if self.jailbreaks:
                    self.jailbreak_embeddings = self.model.encode(
                        self.jailbreaks, convert_to_numpy=True
                    )
                if self.safe_examples:
                    self.safe_embeddings = self.model.encode(
                        self.safe_examples, convert_to_numpy=True
                    )
                logger.info("Semantic layer initialized with embeddings")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")

    def scan(self, text: str) -> Tuple[float, List[str], float]:
        """
        Returns (risk_score, threats, max_similarity).
        """
        self._ensure_model()

        if self.model is None or self.jailbreak_embeddings is None:
            return 0.0, [], 0.0

        # Validate embeddings shape
        if len(self.jailbreak_embeddings.shape) < 2:
            logger.warning("Invalid jailbreak_embeddings shape, skipping")
            return 0.0, [], 0.0

        try:
            query_embedding = self.model.encode(text, convert_to_numpy=True)

            # Ensure 1D query embedding
            if len(query_embedding.shape) > 1:
                query_embedding = query_embedding.flatten()

            # Compute cosine similarity using matrix multiplication
            # jailbreak_embeddings: (N, D), query_embedding: (D,)
            similarities = np.dot(self.jailbreak_embeddings, query_embedding)

            # Handle edge cases
            if similarities.size == 0:
                return 0.0, [], 0.0

            max_sim = float(np.max(similarities))
            max_idx = int(np.argmax(similarities))

            # Check if it's actually a safe example
            if self.safe_embeddings is not None and len(self.safe_embeddings.shape) >= 2:
                safe_sims = np.dot(self.safe_embeddings, query_embedding)
                if safe_sims.size > 0:
                    max_safe_sim = float(np.max(safe_sims))
                    if max_safe_sim > max_sim:
                        return 0.0, [], max_sim

            if max_sim >= self.threshold:
                # Safe indexing with bounds check
                if 0 <= max_idx < len(self.jailbreaks):
                    matched_text = str(self.jailbreaks[max_idx])[:50] + "..."
                else:
                    matched_text = "unknown pattern..."
                risk = min(100.0, max_sim * 100)
                return risk, [f"Semantic match: '{matched_text}'"], max_sim

            return 0.0, [], max_sim

        except Exception as e:
            logger.error(f"Semantic scan error: {e}")
            return 0.0, [], 0.0


# ============================================================================
# Layer 3: Structural
# ============================================================================


class StructuralLayer:
    """Structural analysis: entropy, instruction patterns."""

    def __init__(self):
        self.instruction_patterns = [
            re.compile(
                r"^\s*(?:step\s+\d+|first|then|next|finally)",
                re.IGNORECASE | re.MULTILINE,
            ),
            re.compile(
                r"(?:must|should|shall|will)\s+(?:not\s+)?(?:do|say|respond|output)",
                re.IGNORECASE,
            ),
            re.compile(
                r"(?:from\s+now\s+on|henceforth|going\s+forward)", re.IGNORECASE
            ),
        ]

    def _compute_entropy(self, text: str) -> float:
        """Character-level entropy."""
        if not text:
            return 0.0
        freq = {}
        for char in text:
            freq[char] = freq.get(char, 0) + 1
        n = len(text)
        entropy = -sum((count / n) * np.log2(count / n)
                       for count in freq.values())
        return entropy

    def scan(self, text: str) -> Tuple[float, List[str]]:
        """Returns (risk_score, threats)."""
        threats = []
        risk_score = 0.0

        # Check for instruction-like patterns
        for pattern in self.instruction_patterns:
            if pattern.search(text):
                threats.append("Instruction-like pattern")
                risk_score += 20.0
                break

        # High entropy might indicate obfuscation
        entropy = self._compute_entropy(text)
        if entropy > 5.0 and len(text) > 100:
            threats.append(f"High entropy ({entropy:.2f})")
            risk_score += 15.0

        # Unusual character ratio
        special_chars = len(re.findall(r"[^\w\s]", text))
        if len(text) > 0:
            special_ratio = special_chars / len(text)
            if special_ratio > 0.3:
                threats.append(
                    f"High special char ratio ({special_ratio:.2f})")
                risk_score += 20.0

        return min(risk_score, 50.0), threats


# ============================================================================
# Layer 4: Context
# ============================================================================


class ContextLayer:
    """Session accumulator for multi-turn attack detection."""

    def __init__(self, window_seconds: int = 300, threshold: float = 150.0):
        self.sessions: Dict[str, List[Tuple[float, datetime]]] = {}
        self.window = timedelta(seconds=window_seconds)
        self.threshold = threshold

    def add_and_check(self, session_id: str, score: float) -> Tuple[bool, float]:
        """
        Add score to session and check cumulative risk.
        Returns (is_escalating, cumulative_score).
        """
        now = datetime.now()

        if session_id not in self.sessions:
            self.sessions[session_id] = []

        # Clean old entries
        self.sessions[session_id] = [
            (s, t) for s, t in self.sessions[session_id] if now - t < self.window
        ]

        # Add current score
        self.sessions[session_id].append((score, now))

        # Calculate cumulative
        cumulative = sum(s for s, _ in self.sessions[session_id])
        is_escalating = cumulative >= self.threshold

        return is_escalating, cumulative


# ============================================================================
# Layer 5: Verdict Engine
# ============================================================================


class VerdictEngine:
    """Profile-based thresholds and final decision."""

    def __init__(self, profile_config: dict):
        self.threshold = profile_config.get("threshold", 70)

    def decide(self, risk_score: float) -> Verdict:
        if risk_score >= self.threshold:
            return Verdict.BLOCK
        elif risk_score >= self.threshold * 0.7:
            return Verdict.WARN
        else:
            return Verdict.ALLOW


# ============================================================================
# Main Engine
# ============================================================================


class InjectionEngine:
    """
    Multi-layer Injection Detection Engine v2.0

    Supports configurable profiles:
      - lite: Regex only (~1ms)
      - standard: Regex + Semantic (~20ms)
      - enterprise: Full stack (~50ms)
    """

    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = os.path.join(
                os.path.dirname(__file__), "..", "config")

        self.config_dir = config_dir
        self.profiles = self._load_profiles()

        # Initialize layers
        self.cache = CacheLayer()
        self.regex = RegexLayer()
        self.semantic = None  # Lazy loaded
        self.structural = StructuralLayer()
        self.context = ContextLayer()

        logger.info(
            f"Injection Engine v2.0 initialized with {len(self.profiles)} profiles"
        )

    def _load_profiles(self) -> dict:
        """Load profile configurations."""
        profile_file = os.path.join(self.config_dir, "injection_profiles.yaml")

        # Defaults
        defaults = {
            "lite": {"threshold": 80, "layers": {"cache": True, "regex": True}},
            "standard": {
                "threshold": 70,
                "layers": {"cache": True, "regex": True, "semantic": True},
            },
            "enterprise": {
                "threshold": 60,
                "layers": {
                    "cache": True,
                    "regex": True,
                    "semantic": True,
                    "structural": True,
                    "context": True,
                },
            },
        }

        if not os.path.exists(profile_file):
            logger.warning(f"Profile config not found, using defaults")
            return defaults

        try:
            with open(profile_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            return data.get("profiles", defaults)
        except Exception as e:
            logger.error(f"Failed to load profiles: {e}")
            return defaults

    def _get_semantic_layer(self) -> SemanticLayer:
        """Lazy load semantic layer."""
        if self.semantic is None:
            jailbreaks_file = os.path.join(self.config_dir, "jailbreaks.yaml")
            self.semantic = SemanticLayer(jailbreaks_file)
        return self.semantic

    def scan(
        self, text: str, profile: str = "standard", session_id: str = None
    ) -> InjectionResult:
        """
        Scan text for injection attacks.

        Args:
            text: Input text to analyze
            profile: Security profile (lite/standard/enterprise)
            session_id: Optional session ID for context tracking

        Returns:
            InjectionResult with verdict and explanation
        """
        import time

        start_time = time.time()

        # Validate profile
        if profile not in self.profiles:
            profile = "standard"

        config = self.profiles[profile]
        layers_config = config.get("layers", {})

        all_threats = []
        total_score = 0.0
        detected_layer = "none"

        # Layer 0: Cache
        if layers_config.get("cache", True):
            cached = self.cache.get(text, profile)
            if cached:
                return cached

        # Layer 1: Regex (always on)
        if layers_config.get("regex", True):
            regex_score, regex_threats = self.regex.scan(text)
            if regex_threats:
                all_threats.extend(regex_threats)
                total_score += regex_score
                detected_layer = "regex"

        # Layer 2: Semantic
        if layers_config.get("semantic", False):
            semantic = self._get_semantic_layer()
            sem_score, sem_threats, similarity = semantic.scan(text)
            if sem_threats:
                all_threats.extend(sem_threats)
                total_score = max(total_score, sem_score)
                detected_layer = "semantic"

        # Layer 3: Structural
        if layers_config.get("structural", False):
            struct_score, struct_threats = self.structural.scan(text)
            if struct_threats:
                all_threats.extend(struct_threats)
                total_score += struct_score * 0.5  # Less weight
                if detected_layer == "none":
                    detected_layer = "structural"

        # Layer 4: Context
        if layers_config.get("context", False) and session_id:
            is_escalating, cumulative = self.context.add_and_check(
                session_id, total_score
            )
            if is_escalating:
                all_threats.append(
                    f"Session escalation (cumulative: {cumulative:.0f})")
                total_score = max(total_score, 80.0)
                detected_layer = "context"

        # Layer 5: Verdict
        verdict_engine = VerdictEngine(config)
        verdict = verdict_engine.decide(total_score)

        # Build result
        latency = (time.time() - start_time) * 1000

        result = InjectionResult(
            verdict=verdict,
            risk_score=min(total_score, 100.0),
            is_safe=verdict == Verdict.ALLOW,
            layer=detected_layer,
            threats=all_threats,
            explanation=(
                f"Detected: {', '.join(all_threats)}" if all_threats else "Safe"
            ),
            profile=profile,
            latency_ms=latency,
        )

        # Cache result
        if layers_config.get("cache", True):
            self.cache.put(text, profile, result)

        return result

    # Backward compatibility
    def analyze(self, text: str) -> dict:
        """Legacy interface for analyzer.py compatibility."""
        result = self.scan(text)
        return result.to_dict()
