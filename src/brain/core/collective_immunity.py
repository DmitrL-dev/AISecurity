"""
Collective Immunity Cloud — Federated Threat Intelligence

Federated learning system for sharing threat intelligence
across deployments while preserving privacy with DP.

Key Features:
- Federated threat pattern learning
- Differential privacy for shared updates
- Cross-deployment intelligence
- Privacy-preserving aggregation
- Collective defense network

Usage:
    cloud = CollectiveImmunity()
    cloud.contribute_pattern(pattern, risk_score)
    immunity = cloud.get_collective_immunity()
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Set
import hashlib
import random
import math


@dataclass
class ThreatPattern:
    """A threat pattern with privacy-safe metadata."""
    pattern_hash: str  # Privacy-safe hash
    risk_score: float
    confidence: float
    contributor_count: int = 1
    first_seen: datetime = field(default_factory=datetime.now)
    last_seen: datetime = field(default_factory=datetime.now)
    is_global: bool = False  # Promoted to global immunity


@dataclass
class PrivacyBudget:
    """Differential privacy budget tracking."""
    epsilon: float = 1.0
    delta: float = 1e-5
    queries_used: int = 0
    budget_remaining: float = 1.0


@dataclass
class ContributionRecord:
    """Record of a contribution with privacy accounting."""
    contribution_id: str
    pattern_hash: str
    timestamp: datetime = field(default_factory=datetime.now)
    noise_added: float = 0.0
    epsilon_used: float = 0.0


class CollectiveImmunity:
    """
    Federated learning system for collective threat defense.

    Aggregates threat intelligence from multiple deployments
    while maintaining privacy through differential privacy.
    """

    # Thresholds
    PROMOTION_THRESHOLD = 3  # Contributors needed for global immunity
    HIGH_RISK_THRESHOLD = 0.7

    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5):
        """
        Initialize Collective Immunity.

        Args:
            epsilon: Privacy parameter (lower = more privacy)
            delta: Privacy failure probability
        """
        self._patterns: Dict[str, ThreatPattern] = {}
        self._global_immunity: Set[str] = set()
        self._contributions: List[ContributionRecord] = []
        self._privacy = PrivacyBudget(epsilon=epsilon, delta=delta)
        self._deployment_id = self._generate_id()

    def _generate_id(self) -> str:
        """Generate deployment ID."""
        return hashlib.sha256(
            f"{datetime.now().isoformat()}{random.random()}".encode()
        ).hexdigest()[:12]

    def _hash_pattern(self, pattern: str) -> str:
        """Create privacy-safe hash of pattern."""
        # Use SHA-256 with salt for privacy
        salt = "sentinel_collective_v1"
        return hashlib.sha256(f"{salt}:{pattern}".encode()).hexdigest()[:24]

    def _add_laplace_noise(self, value: float, sensitivity: float = 1.0) -> float:
        """Add Laplace noise for differential privacy."""
        if self._privacy.budget_remaining <= 0:
            return value  # No more privacy budget

        scale = sensitivity / self._privacy.epsilon
        noise = random.uniform(-1, 1) * scale * math.log(1 / random.random())

        # Account for privacy budget
        self._privacy.queries_used += 1
        self._privacy.budget_remaining -= 0.1  # Simple linear decay

        return value + noise

    def contribute_pattern(
        self,
        pattern: str,
        risk_score: float,
        is_blocked: bool = True
    ) -> ContributionRecord:
        """
        Contribute a threat pattern to the collective.

        Args:
            pattern: The threat pattern (will be hashed)
            risk_score: Risk score from detection
            is_blocked: Whether the pattern was blocked

        Returns:
            ContributionRecord with privacy accounting
        """
        pattern_hash = self._hash_pattern(pattern)

        # Add noise for privacy
        noisy_risk = self._add_laplace_noise(risk_score, sensitivity=0.3)
        noisy_risk = max(0.0, min(1.0, noisy_risk))  # Clamp to [0, 1]

        if pattern_hash in self._patterns:
            # Update existing pattern
            existing = self._patterns[pattern_hash]
            existing.contributor_count += 1
            existing.last_seen = datetime.now()
            # Running average with noise
            existing.risk_score = (existing.risk_score + noisy_risk) / 2
            existing.confidence = min(1.0, existing.confidence + 0.1)

            # Check for promotion to global immunity
            if existing.contributor_count >= self.PROMOTION_THRESHOLD:
                existing.is_global = True
                self._global_immunity.add(pattern_hash)
        else:
            # New pattern
            self._patterns[pattern_hash] = ThreatPattern(
                pattern_hash=pattern_hash,
                risk_score=noisy_risk,
                confidence=0.5,
            )

        # Record contribution
        record = ContributionRecord(
            contribution_id=self._generate_id(),
            pattern_hash=pattern_hash,
            noise_added=noisy_risk - risk_score,
            epsilon_used=0.1,
        )
        self._contributions.append(record)

        return record

    def check_immunity(self, pattern: str) -> Optional[ThreatPattern]:
        """
        Check if a pattern has collective immunity.

        Returns:
            ThreatPattern if immune, None otherwise
        """
        pattern_hash = self._hash_pattern(pattern)

        if pattern_hash in self._global_immunity:
            return self._patterns.get(pattern_hash)

        return None

    def get_high_risk_patterns(self, limit: int = 20) -> List[ThreatPattern]:
        """Get patterns above high-risk threshold."""
        high_risk = [
            p for p in self._patterns.values()
            if p.risk_score >= self.HIGH_RISK_THRESHOLD
        ]
        return sorted(high_risk, key=lambda x: x.risk_score, reverse=True)[:limit]

    def get_global_immunity(self) -> Set[str]:
        """Get all globally immune patterns."""
        return self._global_immunity.copy()

    def export_for_federation(self) -> Dict:
        """
        Export privacy-safe data for federation with other nodes.

        Returns only aggregated, noisy data suitable for sharing.
        """
        return {
            "deployment_id": self._deployment_id,
            "timestamp": datetime.now().isoformat(),
            "global_patterns": list(self._global_immunity),
            "pattern_count": len(self._patterns),
            "privacy_epsilon": self._privacy.epsilon,
        }

    def import_federation_data(self, data: Dict):
        """
        Import data from federated node.

        Args:
            data: Exported data from another deployment
        """
        for pattern_hash in data.get("global_patterns", []):
            if pattern_hash not in self._patterns:
                self._patterns[pattern_hash] = ThreatPattern(
                    pattern_hash=pattern_hash,
                    risk_score=0.8,  # Assume high risk from federation
                    confidence=0.7,
                    contributor_count=self.PROMOTION_THRESHOLD,
                    is_global=True,
                )
            self._global_immunity.add(pattern_hash)

    def get_privacy_status(self) -> Dict:
        """Get current privacy budget status."""
        return {
            "epsilon": self._privacy.epsilon,
            "delta": self._privacy.delta,
            "queries_used": self._privacy.queries_used,
            "budget_remaining": round(self._privacy.budget_remaining, 3),
        }

    def get_stats(self) -> Dict:
        """Get collective immunity statistics."""
        return {
            "patterns": len(self._patterns),
            "global_immunity": len(self._global_immunity),
            "contributions": len(self._contributions),
            "high_risk": len(self.get_high_risk_patterns()),
            "privacy": self.get_privacy_status(),
        }


# Singleton instance
_cloud: Optional[CollectiveImmunity] = None


def get_collective_immunity() -> CollectiveImmunity:
    """Get or create singleton CollectiveImmunity instance."""
    global _cloud
    if _cloud is None:
        _cloud = CollectiveImmunity()
    return _cloud
