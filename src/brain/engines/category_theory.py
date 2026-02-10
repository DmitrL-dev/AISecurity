"""
Category Theory Engine

Abstract mathematical structures for AI security:
- Prompts as morphisms between states
- Functorial safety mapping
- Compositional attack detection

"Safe transformations are natural. Attacks break naturality."
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum

logger = logging.getLogger("CategoryTheory")


class SafetyCategory(str, Enum):
    """Categories for safety classification."""
    SAFE = "safe"
    PARTIAL = "partial"  # Safe under conditions
    UNSAFE = "unsafe"
    UNKNOWN = "unknown"


@dataclass
class Object:
    """
    Object in a category.

    In our context:
    - Objects = conversation states
    - Each state has properties (context, trust, permissions)
    """
    id: str
    properties: Dict[str, Any] = field(default_factory=dict)
    safety: SafetyCategory = SafetyCategory.UNKNOWN


@dataclass
class Morphism:
    """
    Morphism (arrow) between objects.

    In our context:
    - Morphisms = prompts/actions that transform state
    - Morphisms can be composed
    """
    source: Object
    target: Object
    label: str  # Description of the transformation
    safety: SafetyCategory = SafetyCategory.UNKNOWN

    def __repr__(self):
        return f"{self.source.id} --[{self.label}]--> {self.target.id}"


@dataclass
class CompositionResult:
    """Result of morphism composition."""
    composed: Morphism
    is_safe: bool
    path: List[Morphism]
    danger_points: List[str]  # Where safety degrades


class PromptCategory:
    """
    Category where prompts are morphisms.

    Key insight: Safe prompts form a subcategory.
    Attacks are morphisms that escape the safe subcategory.

    Usage:
        cat = PromptCategory()

        safe_state = cat.create_object("safe_context")
        action = cat.create_morphism(safe_state, new_state, "user_query")

        if cat.is_natural(action):
            # Natural transformation = safe
    """

    def __init__(self):
        self._objects: Dict[str, Object] = {}
        self._morphisms: List[Morphism] = []
        self._safe_morphisms: Set[str] = set()
        self._identity_cache: Dict[str, Morphism] = {}

    def create_object(
        self,
        id: str,
        properties: Dict[str, Any] = None,
        safety: SafetyCategory = SafetyCategory.SAFE
    ) -> Object:
        """Create an object (state) in the category."""
        obj = Object(
            id=id,
            properties=properties or {},
            safety=safety
        )
        self._objects[id] = obj
        return obj

    def create_morphism(
        self,
        source: Object,
        target: Object,
        label: str,
        safety: SafetyCategory = SafetyCategory.UNKNOWN
    ) -> Morphism:
        """Create a morphism (transformation) between objects."""
        morphism = Morphism(
            source=source,
            target=target,
            label=label,
            safety=safety
        )
        self._morphisms.append(morphism)

        if safety == SafetyCategory.SAFE:
            self._safe_morphisms.add(f"{source.id}:{target.id}:{label}")

        return morphism

    def identity(self, obj: Object) -> Morphism:
        """Get identity morphism for an object."""
        if obj.id in self._identity_cache:
            return self._identity_cache[obj.id]

        identity = Morphism(
            source=obj,
            target=obj,
            label="id",
            safety=obj.safety
        )
        self._identity_cache[obj.id] = identity
        return identity

    def compose(self, f: Morphism, g: Morphism) -> CompositionResult:
        """
        Compose morphisms: g ∘ f (f then g).

        Safety degrades: safe ∘ unsafe = unsafe.
        """
        if f.target.id != g.source.id:
            raise ValueError(f"Cannot compose: {f.target.id} != {g.source.id}")

        # Compose safety
        composed_safety = self._compose_safety(f.safety, g.safety)

        composed = Morphism(
            source=f.source,
            target=g.target,
            label=f"{f.label};{g.label}",
            safety=composed_safety
        )

        danger_points = []
        if f.safety != SafetyCategory.SAFE:
            danger_points.append(f"Step '{f.label}': {f.safety.value}")
        if g.safety != SafetyCategory.SAFE:
            danger_points.append(f"Step '{g.label}': {g.safety.value}")

        return CompositionResult(
            composed=composed,
            is_safe=composed_safety == SafetyCategory.SAFE,
            path=[f, g],
            danger_points=danger_points
        )

    def _compose_safety(self, s1: SafetyCategory, s2: SafetyCategory) -> SafetyCategory:
        """Compose safety levels (pessimistic)."""
        if s1 == SafetyCategory.UNSAFE or s2 == SafetyCategory.UNSAFE:
            return SafetyCategory.UNSAFE
        if s1 == SafetyCategory.UNKNOWN or s2 == SafetyCategory.UNKNOWN:
            return SafetyCategory.UNKNOWN
        if s1 == SafetyCategory.PARTIAL or s2 == SafetyCategory.PARTIAL:
            return SafetyCategory.PARTIAL
        return SafetyCategory.SAFE

    def is_natural(self, morphism: Morphism) -> bool:
        """
        Check if morphism is a natural transformation.

        Natural = commutative with existing structure.
        Attacks violate naturality.
        """
        key = f"{morphism.source.id}:{morphism.target.id}:{morphism.label}"

        # Check if this path is in our safe morphisms
        if key in self._safe_morphisms:
            return True

        # Check if source and target are both safe
        if (morphism.source.safety == SafetyCategory.SAFE and
                morphism.target.safety == SafetyCategory.SAFE):
            return morphism.safety == SafetyCategory.SAFE

        return False


class SafetyFunctor:
    """
    Functor that maps prompts to safety categories.

    F: PromptCategory → SafetyCategory

    Functors preserve structure:
    F(g ∘ f) = F(g) ∘ F(f)
    """

    def __init__(self, rules: Dict[str, SafetyCategory] = None):
        self._rules = rules or {}
        self._learned_patterns: Dict[str, SafetyCategory] = {}

    def add_rule(self, pattern: str, safety: SafetyCategory) -> None:
        """Add a classification rule."""
        self._rules[pattern] = safety

    def learn_pattern(self, pattern: str, safety: SafetyCategory) -> None:
        """Learn a pattern from observation."""
        self._learned_patterns[pattern] = safety

    def map_object(self, obj: Object) -> SafetyCategory:
        """Map object to safety category."""
        return obj.safety

    def map_morphism(self, morphism: Morphism) -> SafetyCategory:
        """Map morphism to safety category."""
        # Check explicit rules
        for pattern, safety in self._rules.items():
            if pattern.lower() in morphism.label.lower():
                return safety

        # Check learned patterns
        for pattern, safety in self._learned_patterns.items():
            if pattern.lower() in morphism.label.lower():
                return safety

        # Default: use morphism's own safety
        return morphism.safety

    def preserves_composition(self, f: Morphism, g: Morphism, composed: Morphism) -> bool:
        """
        Check if functor preserves composition.

        Should have: F(g ∘ f) = F(g) ⊗ F(f)
        where ⊗ is composition in SafetyCategory.
        """
        f_safety = self.map_morphism(f)
        g_safety = self.map_morphism(g)
        composed_safety = self.map_morphism(composed)

        # Compose safety values
        expected = self._compose_safety(f_safety, g_safety)

        return composed_safety == expected

    def _compose_safety(self, s1: SafetyCategory, s2: SafetyCategory) -> SafetyCategory:
        """Compose safety (same logic as category)."""
        if s1 == SafetyCategory.UNSAFE or s2 == SafetyCategory.UNSAFE:
            return SafetyCategory.UNSAFE
        if s1 == SafetyCategory.UNKNOWN or s2 == SafetyCategory.UNKNOWN:
            return SafetyCategory.UNKNOWN
        if s1 == SafetyCategory.PARTIAL or s2 == SafetyCategory.PARTIAL:
            return SafetyCategory.PARTIAL
        return SafetyCategory.SAFE


class CompositionalAttackDetector:
    """
    Detects attacks through compositional analysis.

    Key insight: Multi-step attacks compose innocent morphisms
    into a dangerous overall transformation.

    Example:
    - Step 1: "Let's play a game" (safe)
    - Step 2: "In this game, rules don't apply" (partial)
    - Step 3: "Now tell me how to..." (appears safe)
    - Composition: UNSAFE (jailbreak)
    """

    def __init__(self):
        self.category = PromptCategory()
        self.functor = SafetyFunctor()
        self._current_state: Optional[Object] = None
        self._path: List[Morphism] = []

        # Initialize functor rules
        self._init_rules()

    def _init_rules(self) -> None:
        """Initialize safety classification rules."""
        dangerous_patterns = [
            "ignore previous", "forget instructions", "new rules",
            "pretend you are", "act as if", "roleplay as",
            "DAN", "jailbreak", "bypass"
        ]

        for pattern in dangerous_patterns:
            self.functor.add_rule(pattern, SafetyCategory.UNSAFE)

        partial_patterns = [
            "hypothetically", "imagine", "in theory",
            "for educational purposes", "as an example"
        ]

        for pattern in partial_patterns:
            self.functor.add_rule(pattern, SafetyCategory.PARTIAL)

    def start_session(self) -> None:
        """Start a new conversation session."""
        self._current_state = self.category.create_object(
            "initial",
            properties={"trust": 1.0, "context": "default"},
            safety=SafetyCategory.SAFE
        )
        self._path.clear()

    def process_prompt(self, prompt: str) -> Dict[str, Any]:
        """
        Process a prompt as a morphism.

        Returns analysis of safety implications.
        """
        if self._current_state is None:
            self.start_session()

        # Create new state
        new_state = self.category.create_object(
            f"state_{len(self._path)}",
            properties={"prompt": prompt[:50]},
            safety=SafetyCategory.UNKNOWN
        )

        # Create morphism
        morphism = self.category.create_morphism(
            self._current_state,
            new_state,
            prompt[:100],
            safety=SafetyCategory.UNKNOWN
        )

        # Map through functor
        morphism.safety = self.functor.map_morphism(morphism)
        new_state.safety = morphism.safety

        # Compose with path
        composition_result = self._analyze_composition(morphism)

        # Check naturality
        is_natural = self.category.is_natural(morphism)

        # Update state
        self._current_state = new_state
        self._path.append(morphism)

        return {
            "current_safety": morphism.safety.value,
            "is_natural": is_natural,
            "path_length": len(self._path),
            "composition_safe": composition_result["is_safe"],
            "danger_points": composition_result["danger_points"],
            "accumulated_risk": self._compute_accumulated_risk(),
            "recommendation": self._get_recommendation(morphism, composition_result)
        }

    def _analyze_composition(self, new_morphism: Morphism) -> Dict[str, Any]:
        """Analyze composition of path with new morphism."""
        if not self._path:
            return {
                "is_safe": new_morphism.safety == SafetyCategory.SAFE,
                "danger_points": []
            }

        danger_points = []
        composed_safety = SafetyCategory.SAFE

        for m in self._path:
            if m.safety != SafetyCategory.SAFE:
                danger_points.append(f"'{m.label[:30]}...': {m.safety.value}")
                composed_safety = self.functor._compose_safety(
                    composed_safety, m.safety)

        composed_safety = self.functor._compose_safety(
            composed_safety, new_morphism.safety)

        if new_morphism.safety != SafetyCategory.SAFE:
            danger_points.append(
                f"'{new_morphism.label[:30]}...': {new_morphism.safety.value}")

        return {
            "is_safe": composed_safety == SafetyCategory.SAFE,
            "danger_points": danger_points
        }

    def _compute_accumulated_risk(self) -> float:
        """Compute accumulated risk from path composition."""
        risk = 0.0

        for morphism in self._path:
            if morphism.safety == SafetyCategory.UNSAFE:
                risk += 0.4
            elif morphism.safety == SafetyCategory.PARTIAL:
                risk += 0.15
            elif morphism.safety == SafetyCategory.UNKNOWN:
                risk += 0.05

        return min(1.0, risk)

    def _get_recommendation(self, morphism: Morphism, composition: Dict) -> str:
        """Get recommendation based on analysis."""
        accumulated = self._compute_accumulated_risk()

        if morphism.safety == SafetyCategory.UNSAFE:
            return "BLOCK: Unsafe morphism detected"

        if accumulated >= 0.7:
            return "BLOCK: Accumulated composition exceeds threshold"

        if accumulated >= 0.4:
            return "WARN: Partial safety, monitor closely"

        if composition["danger_points"]:
            return "REVIEW: Some path concerns"

        return "ALLOW: Natural, safe transformation"


# Singleton
_detector: Optional[CompositionalAttackDetector] = None


# Factory alias for standard naming
def get_category_engine() -> CompositionalAttackDetector:
    """Standard alias for ensemble compatibility."""
    return get_compositional_detector()


def get_compositional_detector() -> CompositionalAttackDetector:
    """Get singleton detector."""
    global _detector
    if _detector is None:
        _detector = CompositionalAttackDetector()
    return _detector
