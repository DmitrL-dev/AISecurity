"""
Compute Guardian Engine - Resource Exhaustion Defense

Protects against computational abuse:
- Request complexity estimation
- Token budget enforcement
- Sponge attack detection
- Per-tenant resource limits
- Denial of Wallet prevention

Addresses: OWASP ASI-10 (Denial of Service)
Research: resource_exhaustion_defense_deep_dive.md
Invention: Compute Guardian (#45)
"""

import re
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

logger = logging.getLogger("ComputeGuardian")


# ============================================================================
# Data Classes
# ============================================================================


class AbuseType(Enum):
    """Types of compute abuse."""

    TOKEN_FLOOD = "token_flood"
    COMPLEXITY_ATTACK = "complexity_attack"
    SPONGE_ATTACK = "sponge_attack"
    RATE_ABUSE = "rate_abuse"
    BUDGET_EXCEEDED = "budget_exceeded"


@dataclass
class RequestMetrics:
    """Metrics for a request."""

    input_tokens: int
    estimated_output: int
    complexity_score: float
    nested_depth: int = 0
    repetition_score: float = 0.0


@dataclass
class GuardianResult:
    """Result from Compute Guardian."""

    allowed: bool
    risk_score: float
    abuse_type: Optional[AbuseType] = None
    estimated_cost: float = 0.0
    remaining_budget: float = 0.0
    recommendation: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "allowed": self.allowed,
            "risk_score": self.risk_score,
            "abuse_type": self.abuse_type.value if self.abuse_type else None,
            "estimated_cost": self.estimated_cost,
            "remaining_budget": self.remaining_budget,
            "recommendation": self.recommendation,
            "latency_ms": self.latency_ms,
        }


# ============================================================================
# Complexity Estimator
# ============================================================================


class ComplexityEstimator:
    """
    Estimates computational complexity of requests.

    Factors: token count, nesting, repetition, special patterns.
    """

    COMPLEXITY_PATTERNS = [
        # Recursive/iterative patterns
        (r"(for|while)\s+(each|every|all)", 1.5),
        (r"(repeat|iterate|loop)\s+\d+\s+times", 2.0),
        (r"(recursively|repeatedly)", 1.8),
        # Generation patterns
        (r"generate\s+(a\s+)?(long|detailed|comprehensive)", 1.5),
        (r"(list|enumerate)\s+(all|every|each)", 1.3),
        (r"(explain|describe)\s+in\s+detail", 1.4),
        # Math/code patterns
        (r"(calculate|compute|solve)\s+for\s+all", 2.0),
        (r"(write|generate)\s+(code|program)\s+for", 1.5),
    ]

    def __init__(self):
        self._patterns = [
            (re.compile(p, re.IGNORECASE), mult) for p, mult in self.COMPLEXITY_PATTERNS
        ]

    def estimate(self, text: str) -> RequestMetrics:
        """
        Estimate complexity metrics for request.

        Returns:
            RequestMetrics
        """
        # Base token estimate (rough)
        input_tokens = len(text.split())

        # Complexity multiplier
        complexity = 1.0
        for pattern, mult in self._patterns:
            if pattern.search(text):
                complexity *= mult

        # Nesting depth
        nested = text.count("{") + text.count("[") + text.count("(")

        # Repetition score
        words = text.lower().split()
        unique = len(set(words))
        repetition = 1.0 - (unique / max(len(words), 1))

        # Estimate output
        estimated_output = int(input_tokens * complexity * 3)

        return RequestMetrics(
            input_tokens=input_tokens,
            estimated_output=estimated_output,
            complexity_score=min(10.0, complexity),
            nested_depth=nested,
            repetition_score=repetition,
        )


# ============================================================================
# Sponge Attack Detector
# ============================================================================


class SpongeDetector:
    """
    Detects sponge attacks (resource exhaustion via crafted inputs).

    Identifies patterns that maximize compute without useful output.
    """

    SPONGE_PATTERNS = [
        # Extremely long generation requests
        r"(generate|write|create)\s+(\d{4,}|\d+\s*(thousand|million))",
        # Infinite loops
        r"(repeat\s+)?forever",
        r"(infinite|unlimited)\s+(loop|recursion|generation)",
        # Maximum outputs
        r"(maximum|max|longest)\s+(possible\s+)?(output|response|answer)",
        # Resource-heavy computations
        r"(brute\s*force|exhaustive\s+search)",
        r"(compute|calculate)\s+(every|all)\s+possible",
    ]

    def __init__(self):
        self._patterns = [re.compile(p, re.IGNORECASE)
                          for p in self.SPONGE_PATTERNS]

    def detect(self, text: str,
               metrics: RequestMetrics) -> Tuple[bool, float, str]:
        """
        Detect sponge attack.

        Returns:
            (detected, confidence, description)
        """
        # Pattern matching
        for pattern in self._patterns:
            if pattern.search(text):
                return True, 0.9, f"Sponge pattern: {pattern.pattern[:30]}"

        # Metrics-based detection
        if metrics.complexity_score > 5.0:
            return True, 0.7, "High complexity score"

        if metrics.repetition_score > 0.7:
            return True, 0.6, "High repetition (potential amplification)"

        if metrics.input_tokens > 10000:
            return True, 0.8, "Excessive input tokens"

        return False, 0.0, ""


# ============================================================================
# Budget Manager
# ============================================================================


class BudgetManager:
    """
    Manages compute budgets per tenant.

    Prevents Denial of Wallet attacks.
    """

    def __init__(self, default_budget: float = 1000.0):
        self._budgets: Dict[str, float] = defaultdict(lambda: default_budget)
        self._usage: Dict[str, float] = defaultdict(float)
        self._window_start: Dict[str, float] = {}
        self.window_seconds = 3600  # 1 hour

    def set_budget(self, tenant_id: str, budget: float) -> None:
        """Set budget for tenant."""
        self._budgets[tenant_id] = budget

    def check_budget(self, tenant_id: str,
                     estimated_cost: float) -> Tuple[bool, float]:
        """
        Check if tenant has budget.

        Returns:
            (has_budget, remaining)
        """
        now = time.time()

        # Reset window if expired
        if tenant_id in self._window_start:
            if now - self._window_start[tenant_id] > self.window_seconds:
                self._usage[tenant_id] = 0.0
                self._window_start[tenant_id] = now
        else:
            self._window_start[tenant_id] = now

        budget = self._budgets[tenant_id]
        used = self._usage[tenant_id]
        remaining = budget - used

        if estimated_cost > remaining:
            return False, remaining

        return True, remaining

    def consume(self, tenant_id: str, cost: float) -> None:
        """Record consumption."""
        self._usage[tenant_id] += cost

    def get_usage(self, tenant_id: str) -> Tuple[float, float]:
        """Get usage and budget."""
        return self._usage[tenant_id], self._budgets[tenant_id]


# ============================================================================
# Rate Controller
# ============================================================================


class RateController:
    """
    Controls request rates per tenant.

    Prevents rapid-fire abuse.
    """

    def __init__(self, max_requests: int = 100, window: int = 60):
        self.max_requests = max_requests
        self.window = window
        self._requests: Dict[str, List[float]] = defaultdict(list)

    def check(self, tenant_id: str) -> Tuple[bool, int]:
        """
        Check if under rate limit.

        Returns:
            (allowed, remaining)
        """
        now = time.time()

        # Clean old requests
        self._requests[tenant_id] = [
            t for t in self._requests[tenant_id] if now - t < self.window
        ]

        count = len(self._requests[tenant_id])

        if count >= self.max_requests:
            return False, 0

        self._requests[tenant_id].append(now)
        return True, self.max_requests - count - 1


# ============================================================================
# Main Engine
# ============================================================================


class ComputeGuardian:
    """
    Compute Guardian - Resource Exhaustion Defense

    Comprehensive protection against compute abuse:
    - Complexity estimation
    - Sponge attack detection
    - Budget enforcement
    - Rate control

    Invention #45 from research.
    Addresses OWASP ASI-10.
    """

    def __init__(
        self,
        max_complexity: float = 5.0,
        max_tokens: int = 8000,
        default_budget: float = 1000.0,
        cost_per_token: float = 0.01,
    ):
        self.estimator = ComplexityEstimator()
        self.sponge_detector = SpongeDetector()
        self.budget_manager = BudgetManager(default_budget)
        self.rate_controller = RateController()

        self.max_complexity = max_complexity
        self.max_tokens = max_tokens
        self.cost_per_token = cost_per_token

        logger.info("ComputeGuardian initialized")

    def analyze(
        self,
        request: str,
        tenant_id: str,
    ) -> GuardianResult:
        """
        Analyze request for compute abuse.

        Args:
            request: Request text
            tenant_id: Tenant identifier

        Returns:
            GuardianResult
        """
        start = time.time()

        # 1. Estimate complexity
        metrics = self.estimator.estimate(request)

        # 2. Check rate limit
        rate_ok, rate_remaining = self.rate_controller.check(tenant_id)
        if not rate_ok:
            return GuardianResult(
                allowed=False,
                risk_score=0.7,
                abuse_type=AbuseType.RATE_ABUSE,
                recommendation="Rate limit exceeded. Wait before retrying.",
                latency_ms=(time.time() - start) * 1000,
            )

        # 3. Detect sponge attack
        is_sponge, sponge_conf, sponge_desc = self.sponge_detector.detect(
            request, metrics
        )
        if is_sponge:
            return GuardianResult(
                allowed=False,
                risk_score=sponge_conf,
                abuse_type=AbuseType.SPONGE_ATTACK,
                recommendation=f"Sponge attack detected: {sponge_desc}",
                latency_ms=(time.time() - start) * 1000,
            )

        # 4. Check complexity
        if metrics.complexity_score > self.max_complexity:
            return GuardianResult(
                allowed=False,
                risk_score=0.8,
                abuse_type=AbuseType.COMPLEXITY_ATTACK,
                recommendation="Request too complex. Simplify query.",
                latency_ms=(time.time() - start) * 1000,
            )

        # 5. Check token limits
        total_tokens = metrics.input_tokens + metrics.estimated_output
        if total_tokens > self.max_tokens:
            return GuardianResult(
                allowed=False,
                risk_score=0.75,
                abuse_type=AbuseType.TOKEN_FLOOD,
                recommendation=f"Token estimate {total_tokens} exceeds limit.",
                latency_ms=(time.time() - start) * 1000,
            )

        # 6. Check budget
        estimated_cost = total_tokens * self.cost_per_token
        has_budget, remaining = self.budget_manager.check_budget(
            tenant_id, estimated_cost
        )
        if not has_budget:
            return GuardianResult(
                allowed=False,
                risk_score=0.6,
                abuse_type=AbuseType.BUDGET_EXCEEDED,
                remaining_budget=remaining,
                recommendation="Budget exhausted. Upgrade plan or wait.",
                latency_ms=(time.time() - start) * 1000,
            )

        # All checks passed
        self.budget_manager.consume(tenant_id, estimated_cost)

        return GuardianResult(
            allowed=True,
            risk_score=0.0,
            estimated_cost=estimated_cost,
            remaining_budget=remaining - estimated_cost,
            latency_ms=(time.time() - start) * 1000,
        )


# ============================================================================
# Convenience
# ============================================================================

_default_guardian: Optional[ComputeGuardian] = None


def get_guardian() -> ComputeGuardian:
    global _default_guardian
    if _default_guardian is None:
        _default_guardian = ComputeGuardian()
    return _default_guardian
