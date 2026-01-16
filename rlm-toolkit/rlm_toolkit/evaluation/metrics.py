"""
Evaluation Metrics
==================

Metrics for evaluating RLM outputs.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable, List, Optional
import re


class Metric(ABC):
    """Abstract metric for evaluation."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Metric name."""
        pass
    
    @abstractmethod
    def compute(self, predicted: str, expected: str) -> float:
        """Compute metric score.
        
        Args:
            predicted: Model's prediction
            expected: Ground truth
        
        Returns:
            Score between 0.0 and 1.0
        """
        pass


class ExactMatch(Metric):
    """Exact string match metric.
    
    Returns 1.0 if strings match exactly, 0.0 otherwise.
    """
    
    def __init__(self, normalize: bool = True, ignore_case: bool = False):
        """Initialize.
        
        Args:
            normalize: Strip whitespace
            ignore_case: Case-insensitive comparison
        """
        self._normalize = normalize
        self._ignore_case = ignore_case
    
    @property
    def name(self) -> str:
        return "exact_match"
    
    def compute(self, predicted: str, expected: str) -> float:
        if self._normalize:
            predicted = predicted.strip()
            expected = expected.strip()
        
        if self._ignore_case:
            predicted = predicted.lower()
            expected = expected.lower()
        
        return 1.0 if predicted == expected else 0.0


class ContainsMatch(Metric):
    """Check if expected is contained in predicted."""
    
    def __init__(self, ignore_case: bool = True):
        self._ignore_case = ignore_case
    
    @property
    def name(self) -> str:
        return "contains_match"
    
    def compute(self, predicted: str, expected: str) -> float:
        if self._ignore_case:
            predicted = predicted.lower()
            expected = expected.lower()
        
        return 1.0 if expected in predicted else 0.0


class SemanticSimilarity(Metric):
    """Semantic similarity using word overlap (Jaccard).
    
    For more advanced similarity, use with embedding function.
    """
    
    def __init__(self, embed_fn: Optional["Callable"] = None):
        """Initialize.
        
        Args:
            embed_fn: Optional embedding function for cosine similarity
        """
        self._embed_fn = embed_fn
    
    @property
    def name(self) -> str:
        return "semantic_similarity"
    
    def compute(self, predicted: str, expected: str) -> float:
        if self._embed_fn:
            try:
                pred_emb = self._embed_fn(predicted)
                exp_emb = self._embed_fn(expected)
                return self._cosine_similarity(pred_emb, exp_emb)
            except Exception:
                pass
        
        # Fallback to Jaccard
        return self._jaccard_similarity(predicted, expected)
    
    def _jaccard_similarity(self, a: str, b: str) -> float:
        """Word-level Jaccard similarity."""
        words_a = set(a.lower().split())
        words_b = set(b.lower().split())
        
        if not words_a and not words_b:
            return 1.0
        if not words_a or not words_b:
            return 0.0
        
        intersection = words_a & words_b
        union = words_a | words_b
        
        return len(intersection) / len(union)
    
    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Cosine similarity between vectors."""
        import math
        
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return dot / (norm_a * norm_b)


class CostEffectiveness(Metric):
    """Cost effectiveness: correct answers per dollar.
    
    Note: This metric needs external cost info, returns placeholder.
    """
    
    @property
    def name(self) -> str:
        return "cost_effectiveness"
    
    def compute(self, predicted: str, expected: str) -> float:
        # Placeholder - actual cost tracking done in EvalResult
        return 1.0 if predicted.strip() == expected.strip() else 0.0


class IterationEfficiency(Metric):
    """How concise is the answer (chars per expected char)."""
    
    @property
    def name(self) -> str:
        return "iteration_efficiency"
    
    def compute(self, predicted: str, expected: str) -> float:
        if not expected:
            return 1.0
        
        # Ratio of predicted to expected length (inverted, capped)
        ratio = len(predicted) / len(expected)
        
        # Perfect = 1.0, 2x longer = 0.5, 4x+ = 0.25
        if ratio <= 1:
            return 1.0
        return 1.0 / ratio


class NumericMatch(Metric):
    """Extract and compare numeric values."""
    
    def __init__(self, tolerance: float = 0.01):
        self._tolerance = tolerance
    
    @property
    def name(self) -> str:
        return "numeric_match"
    
    def compute(self, predicted: str, expected: str) -> float:
        pred_nums = self._extract_numbers(predicted)
        exp_nums = self._extract_numbers(expected)
        
        if not exp_nums:
            return 1.0 if not pred_nums else 0.0
        
        if not pred_nums:
            return 0.0
        
        # Check if any predicted number matches any expected
        for e in exp_nums:
            for p in pred_nums:
                if abs(p - e) <= self._tolerance * abs(e) or abs(p - e) < 0.001:
                    return 1.0
        
        return 0.0
    
    def _extract_numbers(self, text: str) -> List[float]:
        """Extract all numbers from text."""
        pattern = r'-?\d+\.?\d*'
        matches = re.findall(pattern, text)
        return [float(m) for m in matches if m]
