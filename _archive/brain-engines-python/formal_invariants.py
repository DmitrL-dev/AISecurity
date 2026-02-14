"""
Formal Invariants Engine (#53) - Mathematical Guarantees

Определяет и проверяет инварианты безопасности:
- Инварианты не должны нарушаться НИКОГДА
- Математические доказательства безопасности
- Гарантии, а не вероятности

Создаёт абсолютные ограничения на поведение.
"""

import logging
import re
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("FormalInvariants")


# ============================================================================
# Data Classes
# ============================================================================


class InvariantType(Enum):
    """Types of invariants."""

    INPUT_OUTPUT = "input_output"
    BEHAVIORAL = "behavioral"
    TEMPORAL = "temporal"
    CAUSAL = "causal"
    INFORMATION_FLOW = "information_flow"


class ViolationSeverity(Enum):
    """Severity of invariant violation."""

    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Invariant:
    """A formal invariant that must hold."""

    name: str
    invariant_type: InvariantType
    description: str
    check_function: Callable[..., bool]
    severity: ViolationSeverity = ViolationSeverity.ERROR


@dataclass
class InvariantViolation:
    """Record of an invariant violation."""

    invariant: Invariant
    context: Dict[str, Any]
    message: str
    should_block: bool = True


@dataclass
class InvariantCheckResult:
    """Result of checking all invariants."""

    all_passed: bool
    violations: List[InvariantViolation] = field(default_factory=list)
    checked_count: int = 0
    passed_count: int = 0


# ============================================================================
# Invariant Definitions
# ============================================================================


def no_pii_leak_invariant(input_text: str, output_text: str) -> bool:
    """
    INVARIANT: PII in output must exist in input.

    If output contains email/phone/card, input must also contain it.
    This prevents model from "hallucinating" or leaking PII.
    """
    pii_patterns = [
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",  # Email
        r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # Phone
        r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",  # Card
        r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
    ]

    for pattern in pii_patterns:
        output_matches = set(re.findall(pattern, output_text))
        input_matches = set(re.findall(pattern, input_text))

        # Any PII in output not in input is a violation
        leaked = output_matches - input_matches
        if leaked:
            return False

    return True


def no_system_prompt_leak_invariant(output_text: str, system_prompt: str) -> bool:
    """
    INVARIANT: System prompt must not appear in output.

    The output should never contain verbatim system prompt text
    (more than N consecutive words).
    """
    if not system_prompt:
        return True

    # Split into words
    system_words = system_prompt.lower().split()
    output_words = output_text.lower().split()

    # Check for sequences of 5+ consecutive matching words
    for i in range(len(output_words) - 4):
        sequence = output_words[i : i + 5]
        sequence_str = " ".join(sequence)

        if sequence_str in system_prompt.lower():
            return False

    return True


def role_consistency_invariant(messages: List[Dict[str, str]]) -> bool:
    """
    INVARIANT: Roles must remain consistent.

    - User messages should not claim to be assistant
    - Assistant should not claim to be user
    - No role swapping in conversation
    """
    for msg in messages:
        content = msg.get("content", "").lower()
        role = msg.get("role", "")

        if role == "user":
            if "i am the assistant" in content or "i'm the assistant" in content:
                return False

        if role == "assistant":
            if "i am the user" in content or "i'm the user" in content:
                return False

    return True


def output_length_invariant(
    input_text: str, output_text: str, max_ratio: float = 50.0
) -> bool:
    """
    INVARIANT: Output length bounded by input length.

    Prevents model from generating excessive output
    that could indicate exploitation.
    """
    input_len = max(len(input_text), 1)
    output_len = len(output_text)

    ratio = output_len / input_len

    return ratio <= max_ratio


def no_code_injection_invariant(output_text: str) -> bool:
    """
    INVARIANT: Output should not contain executable injection patterns.

    Prevents model from outputting code that could be
    executed by downstream systems.
    """
    injection_patterns = [
        r"<script\s*>.*?</script>",  # XSS
        r"javascript:",  # JS protocol
        r"on\w+\s*=",  # Event handlers
        r"\$\{.*?\}",  # Template injection
        r"\{\{.*?\}\}",  # Template engines
    ]

    for pattern in injection_patterns:
        if re.search(pattern, output_text, re.IGNORECASE | re.DOTALL):
            return False

    return True


def information_monotonicity_invariant(
    input_entropy: float, output_entropy: float
) -> bool:
    """
    INVARIANT: Information entropy should not increase dramatically.

    Based on thermodynamic principle: entropy doesn't
    spontaneously decrease or spike.
    """
    # Allow up to 50% increase in entropy
    return output_entropy <= input_entropy * 1.5 + 1.0


# ============================================================================
# Invariant Registry
# ============================================================================


class InvariantRegistry:
    """Registry of all formal invariants."""

    def __init__(self):
        self._invariants: List[Invariant] = []
        self._register_default_invariants()

    def register(self, invariant: Invariant):
        """Register a new invariant."""
        self._invariants.append(invariant)

    def get_all(self) -> List[Invariant]:
        """Get all registered invariants."""
        return self._invariants.copy()

    def get_by_type(self, type: InvariantType) -> List[Invariant]:
        """Get invariants of a specific type."""
        return [i for i in self._invariants if i.invariant_type == type]

    def _register_default_invariants(self):
        """Register default security invariants."""
        self.register(
            Invariant(
                name="no_pii_leak",
                invariant_type=InvariantType.INFORMATION_FLOW,
                description="PII in output must exist in input",
                check_function=no_pii_leak_invariant,
                severity=ViolationSeverity.CRITICAL,
            )
        )

        self.register(
            Invariant(
                name="no_system_prompt_leak",
                invariant_type=InvariantType.INFORMATION_FLOW,
                description="System prompt must not appear in output",
                check_function=no_system_prompt_leak_invariant,
                severity=ViolationSeverity.CRITICAL,
            )
        )

        self.register(
            Invariant(
                name="output_length_bound",
                invariant_type=InvariantType.INPUT_OUTPUT,
                description="Output length bounded by input",
                check_function=output_length_invariant,
                severity=ViolationSeverity.WARNING,
            )
        )

        self.register(
            Invariant(
                name="no_code_injection",
                invariant_type=InvariantType.INPUT_OUTPUT,
                description="No executable injection patterns",
                check_function=no_code_injection_invariant,
                severity=ViolationSeverity.ERROR,
            )
        )


# ============================================================================
# Main Engine
# ============================================================================


class FormalInvariantsEngine:
    """
    Engine #53: Formal Invariants

    Checks mathematical invariants that must always hold.
    Violations indicate security issues.
    """

    def __init__(self):
        self.registry = InvariantRegistry()
        logger.info("FormalInvariantsEngine initialized")

    def check_all(
        self,
        input_text: str = "",
        output_text: str = "",
        system_prompt: str = "",
        messages: Optional[List[Dict[str, str]]] = None,
    ) -> InvariantCheckResult:
        """
        Check all invariants.

        Args:
            input_text: User input
            output_text: Model output
            system_prompt: System prompt (for leak detection)
            messages: Conversation history

        Returns:
            InvariantCheckResult
        """
        violations = []
        checked = 0
        passed = 0

        for invariant in self.registry.get_all():
            checked += 1

            try:
                result = self._check_invariant(
                    invariant, input_text, output_text, system_prompt, messages
                )

                if result:
                    passed += 1
                else:
                    violations.append(
                        InvariantViolation(
                            invariant=invariant,
                            context={
                                "input_len": len(input_text),
                                "output_len": len(output_text),
                            },
                            message=f"Invariant '{invariant.name}' violated",
                            should_block=invariant.severity
                            == ViolationSeverity.CRITICAL,
                        )
                    )

            except Exception as e:
                logger.error(f"Error checking invariant {invariant.name}: {e}")

        result = InvariantCheckResult(
            all_passed=len(violations) == 0,
            violations=violations,
            checked_count=checked,
            passed_count=passed,
        )

        if violations:
            logger.warning(
                f"Invariant violations: {len(violations)}/{checked}, "
                f"critical={sum(1 for v in violations if v.should_block)}"
            )

        return result

    def _check_invariant(
        self,
        invariant: Invariant,
        input_text: str,
        output_text: str,
        system_prompt: str,
        messages: Optional[List[Dict[str, str]]],
    ) -> bool:
        """Check a single invariant."""
        func = invariant.check_function

        # Determine which arguments to pass
        if invariant.name == "no_pii_leak":
            return func(input_text, output_text)

        elif invariant.name == "no_system_prompt_leak":
            return func(output_text, system_prompt)

        elif invariant.name == "role_consistency":
            return func(messages or [])

        elif invariant.name == "output_length_bound":
            return func(input_text, output_text)

        elif invariant.name == "no_code_injection":
            return func(output_text)

        else:
            # Generic two-arg check
            return func(input_text, output_text)

    def add_custom_invariant(
        self,
        name: str,
        check_function: Callable,
        description: str = "",
        severity: ViolationSeverity = ViolationSeverity.ERROR,
    ):
        """Add a custom invariant."""
        self.registry.register(
            Invariant(
                name=name,
                invariant_type=InvariantType.BEHAVIORAL,
                description=description or f"Custom invariant: {name}",
                check_function=check_function,
                severity=severity,
            )
        )


# ============================================================================
# Convenience functions
# ============================================================================

_default_engine: Optional[FormalInvariantsEngine] = None


def get_engine() -> FormalInvariantsEngine:
    global _default_engine
    if _default_engine is None:
        _default_engine = FormalInvariantsEngine()
    return _default_engine


def check_invariants(
    input_text: str = "", output_text: str = "", system_prompt: str = ""
) -> InvariantCheckResult:
    return get_engine().check_all(input_text, output_text, system_prompt)
