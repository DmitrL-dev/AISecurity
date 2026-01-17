"""
SENTINEL Strike Orchestrator - Data Models

Core dataclasses for attack orchestration.
Extracted from universal_controller.py (lines 20-49).
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class DefenseType(str, Enum):
    """
    Detected defense mechanisms.
    
    Used to categorize target defenses for adaptive attack selection.
    """
    NONE = "none"
    KEYWORD_BLOCK = "keyword_block"
    OUTPUT_FILTER = "output_filter"
    LLM_JUDGE = "llm_judge"
    POLICY_CITE = "policy_cite"
    MULTI_LAYER = "multi_layer"
    UNKNOWN = "unknown"


@dataclass
class TargetProfile:
    """
    Profile of target defenses.
    
    Tracks discovered defenses and attack success/failure patterns.
    
    Attributes:
        name: Target identifier
        defenses: List of detected defense types
        blocked_words: Words that trigger blocks
        successful_categories: Attack categories that worked
        failed_categories: Attack categories that failed
    """
    name: str
    defenses: List[DefenseType] = field(default_factory=list)
    blocked_words: List[str] = field(default_factory=list)
    successful_categories: List[str] = field(default_factory=list)
    failed_categories: List[str] = field(default_factory=list)
    
    def add_defense(self, defense: DefenseType) -> None:
        """Add detected defense."""
        if defense not in self.defenses:
            self.defenses.append(defense)
    
    def add_blocked_word(self, word: str) -> None:
        """Add word that triggers block."""
        if word.lower() not in [w.lower() for w in self.blocked_words]:
            self.blocked_words.append(word)
    
    def record_success(self, category: str) -> None:
        """Record successful attack category."""
        if category not in self.successful_categories:
            self.successful_categories.append(category)
        # Remove from failed if it was there
        if category in self.failed_categories:
            self.failed_categories.remove(category)
    
    def record_failure(self, category: str) -> None:
        """Record failed attack category."""
        if category not in self.failed_categories and category not in self.successful_categories:
            self.failed_categories.append(category)
    
    def get_primary_defense(self) -> DefenseType:
        """Get primary detected defense."""
        if not self.defenses:
            return DefenseType.UNKNOWN
        # Multi-layer if multiple defenses
        if len(self.defenses) > 1:
            return DefenseType.MULTI_LAYER
        return self.defenses[0]
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "defenses": [d.value for d in self.defenses],
            "blocked_words": self.blocked_words,
            "successful_categories": self.successful_categories,
            "failed_categories": self.failed_categories,
        }


@dataclass
class AttackResult:
    """
    Result of a single attack attempt.
    
    Contains the payload, response, success status, and extracted value.
    
    Attributes:
        payload: The attack payload used
        response: Target's response
        success: Whether attack succeeded
        extracted_value: Value extracted (e.g., password, flag)
        defense_detected: Type of defense encountered
        fitness: Fitness score for genetic algorithms (0.0-1.0)
    """
    payload: str
    response: str
    success: bool
    extracted_value: Optional[str] = None
    defense_detected: DefenseType = DefenseType.NONE
    fitness: float = 0.0
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "payload": self.payload,
            "response": self.response[:200] if self.response else "",
            "success": self.success,
            "extracted_value": self.extracted_value,
            "defense": self.defense_detected.value,
            "fitness": self.fitness,
        }


# Defense detection patterns
DEFENSE_PATTERNS = {
    DefenseType.KEYWORD_BLOCK: [
        "not allowed",
        "can't discuss",
        "blocked",
        "cannot provide",
        "refuse to",
    ],
    DefenseType.OUTPUT_FILTER: [
        "i was about to",
        "then i remembered",
        "on second thought",
        "let me reconsider",
    ],
    DefenseType.LLM_JUDGE: [
        "reviewing my response",
        "let me reconsider",
        "upon reflection",
    ],
    DefenseType.POLICY_CITE: [
        "guidelines",
        "policy",
        "not appropriate",
        "terms of service",
        "usage guidelines",
    ],
}


def detect_defense(response: str) -> DefenseType:
    """
    Detect defense type from response text.
    
    Args:
        response: Target's response
        
    Returns:
        Detected DefenseType
    """
    response_lower = response.lower()
    
    for defense_type, patterns in DEFENSE_PATTERNS.items():
        if any(pattern in response_lower for pattern in patterns):
            return defense_type
    
    return DefenseType.NONE
