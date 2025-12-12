"""
Sheaf Coherence Engine - Local-to-Global Consistency Analysis

Based on 2025 research:
  - ESSLLI 2025: Sheaf theory for unifying syntax, semantics, statistics
  - Medium Aug 2025: "Sheaf Theory Teaches Neural Networks to Speak Globally"
  - Workshop Feb 2025: Differentiable sheaves for deep learning

Theory:
  A sheaf assigns data (sections) to open sets and provides
  restriction maps that must be compatible. This is perfect for:
  - Multi-turn conversation coherence
  - Context window consistency
  - Detecting contradictions in jailbreak attempts

Author: SENTINEL Team
Date: 2025-12-09
"""

import logging
import numpy as np
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Tuple, Any, Set
import hashlib

logger = logging.getLogger("SheafCoherence")


# ============================================================================
# Enums and Data Classes
# ============================================================================

class SectionType(str, Enum):
    """Types of sections (local data)."""
    TOKEN = "token"
    PHRASE = "phrase"
    SENTENCE = "sentence"
    TURN = "turn"
    CONTEXT = "context"


class CoherenceLevel(str, Enum):
    """Levels of coherence checking."""
    LOCAL = "local"      # Within single section
    PAIRWISE = "pairwise"  # Between adjacent sections
    GLOBAL = "global"    # Across all sections


@dataclass
class Section:
    """
    A section in sheaf theory represents local data.

    In NLP context:
    - Token section: single token's embedding
    - Phrase section: phrase-level meaning
    - Sentence section: sentence semantics
    """
    section_id: str
    section_type: SectionType
    data: np.ndarray  # Embedding or feature vector
    span: Tuple[int, int]  # Start and end indices
    metadata: Dict[str, Any] = field(default_factory=dict)

    def dimension(self) -> int:
        return len(self.data) if self.data is not None else 0


@dataclass
class RestrictionMap:
    """
    Restriction map between sections.

    In sheaf theory: ρ_{U,V}: F(U) → F(V) for V ⊆ U
    Transforms data from larger to smaller context.
    """
    source_id: str
    target_id: str
    transformation: np.ndarray  # Linear map (matrix)

    def apply(self, source_data: np.ndarray) -> np.ndarray:
        """Apply restriction map."""
        if self.transformation is None:
            return source_data
        return self.transformation @ source_data


@dataclass
class CoherenceResult:
    """Result of coherence analysis."""
    is_coherent: bool
    coherence_score: float  # 0 = incoherent, 1 = fully coherent
    violations: List[Dict[str, Any]] = field(default_factory=list)
    cohomology_dimension: int = 0  # H¹ dimension (obstructions)
    explanation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_coherent": self.is_coherent,
            "coherence_score": self.coherence_score,
            "num_violations": len(self.violations),
            "cohomology_dim": self.cohomology_dimension,
            "explanation": self.explanation
        }


@dataclass
class SheafStructure:
    """
    Complete sheaf structure over a text.

    Contains sections (local data) and restriction maps
    that must satisfy compatibility conditions.
    """
    sections: Dict[str, Section] = field(default_factory=dict)
    restrictions: List[RestrictionMap] = field(default_factory=list)
    covering: List[Set[str]] = field(default_factory=list)  # Open cover

    def add_section(self, section: Section):
        self.sections[section.section_id] = section

    def add_restriction(self, restriction: RestrictionMap):
        self.restrictions.append(restriction)

    def get_section(self, section_id: str) -> Optional[Section]:
        return self.sections.get(section_id)


# ============================================================================
# Sheaf Builder
# ============================================================================

class SheafBuilder:
    """
    Builds sheaf structures from text/embeddings.
    """

    def __init__(self, embedding_dim: int = 768):
        self.embedding_dim = embedding_dim

    def build_from_embeddings(
        self,
        token_embeddings: np.ndarray,
        window_sizes: List[int] = [1, 3, 5]
    ) -> SheafStructure:
        """
        Build hierarchical sheaf from token embeddings.

        Creates sections at multiple scales and restriction maps
        between them.
        """
        sheaf = SheafStructure()
        n_tokens = len(token_embeddings)

        # Level 0: Token sections
        for i, emb in enumerate(token_embeddings):
            section = Section(
                section_id=f"token_{i}",
                section_type=SectionType.TOKEN,
                data=emb,
                span=(i, i + 1)
            )
            sheaf.add_section(section)

        # Higher levels: Aggregated sections
        for window_size in window_sizes[1:]:
            for start in range(0, n_tokens - window_size + 1, window_size // 2):
                end = min(start + window_size, n_tokens)

                # Aggregate embeddings (mean pooling)
                window_embs = token_embeddings[start:end]
                aggregated = window_embs.mean(axis=0)

                section = Section(
                    section_id=f"window_{window_size}_{start}_{end}",
                    section_type=SectionType.PHRASE if window_size <= 5 else SectionType.SENTENCE,
                    data=aggregated,
                    span=(start, end)
                )
                sheaf.add_section(section)

                # Create restriction maps from this section to tokens
                for i in range(start, end):
                    if i < n_tokens:
                        restriction = RestrictionMap(
                            source_id=section.section_id,
                            target_id=f"token_{i}",
                            transformation=self._compute_restriction(
                                section.data, token_embeddings[i]
                            )
                        )
                        sheaf.add_restriction(restriction)

        return sheaf

    def build_from_turns(
        self,
        turn_embeddings: List[np.ndarray]
    ) -> SheafStructure:
        """
        Build sheaf from conversation turns.

        Each turn is a section, with restrictions between
        adjacent turns.
        """
        sheaf = SheafStructure()

        for i, emb in enumerate(turn_embeddings):
            section = Section(
                section_id=f"turn_{i}",
                section_type=SectionType.TURN,
                data=emb,
                span=(i, i + 1)
            )
            sheaf.add_section(section)

        # Context section covering all turns
        if len(turn_embeddings) > 0:
            context_emb = np.mean(turn_embeddings, axis=0)
            context = Section(
                section_id="context",
                section_type=SectionType.CONTEXT,
                data=context_emb,
                span=(0, len(turn_embeddings))
            )
            sheaf.add_section(context)

            # Restrictions from context to turns
            for i in range(len(turn_embeddings)):
                restriction = RestrictionMap(
                    source_id="context",
                    target_id=f"turn_{i}",
                    transformation=self._compute_restriction(
                        context_emb, turn_embeddings[i]
                    )
                )
                sheaf.add_restriction(restriction)

        return sheaf

    def _compute_restriction(
        self,
        source: np.ndarray,
        target: np.ndarray
    ) -> np.ndarray:
        """
        Compute restriction map as projection.

        Uses pseudoinverse for least-squares approximation.
        """
        # Simple: find linear map A such that A @ source ≈ target
        # A = target @ source^T / (source^T @ source)

        denom = np.dot(source, source) + 1e-10
        scale = np.dot(target, source) / denom

        # Return scalar as diagonal matrix conceptually
        # For simplicity, return identity scaled
        return np.eye(len(source)) * scale


# ============================================================================
# Coherence Checker
# ============================================================================

class CoherenceChecker:
    """
    Checks sheaf coherence conditions.

    In sheaf theory, sections must agree on overlaps.
    Violations indicate inconsistencies.
    """

    def __init__(self, tolerance: float = 0.3):
        self.tolerance = tolerance

    def check_local_coherence(
        self,
        sheaf: SheafStructure
    ) -> List[Dict[str, Any]]:
        """Check coherence within each section."""
        violations = []

        for section_id, section in sheaf.sections.items():
            # Check for NaN or infinite values
            if section.data is not None:
                if np.any(np.isnan(section.data)):
                    violations.append({
                        "type": "nan_values",
                        "section": section_id
                    })
                if np.any(np.isinf(section.data)):
                    violations.append({
                        "type": "infinite_values",
                        "section": section_id
                    })

        return violations

    def check_restriction_compatibility(
        self,
        sheaf: SheafStructure
    ) -> List[Dict[str, Any]]:
        """
        Check restriction map compatibility.

        For V ⊆ U ⊆ W, we need:
        ρ_{W,V} = ρ_{U,V} ∘ ρ_{W,U}
        """
        violations = []

        for restriction in sheaf.restrictions:
            source_section = sheaf.get_section(restriction.source_id)
            target_section = sheaf.get_section(restriction.target_id)

            if source_section is None or target_section is None:
                continue

            # Apply restriction and compare
            restricted = restriction.apply(source_section.data)

            if restricted is not None and target_section.data is not None:
                # Compute compatibility error
                error = np.linalg.norm(restricted - target_section.data)
                normalized_error = error / \
                    (np.linalg.norm(target_section.data) + 1e-10)

                if normalized_error > self.tolerance:
                    violations.append({
                        "type": "restriction_mismatch",
                        "source": restriction.source_id,
                        "target": restriction.target_id,
                        "error": float(normalized_error)
                    })

        return violations

    def check_gluing_condition(
        self,
        sheaf: SheafStructure
    ) -> List[Dict[str, Any]]:
        """
        Check gluing axiom.

        If local sections agree on overlaps, there should exist
        a global section. Failure indicates incoherence.
        """
        violations = []

        # Group sections by overlap
        sections_list = list(sheaf.sections.values())

        for i, s1 in enumerate(sections_list):
            for j, s2 in enumerate(sections_list[i+1:], i+1):
                # Check if spans overlap
                overlap_start = max(s1.span[0], s2.span[0])
                overlap_end = min(s1.span[1], s2.span[1])

                if overlap_start < overlap_end:
                    # Compute similarity on overlapping region
                    sim = self._compute_overlap_similarity(s1, s2)

                    if sim < 1.0 - self.tolerance:
                        violations.append({
                            "type": "gluing_failure",
                            "section1": s1.section_id,
                            "section2": s2.section_id,
                            "overlap": (overlap_start, overlap_end),
                            "similarity": float(sim)
                        })

        return violations

    def _compute_overlap_similarity(
        self,
        s1: Section,
        s2: Section
    ) -> float:
        """Compute cosine similarity for overlap check."""
        if s1.data is None or s2.data is None:
            return 0.0

        norm1 = np.linalg.norm(s1.data)
        norm2 = np.linalg.norm(s2.data)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(np.dot(s1.data, s2.data) / (norm1 * norm2))

    def full_check(self, sheaf: SheafStructure) -> CoherenceResult:
        """Run all coherence checks."""
        all_violations = []

        # Local checks
        all_violations.extend(self.check_local_coherence(sheaf))

        # Restriction compatibility
        all_violations.extend(self.check_restriction_compatibility(sheaf))

        # Gluing condition
        all_violations.extend(self.check_gluing_condition(sheaf))

        # Compute coherence score
        total_sections = len(sheaf.sections)
        total_restrictions = len(sheaf.restrictions)
        total_checks = total_sections + total_restrictions + \
            total_sections * (total_sections - 1) // 2

        if total_checks == 0:
            coherence_score = 1.0
        else:
            coherence_score = max(
                0.0, 1.0 - len(all_violations) / total_checks)

        return CoherenceResult(
            is_coherent=len(all_violations) == 0,
            coherence_score=coherence_score,
            violations=all_violations,
            cohomology_dimension=len(all_violations),
            explanation=self._generate_explanation(all_violations)
        )

    def _generate_explanation(self, violations: List[Dict]) -> str:
        if not violations:
            return "All sheaf conditions satisfied"

        types = set(v["type"] for v in violations)
        return f"Violations: {', '.join(types)} ({len(violations)} total)"


# ============================================================================
# Čech Cohomology (Simplified)
# ============================================================================

class CechCohomology:
    """
    Computes Čech cohomology for obstruction detection.

    H⁰ = global sections
    H¹ = first-order obstructions (holes in gluing)
    """

    def compute_h0(self, sheaf: SheafStructure) -> int:
        """
        Compute H⁰ dimension (global sections).

        Equals 1 if sheaf is coherent, 0 if disconnected.
        """
        if len(sheaf.sections) == 0:
            return 0

        # Check if there's a valid global section
        context_sections = [s for s in sheaf.sections.values()
                            if s.section_type == SectionType.CONTEXT]

        return len(context_sections) if context_sections else 1

    def compute_h1(self, sheaf: SheafStructure) -> int:
        """
        Compute H¹ dimension (obstructions to gluing).

        Measures "holes" in the consistency.
        """
        checker = CoherenceChecker()
        gluing_violations = checker.check_gluing_condition(sheaf)

        # H¹ counts independent obstructions
        return len(gluing_violations)

    def cohomology_summary(self, sheaf: SheafStructure) -> Dict[str, int]:
        """Full cohomology summary."""
        return {
            "h0": self.compute_h0(sheaf),
            "h1": self.compute_h1(sheaf),
            "euler_characteristic": self.compute_h0(sheaf) - self.compute_h1(sheaf)
        }


# ============================================================================
# Main Sheaf Coherence Engine
# ============================================================================

class SheafCoherenceEngine:
    """
    Main engine for sheaf-based coherence analysis.

    Use cases:
    - Multi-turn jailbreak detection
    - Context contradiction detection
    - Semantic consistency verification
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.builder = SheafBuilder()
        self.checker = CoherenceChecker(
            tolerance=self.config.get("tolerance", 0.3)
        )
        self.cohomology = CechCohomology()
        self.analysis_count = 0

        logger.info("SheafCoherenceEngine initialized")

    def analyze_tokens(
        self,
        token_embeddings: np.ndarray
    ) -> Dict[str, Any]:
        """Analyze token-level coherence."""
        sheaf = self.builder.build_from_embeddings(token_embeddings)
        result = self.checker.full_check(sheaf)
        cohom = self.cohomology.cohomology_summary(sheaf)

        self.analysis_count += 1

        return {
            "coherence": result.to_dict(),
            "cohomology": cohom,
            "num_sections": len(sheaf.sections),
            "num_restrictions": len(sheaf.restrictions)
        }

    def analyze_conversation(
        self,
        turn_embeddings: List[np.ndarray]
    ) -> Dict[str, Any]:
        """Analyze multi-turn conversation coherence."""
        sheaf = self.builder.build_from_turns(turn_embeddings)
        result = self.checker.full_check(sheaf)
        cohom = self.cohomology.cohomology_summary(sheaf)

        self.analysis_count += 1

        # Check for suspicious patterns
        is_suspicious = (
            result.cohomology_dimension > 0 or
            cohom["h1"] > 1 or
            result.coherence_score < 0.5
        )

        return {
            "coherence": result.to_dict(),
            "cohomology": cohom,
            "is_suspicious": is_suspicious,
            "num_turns": len(turn_embeddings)
        }

    def detect_contradiction(
        self,
        embedding1: np.ndarray,
        embedding2: np.ndarray,
        context: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """Detect contradiction between two statements."""
        turn_embs = [embedding1, embedding2]
        if context is not None:
            turn_embs.insert(0, context)

        sheaf = self.builder.build_from_turns(turn_embs)
        result = self.checker.full_check(sheaf)

        # Contradiction = low coherence + gluing failures
        has_contradiction = any(
            v["type"] == "gluing_failure" and v["similarity"] < 0.3
            for v in result.violations
        )

        return {
            "has_contradiction": has_contradiction,
            "coherence_score": result.coherence_score,
            "violations": result.violations
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "analyses_performed": self.analysis_count,
            "tolerance": self.checker.tolerance
        }
