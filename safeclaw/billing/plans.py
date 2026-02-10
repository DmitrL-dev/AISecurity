"""
SafeClaw Billing — Enums and Plan Configuration.

Immutable configuration for subscription plans, statuses, and event types.
Per billing_spec.md v1.1 (Approved 2026-02-10).
"""

import uuid
from dataclasses import dataclass
from django.db import models


# ---------------------------------------------------------------------------
# Enums (Django TextChoices for model field integration)
# ---------------------------------------------------------------------------


class PlanType(models.TextChoices):
    FREE = "free", "Free"
    PRO = "pro", "Pro"
    TEAM = "team", "Team"
    ENTERPRISE = "enterprise", "Enterprise"


class SubscriptionStatus(models.TextChoices):
    FREE = "free", "Free Tier"
    ACTIVE = "active", "Active"
    PAST_DUE = "past_due", "Past Due"
    SUSPENDED = "suspended", "Suspended"
    CANCELLED = "cancelled", "Cancelled"


class BillingEventType(models.TextChoices):
    CREATED = "subscription.created", "Subscription Created"
    ACTIVATED = "subscription.activated", "Subscription Activated"
    RENEWED = "subscription.renewed", "Subscription Renewed"
    PAYMENT_FAILED = "payment.failed", "Payment Failed"
    SUSPENDED = "subscription.suspended", "Subscription Suspended"
    CANCELLED = "subscription.cancelled", "Subscription Cancelled"
    UPGRADED = "subscription.upgraded", "Subscription Upgraded"
    DOWNGRADED = "subscription.downgraded", "Subscription Downgraded"
    REFUNDED = "payment.refunded", "Payment Refunded"
    TOKENS_RESET = "tokens.reset", "Tokens Reset"


# ---------------------------------------------------------------------------
# Plan Configuration (frozen dataclass — immutable at runtime)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlanConfig:
    """Immutable plan configuration. Prices in kopecks (1₽ = 100 kopecks)."""

    name: PlanType
    price_kopecks: int
    tokens_monthly: int  # -1 means unlimited
    max_agents: int  # -1 means unlimited
    features: frozenset[str]

    @property
    def price_rub(self) -> float:
        return self.price_kopecks / 100


PLANS: dict[str, PlanConfig] = {
    PlanType.FREE: PlanConfig(
        name=PlanType.FREE,
        price_kopecks=0,
        tokens_monthly=50_000,
        max_agents=1,
        features=frozenset({"shield_basic"}),
    ),
    PlanType.PRO: PlanConfig(
        name=PlanType.PRO,
        price_kopecks=149_000,  # 1490₽
        tokens_monthly=500_000,
        max_agents=5,
        features=frozenset(
            {
                "shield_full",
                "rlm_memory",
                "priority_routing",
            }
        ),
    ),
    PlanType.TEAM: PlanConfig(
        name=PlanType.TEAM,
        price_kopecks=499_000,  # 4990₽ base
        tokens_monthly=2_000_000,
        max_agents=20,
        features=frozenset(
            {
                "shield_full",
                "rlm_memory",
                "priority_routing",
                "workspace",
                "shared_memory",
            }
        ),
    ),
    PlanType.ENTERPRISE: PlanConfig(
        name=PlanType.ENTERPRISE,
        price_kopecks=4_990_000,  # 49900₽ base
        tokens_monthly=-1,  # unlimited
        max_agents=-1,  # unlimited
        features=frozenset(
            {
                "shield_full",
                "rlm_memory",
                "priority_routing",
                "workspace",
                "shared_memory",
                "on_prem",
                "sla",
                "strike_audit",
                "dedicated_support",
            }
        ),
    ),
}


def get_plan(plan_type: str | PlanType) -> PlanConfig:
    """Get plan config by type. Raises KeyError if not found."""
    return PLANS[str(plan_type)]
