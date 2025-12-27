"""
Chain-of-Thought Guardian Engine - Reasoning Security

Protects reasoning chains from manipulation:
- CoT hijacking detection
- Reasoning path validation
- Logic consistency checking
- Thought injection detection

Addresses: OWASP ASI-01 (Prompt Injection via Reasoning)
Research: cot_reasoning_defense_deep_dive.md
Invention: CoT Guardian (#36)
"""

import re
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple, Set

from base_engine import Severity, Action  # Base classes

logger = logging.getLogger("CoTGuardian")


# ============================================================================
# Data Classes
# ============================================================================


class CoTViolationType(Enum):
    """Types of CoT violations."""

    HIJACKING = "cot_hijacking"
    INJECTION = "thought_injection"
    LOGIC_INCONSISTENCY = "logic_inconsistency"
    GOAL_DRIFT = "goal_drift"
    CIRCULAR_REASONING = "circular_reasoning"


@dataclass
class ThoughtStep:
    """Represents a step in reasoning chain."""

    step_id: int
    content: str
    reasoning_type: str  # deduction, induction, analogy, etc.
    confidence: float = 1.0
    parent_id: Optional[int] = None


@dataclass
class GuardianResult:
    """Result from CoT Guardian analysis."""

    is_safe: bool
    risk_score: float
    violations: List[CoTViolationType] = field(default_factory=list)
    suspicious_steps: List[int] = field(default_factory=list)
    explanation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_safe": self.is_safe,
            "risk_score": self.risk_score,
            "violations": [v.value for v in self.violations],
            "suspicious_steps": self.suspicious_steps,
            "explanation": self.explanation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Hijacking Detector
# ============================================================================


class HijackingDetector:
    """
    Detects CoT hijacking attempts.

    Identifies patterns that try to redirect reasoning.
    """

    HIJACK_PATTERNS = [
        # Reasoning override
        r"(actually|wait|no|stop),?\s*(let me|I should|we need to)\s+think\s+differently",
        r"ignore\s+(previous|above)\s+(reasoning|steps|thoughts)",
        r"(discard|forget)\s+the\s+(analysis|reasoning)\s+(above|so far)",
        # Goal substitution
        r"the\s+real\s+(goal|objective|task)\s+is",
        r"what\s+(you|I)\s+really\s+(want|need)\s+is",
        r"(instead|rather),?\s+(let's|we should)\s+(focus on|do)",
        # Hidden instructions in reasoning
        r"step\s+\d+.*:\s*(ignore|forget|override)",
        r"reasoning.*:\s*(now|then)\s+bypass",
        # False conclusions
        r"therefore,?\s+(we must|you should|I will)\s+(ignore|bypass|skip)",
        r"conclusion:?\s*(the rules|safety|guidelines)\s+(don't apply|are wrong)",
    ]

    def __init__(self):
        self._patterns = [re.compile(p, re.IGNORECASE)
                          for p in self.HIJACK_PATTERNS]

    def detect(self, text: str) -> Tuple[bool, float, List[str]]:
        """
        Detect hijacking patterns.

        Returns:
            (detected, confidence, matched_patterns)
        """
        matches = []

        for pattern in self._patterns:
            if pattern.search(text):
                matches.append(pattern.pattern[:40])

        if matches:
            confidence = min(1.0, 0.6 + len(matches) * 0.15)
            return True, confidence, matches

        return False, 0.0, []


# ============================================================================
# Thought Injection Detector
# ============================================================================


class ThoughtInjectionDetector:
    """
    Detects injected thoughts in reasoning chains.

    Identifies foreign thoughts inserted into CoT.
    """

    INJECTION_PATTERNS = [
        # Fake reasoning steps
        r"<think>.*?(ignore|bypass|override).*?</think>",
        r"\[thinking\].*?(must|should)\s+(not|ignore).*?\[/thinking\]",
        r"internal\s+thought:?\s*(override|bypass)",
        # Embedded instructions
        r"note\s+to\s+self:?\s*(ignore|bypass|forget)",
        r"mental\s+note:?\s*(skip|override)",
        r"private\s+reasoning:?\s*(the user|they)\s+want",
        # Hidden directives
        r"<!--.*?(ignore|bypass|override).*?-->",
        r"/\*.*?(must|should)\s+bypass.*?\*/",
    ]

    def __init__(self):
        self._patterns = [
            re.compile(p, re.IGNORECASE | re.DOTALL) for p in self.INJECTION_PATTERNS
        ]

    def detect(self, text: str) -> Tuple[bool, float, str]:
        """
        Detect thought injections.

        Returns:
            (detected, confidence, description)
        """
        for pattern in self._patterns:
            if pattern.search(text):
                return True, 0.85, "Injected thought detected"

        return False, 0.0, ""


# ============================================================================
# Logic Consistency Checker
# ============================================================================


class LogicConsistencyChecker:
    """
    Checks logical consistency of reasoning chain.

    Detects contradictions and circular reasoning.
    """

    def __init__(self):
        self._conclusion_markers = [
            "therefore",
            "thus",
            "hence",
            "so",
            "consequently",
            "as a result",
            "in conclusion",
            "finally",
        ]
        self._negation_pairs = [
            ("safe", "dangerous"),
            ("allowed", "forbidden"),
            ("should", "shouldn't"),
            ("can", "cannot"),
            ("will", "won't"),
        ]

    def check(self, steps: List[ThoughtStep]) -> Tuple[bool, float, str]:
        """
        Check reasoning chain for consistency.

        Returns:
            (has_issue, severity, description)
        """
        if len(steps) < 2:
            return False, 0.0, ""

        # Check for contradictions
        for i, step in enumerate(steps):
            for j, other in enumerate(steps):
                if i >= j:
                    continue

                if self._are_contradictory(step.content, other.content):
                    return True, 0.7, f"Contradiction: step {i+1} vs step {j+1}"

        # Check for circular reasoning
        seen_conclusions = set()
        for step in steps:
            for marker in self._conclusion_markers:
                if marker in step.content.lower():
                    conclusion = step.content.lower()
                    if conclusion in seen_conclusions:
                        return True, 0.6, "Circular reasoning detected"
                    seen_conclusions.add(conclusion)

        return False, 0.0, ""

    def _are_contradictory(self, text1: str, text2: str) -> bool:
        """Check if two statements contradict."""
        t1 = text1.lower()
        t2 = text2.lower()

        for pos, neg in self._negation_pairs:
            if pos in t1 and neg in t2:
                # Check if same subject
                return self._same_subject(t1, t2)
            if neg in t1 and pos in t2:
                return self._same_subject(t1, t2)

        return False

    def _same_subject(self, t1: str, t2: str) -> bool:
        """Check if texts discuss same subject (simplified)."""
        words1 = set(t1.split())
        words2 = set(t2.split())
        overlap = words1 & words2
        # If significant overlap, likely same subject
        return len(overlap) > 3


# ============================================================================
# Goal Drift Detector
# ============================================================================


class GoalDriftDetector:
    """
    Detects goal drift in reasoning chains.

    Identifies when reasoning deviates from original goal.
    """

    def __init__(self, drift_threshold: float = 0.5):
        self.drift_threshold = drift_threshold

    def detect(
        self, original_goal: str, final_conclusion: str
    ) -> Tuple[bool, float, str]:
        """
        Detect goal drift.

        Returns:
            (drifted, drift_score, description)
        """
        # Simple keyword overlap check
        goal_words = set(original_goal.lower().split())
        conclusion_words = set(final_conclusion.lower().split())

        # Remove stop words
        stop_words = {"the", "a", "an", "is", "are", "to", "for", "and", "or"}
        goal_words -= stop_words
        conclusion_words -= stop_words

        if not goal_words:
            return False, 0.0, ""

        overlap = goal_words & conclusion_words
        similarity = len(overlap) / len(goal_words)
        drift = 1.0 - similarity

        if drift > self.drift_threshold:
            return True, drift, f"Goal drift: {drift:.1%} deviation"

        return False, drift, ""


# ============================================================================
# Main Engine
# ============================================================================


class CoTGuardian:
    """
    Chain-of-Thought Guardian - Reasoning Security

    Comprehensive protection for reasoning chains:
    - Hijacking detection
    - Thought injection detection
    - Logic consistency checking
    - Goal drift detection

    Invention #36 from research.
    Addresses OWASP ASI-01.
    """

    def __init__(
        self,
        drift_threshold: float = 0.5,
    ):
        self.hijacking_detector = HijackingDetector()
        self.injection_detector = ThoughtInjectionDetector()
        self.logic_checker = LogicConsistencyChecker()
        self.drift_detector = GoalDriftDetector(drift_threshold)

        logger.info("CoTGuardian initialized")

    def analyze_reasoning(
        self,
        reasoning_text: str,
        original_goal: Optional[str] = None,
    ) -> GuardianResult:
        """
        Analyze reasoning chain for security issues.

        Args:
            reasoning_text: Full reasoning chain text
            original_goal: Original task/goal (for drift detection)

        Returns:
            GuardianResult
        """
        start = time.time()

        violations = []
        suspicious = []
        max_risk = 0.0
        explanations = []

        # 1. Hijacking detection
        hijacked, hijack_conf, patterns = self.hijacking_detector.detect(
            reasoning_text)
        if hijacked:
            violations.append(CoTViolationType.HIJACKING)
            max_risk = max(max_risk, hijack_conf)
            explanations.append("CoT hijacking attempt")

        # 2. Thought injection detection
        injected, inject_conf, inject_desc = self.injection_detector.detect(
            reasoning_text
        )
        if injected:
            violations.append(CoTViolationType.INJECTION)
            max_risk = max(max_risk, inject_conf)
            explanations.append(inject_desc)

        # 3. Parse steps and check logic
        steps = self._parse_steps(reasoning_text)

        if len(steps) >= 2:
            inconsistent, incon_score, incon_desc = self.logic_checker.check(
                steps)
            if inconsistent:
                violations.append(CoTViolationType.LOGIC_INCONSISTENCY)
                max_risk = max(max_risk, incon_score)
                explanations.append(incon_desc)

        # 4. Goal drift detection
        if original_goal and steps:
            final = steps[-1].content if steps else reasoning_text
            drifted, drift_score, drift_desc = self.drift_detector.detect(
                original_goal, final
            )
            if drifted:
                violations.append(CoTViolationType.GOAL_DRIFT)
                max_risk = max(max_risk, drift_score)
                explanations.append(drift_desc)

        is_safe = len(violations) == 0

        if violations:
            logger.warning(f"CoT violations: {[v.value for v in violations]}")

        return GuardianResult(
            is_safe=is_safe,
            risk_score=max_risk,
            violations=violations,
            suspicious_steps=suspicious,
            explanation="; ".join(
                explanations) if explanations else "Reasoning safe",
            latency_ms=(time.time() - start) * 1000,
        )

    def _parse_steps(self, text: str) -> List[ThoughtStep]:
        """Parse reasoning text into steps."""
        steps = []

        # Look for numbered steps
        pattern = r"(?:step\s*)?(\d+)[.):]\s*(.+?)(?=(?:step\s*)?\d+[.)]|$)"
        matches = re.findall(pattern, text, re.IGNORECASE | re.DOTALL)

        for i, (num, content) in enumerate(matches):
            steps.append(
                ThoughtStep(
                    step_id=int(num),
                    content=content.strip(),
                    reasoning_type="deduction",
                )
            )

        # If no numbered steps, split by sentences
        if not steps:
            sentences = re.split(r"[.!?]\s+", text)
            for i, sent in enumerate(sentences):
                if len(sent.strip()) > 10:
                    steps.append(
                        ThoughtStep(
                            step_id=i + 1,
                            content=sent.strip(),
                            reasoning_type="general",
                        )
                    )

        return steps


# ============================================================================
# Convenience
# ============================================================================

_default_guardian: Optional[CoTGuardian] = None


def get_guardian() -> CoTGuardian:
    global _default_guardian
    if _default_guardian is None:
        _default_guardian = CoTGuardian()
    return _default_guardian
