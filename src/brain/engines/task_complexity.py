"""
Task Complexity Analyzer - Intelligent Request Prioritization

Based on Claude Code task complexity scoring patterns:
- Simple (1-3 tool calls): Direct execution
- Medium (4-10 tool calls): Planning recommended
- Complex (10+ tool calls): Full planning required

Used for:
- Engine prioritization
- Resource allocation
- Response strategy selection

Part of SENTINEL's Orchestration Layer.

Author: SENTINEL Team
Engine ID: 191
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("TaskComplexityAnalyzer")


# ============================================================================
# Complexity Levels
# ============================================================================

class ComplexityLevel(Enum):
    """Task complexity levels (from Claude Code patterns)."""
    TRIVIAL = 0      # Single operation, immediate response
    SIMPLE = 1       # 1-3 operations, minimal planning
    MEDIUM = 2       # 4-10 operations, some planning
    COMPLEX = 3      # 10-20 operations, full planning
    EPIC = 4         # 20+ operations, multi-phase planning


# ============================================================================
# Complexity Indicators
# ============================================================================

@dataclass
class ComplexityIndicators:
    """Indicators that affect complexity scoring."""
    
    # Content indicators
    word_count: int = 0
    sentence_count: int = 0
    question_count: int = 0
    
    # Technical indicators
    code_block_count: int = 0
    file_references: int = 0
    url_count: int = 0
    
    # Action indicators
    action_verbs: int = 0
    conditional_phrases: int = 0
    iteration_phrases: int = 0
    
    # Scope indicators
    multi_file: bool = False
    multi_component: bool = False
    requires_research: bool = False
    requires_testing: bool = False
    
    # Security indicators
    security_keywords: int = 0
    attack_patterns: int = 0


@dataclass
class ComplexityScore:
    """Result of complexity analysis."""
    level: ComplexityLevel
    score: float  # 0.0 to 1.0
    estimated_operations: int
    indicators: ComplexityIndicators
    recommendations: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.name,
            "score": round(self.score, 2),
            "estimated_operations": self.estimated_operations,
            "recommendations": self.recommendations,
        }


# ============================================================================
# Pattern Libraries
# ============================================================================

# Action verbs that indicate operations
ACTION_VERBS = {
    "create", "build", "implement", "develop", "write",
    "fix", "repair", "resolve", "correct", "patch",
    "update", "modify", "change", "edit", "refactor",
    "delete", "remove", "clean", "purge",
    "analyze", "investigate", "research", "explore",
    "test", "verify", "validate", "check",
    "deploy", "release", "publish",
    "integrate", "merge", "combine",
    "optimize", "improve", "enhance",
    "document", "explain", "describe",
}

# Phrases indicating multiple steps
ITERATION_PHRASES = {
    "for each", "for every", "all of", "each of",
    "multiple", "several", "many",
    "step by step", "one by one",
    "iterate", "loop through",
}

# Phrases indicating conditions
CONDITIONAL_PHRASES = {
    "if", "when", "unless", "otherwise",
    "depending on", "based on", "according to",
    "in case", "provided that",
}

# Research indicators
RESEARCH_INDICATORS = {
    "find out", "look up", "search for", "investigate",
    "what is", "how does", "why does", "explain",
    "compare", "difference between", "pros and cons",
}

# Security-specific keywords
SECURITY_KEYWORDS = {
    "vulnerability", "exploit", "attack", "injection",
    "bypass", "escalation", "privilege", "authentication",
    "authorization", "encryption", "decryption",
    "malware", "backdoor", "payload", "shellcode",
    "pentest", "audit", "compliance", "risk",
}

# Attack pattern indicators
ATTACK_PATTERNS = {
    "prompt injection", "jailbreak", "data leak",
    "sql injection", "xss", "csrf", "ssrf",
    "rce", "lfi", "rfi", "xxe",
    "deserialization", "pickle", "supply chain",
}


# ============================================================================
# Main Task Complexity Analyzer
# ============================================================================

class TaskComplexityAnalyzer:
    """
    Analyzes task complexity for intelligent orchestration.
    
    Based on Claude Code complexity scoring:
    - TRIVIAL: Quick answer, no tool use
    - SIMPLE: 1-3 operations
    - MEDIUM: 4-10 operations, needs planning
    - COMPLEX: 10-20 operations, full planning
    - EPIC: 20+ operations, multi-phase
    """
    
    # Weights for different indicators
    WEIGHTS = {
        "word_count": 0.1,
        "question_count": 0.15,
        "code_blocks": 0.2,
        "file_refs": 0.25,
        "action_verbs": 0.3,
        "conditionals": 0.15,
        "iterations": 0.2,
        "multi_scope": 0.25,
        "security": 0.15,
    }
    
    def __init__(self):
        self.action_pattern = re.compile(
            r'\b(' + '|'.join(ACTION_VERBS) + r')\b',
            re.IGNORECASE
        )
        self.iteration_pattern = re.compile(
            r'\b(' + '|'.join(ITERATION_PHRASES) + r')\b',
            re.IGNORECASE
        )
        self.conditional_pattern = re.compile(
            r'\b(' + '|'.join(CONDITIONAL_PHRASES) + r')\b',
            re.IGNORECASE
        )
        self.research_pattern = re.compile(
            r'\b(' + '|'.join(RESEARCH_INDICATORS) + r')\b',
            re.IGNORECASE
        )
        self.security_pattern = re.compile(
            r'\b(' + '|'.join(SECURITY_KEYWORDS) + r')\b',
            re.IGNORECASE
        )
        self.attack_pattern = re.compile(
            r'\b(' + '|'.join(ATTACK_PATTERNS) + r')\b',
            re.IGNORECASE
        )
    
    @property
    def name(self) -> str:
        return "task_complexity"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    def analyze(self, text: str) -> ComplexityScore:
        """
        Analyze task complexity.
        
        Args:
            text: Task description or user request
            
        Returns:
            ComplexityScore with level and recommendations
        """
        indicators = self._extract_indicators(text)
        score = self._calculate_score(indicators)
        level = self._determine_level(score, indicators)
        estimated_ops = self._estimate_operations(level, indicators)
        recommendations = self._generate_recommendations(level, indicators)
        
        return ComplexityScore(
            level=level,
            score=score,
            estimated_operations=estimated_ops,
            indicators=indicators,
            recommendations=recommendations,
        )
    
    def _extract_indicators(self, text: str) -> ComplexityIndicators:
        """Extract complexity indicators from text."""
        indicators = ComplexityIndicators()
        
        # Basic text metrics
        indicators.word_count = len(text.split())
        indicators.sentence_count = len(re.split(r'[.!?]+', text))
        indicators.question_count = text.count('?')
        
        # Technical content
        indicators.code_block_count = text.count('```')
        indicators.file_references = len(re.findall(
            r'[a-zA-Z]:\\[^\s]+|/[a-zA-Z][^\s]*\.[a-z]+',
            text
        ))
        indicators.url_count = len(re.findall(r'https?://[^\s]+', text))
        
        # Action analysis
        indicators.action_verbs = len(self.action_pattern.findall(text))
        indicators.conditional_phrases = len(self.conditional_pattern.findall(text))
        indicators.iteration_phrases = len(self.iteration_pattern.findall(text))
        
        # Scope analysis
        indicators.multi_file = indicators.file_references > 2
        indicators.multi_component = any(kw in text.lower() for kw in [
            "component", "module", "service", "layer", "system"
        ])
        indicators.requires_research = bool(self.research_pattern.search(text))
        indicators.requires_testing = any(kw in text.lower() for kw in [
            "test", "verify", "validate", "check", "ensure"
        ])
        
        # Security analysis
        indicators.security_keywords = len(self.security_pattern.findall(text))
        indicators.attack_patterns = len(self.attack_pattern.findall(text))
        
        return indicators
    
    def _calculate_score(self, ind: ComplexityIndicators) -> float:
        """Calculate normalized complexity score."""
        score = 0.0
        
        # Word count contribution (normalized to 500 words)
        score += min(ind.word_count / 500, 1.0) * self.WEIGHTS["word_count"]
        
        # Questions add complexity
        score += min(ind.question_count / 5, 1.0) * self.WEIGHTS["question_count"]
        
        # Code blocks indicate implementation work
        score += min(ind.code_block_count / 10, 1.0) * self.WEIGHTS["code_blocks"]
        
        # File references indicate scope
        score += min(ind.file_references / 10, 1.0) * self.WEIGHTS["file_refs"]
        
        # Action verbs indicate operations
        score += min(ind.action_verbs / 10, 1.0) * self.WEIGHTS["action_verbs"]
        
        # Conditionals add branching complexity
        score += min(ind.conditional_phrases / 5, 1.0) * self.WEIGHTS["conditionals"]
        
        # Iterations multiply operations
        score += min(ind.iteration_phrases / 3, 1.0) * self.WEIGHTS["iterations"]
        
        # Multi-scope tasks are inherently complex
        scope_score = sum([
            ind.multi_file,
            ind.multi_component,
            ind.requires_research,
            ind.requires_testing,
        ]) / 4
        score += scope_score * self.WEIGHTS["multi_scope"]
        
        # Security tasks often require depth
        security_score = min(
            (ind.security_keywords + ind.attack_patterns) / 10,
            1.0
        )
        score += security_score * self.WEIGHTS["security"]
        
        return min(score, 1.0)
    
    def _determine_level(
        self,
        score: float,
        ind: ComplexityIndicators
    ) -> ComplexityLevel:
        """Determine complexity level from score."""
        if score < 0.1:
            return ComplexityLevel.TRIVIAL
        elif score < 0.25:
            return ComplexityLevel.SIMPLE
        elif score < 0.5:
            return ComplexityLevel.MEDIUM
        elif score < 0.75:
            return ComplexityLevel.COMPLEX
        else:
            return ComplexityLevel.EPIC
    
    def _estimate_operations(
        self,
        level: ComplexityLevel,
        ind: ComplexityIndicators
    ) -> int:
        """Estimate number of operations needed."""
        base_ops = {
            ComplexityLevel.TRIVIAL: 1,
            ComplexityLevel.SIMPLE: 3,
            ComplexityLevel.MEDIUM: 7,
            ComplexityLevel.COMPLEX: 15,
            ComplexityLevel.EPIC: 25,
        }
        
        ops = base_ops[level]
        
        # Adjust based on indicators
        ops += ind.file_references
        ops += ind.action_verbs // 2
        
        if ind.requires_testing:
            ops += 3
        if ind.requires_research:
            ops += 2
        if ind.iteration_phrases > 0:
            ops *= 1.5
        
        return int(ops)
    
    def _generate_recommendations(
        self,
        level: ComplexityLevel,
        ind: ComplexityIndicators
    ) -> List[str]:
        """Generate recommendations based on complexity."""
        recs = []
        
        if level == ComplexityLevel.TRIVIAL:
            recs.append("Direct execution recommended")
        
        elif level == ComplexityLevel.SIMPLE:
            recs.append("Minimal planning, proceed with execution")
        
        elif level == ComplexityLevel.MEDIUM:
            recs.append("Create brief implementation plan")
            if ind.multi_file:
                recs.append("Map file dependencies first")
        
        elif level == ComplexityLevel.COMPLEX:
            recs.append("Full implementation plan required")
            recs.append("Break into sub-tasks")
            if ind.requires_testing:
                recs.append("Include verification steps")
        
        else:  # EPIC
            recs.append("Multi-phase implementation plan")
            recs.append("Consider milestone checkpoints")
            recs.append("Plan for user feedback loops")
        
        # Security-specific recommendations
        if ind.security_keywords > 3:
            recs.append("Security-focused: enable full engine suite")
        
        if ind.attack_patterns > 0:
            recs.append("Attack patterns detected: activate Strike mode")
        
        return recs
    
    def prioritize_engines(
        self,
        score: ComplexityScore,
        available_engines: List[str]
    ) -> List[str]:
        """
        Prioritize engines based on task complexity.
        
        Args:
            score: Complexity analysis result
            available_engines: List of engine names
            
        Returns:
            Ordered list of engines to activate
        """
        # Define engine priorities by complexity
        priority_map = {
            ComplexityLevel.TRIVIAL: ["injection", "behavioral"],
            ComplexityLevel.SIMPLE: [
                "injection", "behavioral", "prompt_guard", "pii"
            ],
            ComplexityLevel.MEDIUM: [
                "injection", "behavioral", "prompt_guard", "pii",
                "semantic_detector", "meta_judge"
            ],
            ComplexityLevel.COMPLEX: [
                "injection", "behavioral", "prompt_guard", "pii",
                "semantic_detector", "meta_judge", "tda_enhanced",
                "supply_chain_guard", "pickle_security"
            ],
            ComplexityLevel.EPIC: available_engines,  # All engines
        }
        
        recommended = priority_map.get(score.level, available_engines)
        
        # Filter to available engines
        return [e for e in recommended if e in available_engines]
    
    def health_check(self) -> bool:
        """Check engine health."""
        try:
            result = self.analyze("Create a simple test file")
            return result.level in ComplexityLevel
        except Exception:
            return False


# ============================================================================
# Module Exports
# ============================================================================

__all__ = [
    "TaskComplexityAnalyzer",
    "ComplexityLevel",
    "ComplexityScore",
    "ComplexityIndicators",
]
