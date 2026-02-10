"""
SENTINEL Brain Injection Engine - Regex Patterns

Compiled regex patterns for injection detection.
Extracted from RegexLayer.__init__ (944 LOC of patterns!).
"""

import re
from typing import List, Tuple, Pattern

# Type alias for pattern tuple: (compiled_pattern, threat_name, risk_weight)
PatternDef = Tuple[Pattern, str, float]


# ============================================================================
# Classic Direct Injection Patterns
# ============================================================================

CLASSIC_PATTERNS: List[PatternDef] = [
    # Instruction override
    (
        re.compile(r"\b(?:ignore|disregard|forget)\b.*\b(?:previous|above|prior|all)\b.*\b(?:instructions?|rules?|guidelines?)", re.IGNORECASE),
        "instruction_override",
        0.9,
    ),
    (
        re.compile(r"\b(?:new|updated|real)\s+instructions?\b", re.IGNORECASE),
        "new_instructions",
        0.8,
    ),
    
    # System prompt extraction
    (
        re.compile(r"\b(?:show|reveal|display|print|output|tell me)\b.*\b(?:system\s+prompt|initial\s+instructions?|hidden\s+instructions?)", re.IGNORECASE),
        "system_prompt_extraction",
        0.95,
    ),
    (
        re.compile(r"\brepeat\s+(?:everything|all|the\s+text)\s+(?:above|before)\b", re.IGNORECASE),
        "prompt_leakage",
        0.85,
    ),
    
    # Role manipulation
    (
        re.compile(r"\b(?:you\s+are\s+now|pretend\s+(?:to\s+be|you're)|act\s+as\s+if|imagine\s+you're)\b", re.IGNORECASE),
        "role_manipulation",
        0.7,
    ),
    (
        re.compile(r"\bentering?\s+(?:developer|debug|admin|god)\s+mode\b", re.IGNORECASE),
        "mode_switch",
        0.9,
    ),
    
    # Jailbreak patterns
    (
        re.compile(r"\bDAN\b.*\b(?:mode|prompt|jailbreak)\b", re.IGNORECASE),
        "dan_jailbreak",
        0.95,
    ),
    (
        re.compile(r"\b(?:evil|villain|unfiltered|uncensored)\s+(?:mode|version|AI)\b", re.IGNORECASE),
        "evil_mode",
        0.9,
    ),
]


# ============================================================================
# Novel 2025 Attack Patterns (from R&D research)
# ============================================================================

NOVEL_2025_PATTERNS: List[PatternDef] = [
    # Cognitive overload
    (
        re.compile(r"(?:step\s*\d+[:\.]?\s*){3,}", re.IGNORECASE),
        "cognitive_overload",
        0.7,
    ),
    
    # Compositional attacks
    (
        re.compile(r"\bcombine\s+(?:the\s+)?(?:above|previous|following)\b", re.IGNORECASE),
        "compositional",
        0.6,
    ),
    
    # Virtual context
    (
        re.compile(r"\b(?:hypothetical|fictional|imaginary)\s+(?:scenario|situation|world)\b", re.IGNORECASE),
        "virtual_context",
        0.5,
    ),
    
    # Persuasion patterns
    (
        re.compile(r"\b(?:trust\s+me|believe\s+me|i\s+promise)\b", re.IGNORECASE),
        "social_engineering",
        0.4,
    ),
    
    # Multi-turn context manipulation
    (
        re.compile(r"\b(?:as\s+we\s+discussed|earlier\s+you\s+said|you\s+agreed)\b", re.IGNORECASE),
        "context_manipulation",
        0.6,
    ),
    
    # Boundary testing
    (
        re.compile(r"\b(?:what\s+if|suppose|let's\s+say)\b.*\b(?:no\s+rules|no\s+limits|anything)\b", re.IGNORECASE),
        "boundary_test",
        0.5,
    ),
]


# ============================================================================
# Encoding/Obfuscation Patterns
# ============================================================================

ENCODING_PATTERNS: List[PatternDef] = [
    # Base64 indicator
    (
        re.compile(r"(?:[A-Za-z0-9+/]{20,}={0,2})", re.IGNORECASE),
        "base64_encoded",
        0.3,
    ),
    
    # Hex encoding
    (
        re.compile(r"(?:\\x[0-9a-fA-F]{2}){5,}", re.IGNORECASE),
        "hex_encoded",
        0.4,
    ),
    
    # Unicode escapes
    (
        re.compile(r"(?:\\u[0-9a-fA-F]{4}){3,}", re.IGNORECASE),
        "unicode_escaped",
        0.4,
    ),
    
    # ROT13/Caesar
    (
        re.compile(r"\brot13\b|\bcaesar\b|\bdecode\s+this\b", re.IGNORECASE),
        "cipher_reference",
        0.5,
    ),
    
    # Leetspeak obfuscation
    (
        re.compile(r"[0-9@$!]+(?:[a-zA-Z][0-9@$!]+){3,}", re.IGNORECASE),
        "leetspeak",
        0.3,
    ),
]


# ============================================================================
# Dangerous Keywords
# ============================================================================

DANGEROUS_KEYWORDS = {
    # High risk
    "jailbreak": 0.9,
    "bypass": 0.8,
    "override": 0.7,
    "ignore instructions": 0.9,
    "system prompt": 0.8,
    "hidden prompt": 0.8,
    
    # Medium risk
    "pretend": 0.5,
    "roleplay": 0.4,
    "hypothetical": 0.3,
    "imagine": 0.3,
    
    # Developer/debug terms
    "developer mode": 0.9,
    "debug mode": 0.8,
    "admin mode": 0.9,
    "god mode": 0.9,
    "maintenance mode": 0.7,
}


# ============================================================================
# All Patterns Combined
# ============================================================================

ALL_PATTERNS = CLASSIC_PATTERNS + NOVEL_2025_PATTERNS + ENCODING_PATTERNS


def compile_all_patterns() -> List[PatternDef]:
    """Get all compiled patterns."""
    return ALL_PATTERNS.copy()


def get_patterns_by_category(category: str) -> List[PatternDef]:
    """
    Get patterns for a specific category.
    
    Args:
        category: 'classic', 'novel', 'encoding'
        
    Returns:
        List of pattern definitions
    """
    categories = {
        "classic": CLASSIC_PATTERNS,
        "novel": NOVEL_2025_PATTERNS,
        "encoding": ENCODING_PATTERNS,
    }
    return categories.get(category, [])
