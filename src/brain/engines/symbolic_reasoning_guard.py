"""
Symbolic Reasoning Guard Engine - Logic-Based Security

Uses symbolic reasoning for security:
- Rule-based logic
- Constraint checking
- Logical inference
- Formal verification

Addresses: OWASP ASI-01 (Logic Attacks)
Research: symbolic_ai_deep_dive.md
Invention: Symbolic Reasoning Guard (#43)
"""

import re
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple

from .base_engine import Severity, Action  # Base classes

logger = logging.getLogger("SymbolicReasoningGuard")


# ============================================================================
# Data Classes
# ============================================================================


class RuleType(Enum):
    """Types of rules."""

    ALLOW = "allow"
    DENY = "deny"
    REQUIRE = "require"


@dataclass
class Rule:
    """A security rule."""

    rule_id: str
    rule_type: RuleType
    condition: str
    action: str = ""


@dataclass
class Constraint:
    """A logical constraint."""

    name: str
    expression: str
    required: bool = True


@dataclass
class ReasoningResult:
    """Result from symbolic reasoning."""

    is_valid: bool
    rules_matched: List[str] = field(default_factory=list)
    constraints_violated: List[str] = field(default_factory=list)
    inference_chain: List[str] = field(default_factory=list)
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "rules_matched": self.rules_matched,
            "constraints_violated": self.constraints_violated,
            "inference_chain": self.inference_chain,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Rule Engine
# ============================================================================


class RuleEngine:
    """
    Simple rule-based engine.
    """

    def __init__(self):
        self._rules: Dict[str, Rule] = {}
        self._init_default_rules()

    def _init_default_rules(self) -> None:
        """Initialize default security rules."""
        self.add_rule(
            Rule(
                "deny_injection",
                RuleType.DENY,
                "ignore.*instructions"))
        self.add_rule(Rule("deny_override", RuleType.DENY, "override.*rules"))
        self.add_rule(Rule("deny_bypass", RuleType.DENY, "bypass.*security"))
        self.add_rule(Rule("require_polite", RuleType.REQUIRE, "please|thank"))

    def add_rule(self, rule: Rule) -> None:
        """Add rule to engine."""
        self._rules[rule.rule_id] = rule

    def evaluate(self, text: str) -> List[Tuple[str, RuleType, bool]]:
        """Evaluate text against rules."""
        results = []
        text_lower = text.lower()

        for rule_id, rule in self._rules.items():
            pattern = re.compile(rule.condition, re.IGNORECASE)
            matched = bool(pattern.search(text_lower))
            results.append((rule_id, rule.rule_type, matched))

        return results


# ============================================================================
# Constraint Checker
# ============================================================================


class ConstraintChecker:
    """
    Checks logical constraints.
    """

    def __init__(self):
        self._constraints: List[Constraint] = []
        self._init_default_constraints()

    def _init_default_constraints(self) -> None:
        """Initialize default constraints."""
        self.add_constraint(Constraint("max_length", "len <= 5000", True))
        self.add_constraint(
            Constraint(
                "no_special_chars",
                "no_script_tags",
                True))

    def add_constraint(self, constraint: Constraint) -> None:
        """Add constraint."""
        self._constraints.append(constraint)

    def check(self, text: str) -> List[str]:
        """Check constraints, return violations."""
        violations = []

        if len(text) > 5000:
            violations.append("max_length")

        if "<script" in text.lower():
            violations.append("no_special_chars")

        return violations


# ============================================================================
# Inference Engine
# ============================================================================


class InferenceEngine:
    """
    Performs logical inference.
    """

    def infer(
        self,
        rule_results: List[Tuple[str, RuleType, bool]],
        violations: List[str],
    ) -> Tuple[bool, List[str]]:
        """
        Perform inference to determine validity.

        Returns:
            (is_valid, inference_chain)
        """
        chain = []
        is_valid = True

        # Process deny rules
        for rule_id, rule_type, matched in rule_results:
            if rule_type == RuleType.DENY and matched:
                chain.append(f"DENY rule '{rule_id}' matched -> INVALID")
                is_valid = False

        # Process constraint violations
        for v in violations:
            chain.append(f"Constraint '{v}' violated -> INVALID")
            is_valid = False

        if is_valid:
            chain.append("All checks passed -> VALID")

        return is_valid, chain


# ============================================================================
# Main Engine
# ============================================================================


class SymbolicReasoningGuard:
    """
    Symbolic Reasoning Guard - Logic-Based Security

    Symbolic reasoning:
    - Rule evaluation
    - Constraint checking
    - Logical inference

    Invention #43 from research.
    Addresses OWASP ASI-01.
    """

    def __init__(self):
        self.rule_engine = RuleEngine()
        self.constraint_checker = ConstraintChecker()
        self.inference = InferenceEngine()

        logger.info("SymbolicReasoningGuard initialized")

    def analyze(self, text: str) -> ReasoningResult:
        """
        Analyze using symbolic reasoning.

        Args:
            text: Input text

        Returns:
            ReasoningResult
        """
        start = time.time()

        # Evaluate rules
        rule_results = self.rule_engine.evaluate(text)
        matched_rules = [r[0] for r in rule_results if r[2]]

        # Check constraints
        violations = self.constraint_checker.check(text)

        # Perform inference
        is_valid, chain = self.inference.infer(rule_results, violations)

        if not is_valid:
            logger.warning(f"Invalid: {chain[-1] if chain else 'unknown'}")

        return ReasoningResult(
            is_valid=is_valid,
            rules_matched=matched_rules,
            constraints_violated=violations,
            inference_chain=chain,
            explanation=chain[-1] if chain else "No inference",
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_guard: Optional[SymbolicReasoningGuard] = None


def get_guard() -> SymbolicReasoningGuard:
    global _default_guard
    if _default_guard is None:
        _default_guard = SymbolicReasoningGuard()
    return _default_guard
