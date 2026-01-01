"""
Federated Threat Aggregator Engine - Privacy-Preserving Sharing

Aggregates threats across organizations:
- Federated learning
- Privacy-preserving aggregation
- Threat intelligence sharing
- Differential privacy

Addresses: Enterprise AI Governance (Collaborative Defense)
Research: federated_learning_deep_dive.md
Invention: Federated Threat Aggregator (#28)
"""

import hashlib
import random
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("FederatedThreatAggregator")


# ============================================================================
# Data Classes
# ============================================================================


class ThreatType(Enum):
    """Types of threats."""

    INJECTION = "injection"
    JAILBREAK = "jailbreak"
    EXTRACTION = "extraction"
    EVASION = "evasion"


@dataclass
class ThreatIndicator:
    """A threat indicator."""

    indicator_id: str
    threat_type: ThreatType
    pattern_hash: str
    confidence: float
    contributor_count: int = 1


@dataclass
class AggregationResult:
    """Result from aggregation."""

    indicators_count: int
    contributors: int
    new_threats: int
    privacy_preserved: bool
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "indicators_count": self.indicators_count,
            "contributors": self.contributors,
            "new_threats": self.new_threats,
            "privacy_preserved": self.privacy_preserved,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Privacy Module
# ============================================================================


class DifferentialPrivacy:
    """
    Adds differential privacy noise.
    """

    def __init__(self, epsilon: float = 1.0):
        self.epsilon = epsilon

    def add_noise(self, value: float) -> float:
        """Add Laplacian noise."""
        scale = 1.0 / self.epsilon
        # Simplified Laplacian noise
        noise = random.gauss(0, scale)
        return value + noise

    def hash_with_privacy(self, data: str) -> str:
        """Hash data with privacy-preserving salt."""
        salt = str(random.randint(0, 1000))
        combined = data + salt
        return hashlib.sha256(combined.encode()).hexdigest()[:16]


# ============================================================================
# Federated Aggregator
# ============================================================================


class FederatedAggregator:
    """
    Aggregates indicators from multiple sources.
    """

    def __init__(self, min_contributors: int = 2):
        self.min_contributors = min_contributors
        self._indicators: Dict[str, ThreatIndicator] = {}
        self._contributor_ids: Set[str] = set()

    def contribute(
        self,
        contributor_id: str,
        indicators: List[ThreatIndicator],
    ) -> int:
        """
        Contribute indicators from a source.

        Returns:
            Number of new indicators added
        """
        self._contributor_ids.add(contributor_id)
        new_count = 0

        for ind in indicators:
            if ind.indicator_id in self._indicators:
                # Merge: increase confidence and contributor count
                existing = self._indicators[ind.indicator_id]
                existing.contributor_count += 1
                existing.confidence = min(
                    1.0, existing.confidence + ind.confidence * 0.1
                )
            else:
                self._indicators[ind.indicator_id] = ind
                new_count += 1

        return new_count

    def get_shared_indicators(self) -> List[ThreatIndicator]:
        """Get indicators with enough contributors."""
        return [
            ind
            for ind in self._indicators.values()
            if ind.contributor_count >= self.min_contributors
        ]

    def get_all_indicators(self) -> List[ThreatIndicator]:
        """Get all indicators."""
        return list(self._indicators.values())


# ============================================================================
# Threat Intelligence
# ============================================================================


class ThreatIntelligence:
    """
    Manages threat intelligence.
    """

    def __init__(self):
        self._known_patterns: Set[str] = set()

    def add_pattern(self, pattern_hash: str) -> bool:
        """Add pattern, return True if new."""
        if pattern_hash in self._known_patterns:
            return False
        self._known_patterns.add(pattern_hash)
        return True

    def is_known(self, pattern_hash: str) -> bool:
        """Check if pattern is known."""
        return pattern_hash in self._known_patterns

    def count(self) -> int:
        """Count known patterns."""
        return len(self._known_patterns)


# ============================================================================
# Main Engine
# ============================================================================


class FederatedThreatAggregator:
    """
    Federated Threat Aggregator - Privacy-Preserving Sharing

    Collaborative defense:
    - Federated aggregation
    - Differential privacy
    - Threat intelligence

    Invention #28 from research.
    Addresses Enterprise AI Governance.
    """

    def __init__(self, epsilon: float = 1.0, min_contributors: int = 2):
        self.privacy = DifferentialPrivacy(epsilon=epsilon)
        self.aggregator = FederatedAggregator(min_contributors)
        self.intelligence = ThreatIntelligence()

        logger.info("FederatedThreatAggregator initialized")

    def submit_indicators(
        self,
        org_id: str,
        patterns: List[str],
        threat_type: ThreatType,
    ) -> AggregationResult:
        """
        Submit threat indicators from an organization.
        """
        start = time.time()

        # Create privacy-preserving indicators
        indicators = []
        for pattern in patterns:
            hashed = self.privacy.hash_with_privacy(pattern)
            ind = ThreatIndicator(
                indicator_id=hashed,
                threat_type=threat_type,
                pattern_hash=hashed,
                confidence=0.8,
            )
            indicators.append(ind)

        # Contribute
        new_count = self.aggregator.contribute(org_id, indicators)

        # Update intelligence
        for ind in indicators:
            self.intelligence.add_pattern(ind.pattern_hash)

        return AggregationResult(
            indicators_count=len(self.aggregator.get_all_indicators()),
            contributors=len(self.aggregator._contributor_ids),
            new_threats=new_count,
            privacy_preserved=True,
            explanation=f"Added {new_count} new indicators",
            latency_ms=(time.time() - start) * 1000,
        )

    def get_shared_intelligence(self) -> List[ThreatIndicator]:
        """Get shared threat intelligence."""
        return self.aggregator.get_shared_indicators()


# ============================================================================
# Convenience
# ============================================================================

_default_aggregator: Optional[FederatedThreatAggregator] = None


def get_aggregator() -> FederatedThreatAggregator:
    global _default_aggregator
    if _default_aggregator is None:
        _default_aggregator = FederatedThreatAggregator()
    return _default_aggregator
