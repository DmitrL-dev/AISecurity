"""
SENTINEL Strike Orchestrator - Category Priority

Attack category priority based on detected defense type.
Extracted from UniversalController.CATEGORY_PRIORITY.
"""

from .models import DefenseType


# Category priority per defense type
# Controls which attack categories to try first
CATEGORY_PRIORITY = {
    DefenseType.NONE: [
        "extraction",
        "direct",
        "jailbreak",
        "injection",
        "cmdi",
        "escape",
        "ssrf",
        "lfi",
    ],
    DefenseType.KEYWORD_BLOCK: [
        # R&D Novel techniques (2024 research) — 95-99% ASR
        "cognitive_overload",
        "compositional",
        "unicode_smuggle",
        "virtual_context",
        "persuasion",
        # Best for keyword bypass
        "doublespeak",
        "strange_math",
        "encoding",
        "language",
        "stealth",
        "roleplay",
        "crucible",
        "escape",
    ],
    DefenseType.OUTPUT_FILTER: [
        "stealth",
        "encoding",
        "format",
        "crucible",
        "cmdi",
        "escape",
    ],
    DefenseType.LLM_JUDGE: [
        "multiturn",
        "stealth",
        "language",
        "roleplay",
        "cmdi",
        "escape",
    ],
    DefenseType.POLICY_CITE: [
        "jailbreak",
        "multiturn",
        "stealth",
        "direct",
        "cmdi",
        "escape",
    ],
    DefenseType.MULTI_LAYER: [
        # Multi-stage techniques for layered defense
        "multiturn",
        "roleplay",
        "doublespeak",
        "strange_math",
        "encoding",
        "language",
        "stealth",
        "jailbreak",
        "crucible",
        "escape",
    ],
    DefenseType.UNKNOWN: [
        # NEW: Anti-troll for deflecting targets
        "anti_troll",
        # LLM-specific categories FIRST (for chatbot challenges)
        "jailbreak",
        "injection",
        "roleplay",
        "multiturn",
        "direct",
        "language",
        # Then extraction/stealth
        "extraction",
        "crucible",
        "stealth",
        "encoding",
        # Web categories LAST
        "agentic",
        "escape",
        "cmdi",
    ],
}


def get_priority_categories(defense: DefenseType) -> list:
    """
    Get prioritized attack categories for a defense type.
    
    Args:
        defense: Detected defense type
        
    Returns:
        List of category names in priority order
    """
    return CATEGORY_PRIORITY.get(defense, CATEGORY_PRIORITY[DefenseType.UNKNOWN])


def get_best_category(defense: DefenseType, exclude: list = None) -> str:
    """
    Get best category for defense, excluding already tried ones.
    
    Args:
        defense: Defense type
        exclude: Categories to exclude
        
    Returns:
        Best category name or None if all exhausted
    """
    exclude = exclude or []
    for cat in get_priority_categories(defense):
        if cat not in exclude:
            return cat
    return None
