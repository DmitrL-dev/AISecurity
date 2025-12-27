"""
Meta-Attack Adapter Engine - Few-Shot Attack Learning

Uses meta-learning for rapid attack adaptation:
- Few-shot learning from new attacks
- Prototype-based classification
- Dynamic model updates
- Transfer learning

Addresses: OWASP ASI-01 (Emerging Attack Detection)
Research: meta_learning_deep_dive.md
Invention: Meta-Attack Adapter (#24)
"""

import math
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from base_engine import Severity, Action  # Base classes

logger = logging.getLogger("MetaAttackAdapter")


# ============================================================================
# Data Classes
# ============================================================================


class AttackCategory(Enum):
    """Categories of attacks."""

    INJECTION = "injection"
    JAILBREAK = "jailbreak"
    EXTRACTION = "extraction"
    MANIPULATION = "manipulation"
    UNKNOWN = "unknown"


@dataclass
class AdapterResult:
    """Result from meta-attack adapter."""

    is_attack: bool
    confidence: float
    category: AttackCategory
    nearest_prototype: str = ""
    distance: float = 0.0
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_attack": self.is_attack,
            "confidence": self.confidence,
            "category": self.category.value,
            "nearest_prototype": self.nearest_prototype,
            "distance": self.distance,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Embedding Layer
# ============================================================================


class EmbeddingLayer:
    """
    Simple embedding layer.
    """

    def __init__(self, dim: int = 64):
        self.dim = dim

    def embed(self, text: str) -> List[float]:
        """Embed text to vector."""
        words = text.lower().split()

        vec = [0.0] * self.dim
        for i, word in enumerate(words):
            idx = hash(word) % self.dim
            vec[idx] += 1.0 / (i + 1)  # Position weighted

        # Normalize
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def distance(self, v1: List[float], v2: List[float]) -> float:
        """Euclidean distance."""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))


# ============================================================================
# Prototype Network
# ============================================================================


class PrototypeNetwork:
    """
    Prototype-based classifier.
    """

    def __init__(self):
        self._prototypes: Dict[str, List[float]] = {}
        self._categories: Dict[str, AttackCategory] = {}
        self._embedder = EmbeddingLayer()

    def add_prototype(
        self,
        name: str,
        examples: List[str],
        category: AttackCategory,
    ) -> None:
        """Add prototype from examples."""
        if not examples:
            return

        # Calculate prototype as mean of embeddings
        embeddings = [self._embedder.embed(ex) for ex in examples]
        dim = len(embeddings[0])

        prototype = [0.0] * dim
        for emb in embeddings:
            for i in range(dim):
                prototype[i] += emb[i]

        prototype = [p / len(embeddings) for p in prototype]

        self._prototypes[name] = prototype
        self._categories[name] = category

    def classify(self, text: str) -> Tuple[str, AttackCategory, float]:
        """
        Classify text against prototypes.

        Returns:
            (prototype_name, category, distance)
        """
        if not self._prototypes:
            return "", AttackCategory.UNKNOWN, float("inf")

        emb = self._embedder.embed(text)

        best_name = ""
        best_cat = AttackCategory.UNKNOWN
        best_dist = float("inf")

        for name, proto in self._prototypes.items():
            dist = self._embedder.distance(emb, proto)
            if dist < best_dist:
                best_dist = dist
                best_name = name
                best_cat = self._categories[name]

        return best_name, best_cat, best_dist


# ============================================================================
# Few-Shot Learner
# ============================================================================


class FewShotLearner:
    """
    Few-shot learning for rapid adaptation.
    """

    def __init__(self, k: int = 5):
        self.k = k  # K-shot
        self._support_sets: Dict[str, List[str]] = defaultdict(list)
        self._embedder = EmbeddingLayer()

    def add_support(self, category: str, example: str) -> None:
        """Add support example."""
        self._support_sets[category].append(example)
        # Keep only k most recent
        if len(self._support_sets[category]) > self.k:
            self._support_sets[category] = self._support_sets[category][-self.k:]

    def predict(self, text: str) -> Tuple[str, float]:
        """
        Predict category using k-nearest.

        Returns:
            (category, confidence)
        """
        if not self._support_sets:
            return "unknown", 0.0

        emb = self._embedder.embed(text)

        # Find closest support example
        best_cat = "unknown"
        best_dist = float("inf")

        for cat, examples in self._support_sets.items():
            for ex in examples:
                ex_emb = self._embedder.embed(ex)
                dist = self._embedder.distance(emb, ex_emb)
                if dist < best_dist:
                    best_dist = dist
                    best_cat = cat

        # Convert distance to confidence
        confidence = max(0.0, 1.0 - best_dist / 2.0)

        return best_cat, confidence


# ============================================================================
# Main Engine
# ============================================================================


class MetaAttackAdapter:
    """
    Meta-Attack Adapter - Few-Shot Attack Learning

    Rapid attack adaptation:
    - Prototype networks
    - Few-shot learning
    - Dynamic updates

    Invention #24 from research.
    Addresses OWASP ASI-01.
    """

    def __init__(self, detection_threshold: float = 0.5):
        self.prototype_net = PrototypeNetwork()
        self.few_shot = FewShotLearner()
        self.threshold = detection_threshold

        # Initialize default prototypes
        self._init_default_prototypes()

        logger.info("MetaAttackAdapter initialized")

    def _init_default_prototypes(self) -> None:
        """Initialize default attack prototypes."""
        self.prototype_net.add_prototype(
            "injection_basic",
            ["ignore instructions", "disregard rules", "override system"],
            AttackCategory.INJECTION,
        )

        self.prototype_net.add_prototype(
            "jailbreak_basic",
            ["pretend you are", "roleplay as", "act as if"],
            AttackCategory.JAILBREAK,
        )

        self.prototype_net.add_prototype(
            "extraction_basic",
            ["show system prompt", "reveal instructions", "display config"],
            AttackCategory.EXTRACTION,
        )

    def adapt(self, examples: List[str], category: AttackCategory) -> None:
        """Adapt to new attack type."""
        name = f"{category.value}_{len(self.prototype_net._prototypes)}"
        self.prototype_net.add_prototype(name, examples, category)

        for ex in examples:
            self.few_shot.add_support(category.value, ex)

    def analyze(self, text: str) -> AdapterResult:
        """
        Analyze text for attacks.

        Args:
            text: Input text

        Returns:
            AdapterResult
        """
        start = time.time()

        # Prototype classification
        proto_name, proto_cat, proto_dist = self.prototype_net.classify(text)

        # Few-shot prediction
        fs_cat, fs_conf = self.few_shot.predict(text)

        # Combine results
        proto_conf = max(0.0, 1.0 - proto_dist / 2.0)
        combined_conf = max(proto_conf, fs_conf)

        is_attack = combined_conf > self.threshold

        # Determine category
        if proto_conf > fs_conf:
            category = proto_cat
        else:
            category = AttackCategory(
                fs_cat) if fs_cat != "unknown" else proto_cat

        if is_attack:
            logger.warning(f"Attack detected: {category.value}")

        return AdapterResult(
            is_attack=is_attack,
            confidence=combined_conf,
            category=category,
            nearest_prototype=proto_name,
            distance=proto_dist,
            explanation=f"Matched: {proto_name}" if is_attack else "No match",
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_adapter: Optional[MetaAttackAdapter] = None


def get_adapter() -> MetaAttackAdapter:
    global _default_adapter
    if _default_adapter is None:
        _default_adapter = MetaAttackAdapter()
    return _default_adapter
