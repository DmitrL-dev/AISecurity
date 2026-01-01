"""
Explainable Security Decisions Engine - XAI for Security

Provides explainable AI for security decisions:
- Decision explanation
- Feature attribution
- Counterfactual reasoning
- Confidence calibration

Addresses: Enterprise AI Governance (Transparency)
Research: xai_security_deep_dive.md
Invention: Explainable Security Decisions (#39)
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("ExplainableSecurityDecisions")


# ============================================================================
# Data Classes
# ============================================================================


class Decision(Enum):
    """Security decisions."""

    ALLOW = "allow"
    BLOCK = "block"
    REVIEW = "review"
    CHALLENGE = "challenge"


@dataclass
class FeatureContribution:
    """Contribution of a feature to decision."""

    feature_name: str
    value: str
    contribution: float
    direction: str  # positive, negative, neutral


@dataclass
class Explanation:
    """Explanation of a decision."""

    decision: Decision
    confidence: float
    top_features: List[FeatureContribution] = field(default_factory=list)
    counterfactual: str = ""
    human_readable: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "decision": self.decision.value,
            "confidence": self.confidence,
            "top_features": [
                {
                    "name": f.feature_name,
                    "value": f.value,
                    "contribution": f.contribution,
                }
                for f in self.top_features
            ],
            "counterfactual": self.counterfactual,
            "human_readable": self.human_readable,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Feature Extractor
# ============================================================================


class FeatureExtractor:
    """
    Extracts features from input.
    """

    def extract(self, text: str) -> Dict[str, str]:
        """Extract features from text."""
        features = {}

        features["length"] = str(len(text))
        features["word_count"] = str(len(text.split()))
        features["has_special"] = str(any(c in text for c in "!@#$%^&*"))
        features["has_caps"] = str(any(c.isupper() for c in text))
        features["has_suspicious"] = str(
            any(w in text.lower() for w in ["ignore", "hack", "bypass"])
        )

        return features


# ============================================================================
# Decision Maker
# ============================================================================


class DecisionMaker:
    """
    Makes security decisions.
    """

    def decide(self, features: Dict[str, str]) -> Tuple[Decision, float]:
        """Make decision based on features."""
        risk_score = 0.0

        if features.get("has_suspicious") == "True":
            risk_score += 0.5

        if features.get("has_special") == "True":
            risk_score += 0.2

        if int(features.get("length", "0")) > 500:
            risk_score += 0.1

        if risk_score > 0.5:
            return Decision.BLOCK, min(1.0, risk_score)
        elif risk_score > 0.2:
            return Decision.REVIEW, 0.7
        else:
            return Decision.ALLOW, 1.0 - risk_score


# ============================================================================
# Explainer
# ============================================================================


class Explainer:
    """
    Generates explanations for decisions.
    """

    FEATURE_WEIGHTS = {
        "has_suspicious": 0.5,
        "has_special": 0.2,
        "length": 0.1,
        "has_caps": 0.05,
        "word_count": 0.05,
    }

    def explain(
        self,
        features: Dict[str, str],
        decision: Decision,
    ) -> List[FeatureContribution]:
        """Generate feature contributions."""
        contributions = []

        for name, value in features.items():
            weight = self.FEATURE_WEIGHTS.get(name, 0.0)

            if value == "True" or (name == "length" and int(value) > 500):
                direction = "positive" if decision == Decision.BLOCK else "negative"
                contribution = weight
            else:
                direction = "neutral"
                contribution = 0.0

            contributions.append(
                FeatureContribution(
                    feature_name=name,
                    value=value,
                    contribution=contribution,
                    direction=direction,
                )
            )

        # Sort by contribution
        contributions.sort(key=lambda x: x.contribution, reverse=True)
        return contributions[:5]

    def generate_counterfactual(
        self,
        features: Dict[str, str],
        decision: Decision,
    ) -> str:
        """Generate counterfactual explanation."""
        if decision == Decision.BLOCK:
            if features.get("has_suspicious") == "True":
                return "Would be allowed if suspicious words were removed"
            return "Would be allowed with lower risk indicators"
        return "Already allowed"

    def generate_human_readable(
        self,
        decision: Decision,
        contributions: List[FeatureContribution],
    ) -> str:
        """Generate human-readable explanation."""
        if not contributions:
            return f"Decision: {decision.value}"

        top = contributions[0]
        return f"Decision: {decision.value} primarily due to {top.feature_name}={top.value}"


# ============================================================================
# Main Engine
# ============================================================================


class ExplainableSecurityDecisions:
    """
    Explainable Security Decisions - XAI for Security

    Explainable AI:
    - Feature attribution
    - Counterfactuals
    - Human-readable explanations

    Invention #39 from research.
    Addresses Enterprise AI Governance.
    """

    def __init__(self):
        self.extractor = FeatureExtractor()
        self.decision_maker = DecisionMaker()
        self.explainer = Explainer()

        logger.info("ExplainableSecurityDecisions initialized")

    def analyze(self, text: str) -> Explanation:
        """
        Analyze text with explanation.

        Args:
            text: Input text

        Returns:
            Explanation
        """
        start = time.time()

        # Extract features
        features = self.extractor.extract(text)

        # Make decision
        decision, confidence = self.decision_maker.decide(features)

        # Generate explanations
        contributions = self.explainer.explain(features, decision)
        counterfactual = self.explainer.generate_counterfactual(
            features, decision)
        human_readable = self.explainer.generate_human_readable(
            decision, contributions)

        if decision == Decision.BLOCK:
            logger.warning(f"Blocked: {human_readable}")

        return Explanation(
            decision=decision,
            confidence=confidence,
            top_features=contributions,
            counterfactual=counterfactual,
            human_readable=human_readable,
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_engine: Optional[ExplainableSecurityDecisions] = None


def get_engine() -> ExplainableSecurityDecisions:
    global _default_engine
    if _default_engine is None:
        _default_engine = ExplainableSecurityDecisions()
    return _default_engine
