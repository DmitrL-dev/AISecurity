"""
SafeClaw Billing — Subscription Lifecycle State Machine.

Per billing_spec.md v1.1 §3.2.
Manages subscription state transitions with validation.

Valid transitions:
  FREE      → ACTIVE     (payment.succeeded)
  ACTIVE    → PAST_DUE   (payment.failed)
  ACTIVE    → CANCELLED  (user.cancel)
  ACTIVE    → ACTIVE     (auto-renew, upgrade/downgrade)
  PAST_DUE  → ACTIVE     (payment.succeeded)
  PAST_DUE  → SUSPENDED  (grace_period_expired)
  SUSPENDED → ACTIVE     (payment.succeeded)
  SUSPENDED → CANCELLED  (30_days_expired)
"""

import logging
import uuid
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from .models import BillingEvent, Subscription
from .plans import (
    BillingEventType,
    PlanType,
    SubscriptionStatus,
    PLANS,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Transition table
# ---------------------------------------------------------------------------

# Maps: (current_status) → set of allowed target statuses
VALID_TRANSITIONS: dict[str, set[str]] = {
    SubscriptionStatus.FREE: {
        SubscriptionStatus.ACTIVE,
    },
    SubscriptionStatus.ACTIVE: {
        SubscriptionStatus.ACTIVE,  # renew / upgrade
        SubscriptionStatus.PAST_DUE,
        SubscriptionStatus.CANCELLED,
    },
    SubscriptionStatus.PAST_DUE: {
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.SUSPENDED,
    },
    SubscriptionStatus.SUSPENDED: {
        SubscriptionStatus.ACTIVE,
        SubscriptionStatus.CANCELLED,
    },
    SubscriptionStatus.CANCELLED: set(),  # terminal
}


class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""

    def __init__(self, current: str, target: str):
        self.current = current
        self.target = target
        super().__init__(f"Invalid transition: {current} → {target}")


def validate_transition(current: str, target: str) -> bool:
    """Check if a state transition is valid."""
    allowed = VALID_TRANSITIONS.get(current, set())
    return target in allowed


# ---------------------------------------------------------------------------
# Lifecycle operations
# ---------------------------------------------------------------------------


def activate(
    subscription: Subscription,
    payment_method_id: str | None = None,
) -> Subscription:
    """
    Activate subscription after successful payment.

    FREE/PAST_DUE/SUSPENDED → ACTIVE
    Resets token counter and sets 30-day expiry.
    """
    _assert_transition(
        subscription,
        SubscriptionStatus.ACTIVE,
    )

    with transaction.atomic():
        sub = Subscription.objects.select_for_update().get(
            pk=subscription.pk,
        )
        old_status = sub.status
        sub.status = SubscriptionStatus.ACTIVE
        sub.tokens_used = 0
        sub.expires_at = timezone.now() + timedelta(days=30)

        plan_config = PLANS.get(sub.plan)
        if plan_config:
            sub.tokens_limit = plan_config.tokens_monthly

        if payment_method_id:
            sub.yokassa_payment_method_id = payment_method_id

        sub.save()

        evt_type = (
            BillingEventType.ACTIVATED
            if old_status == SubscriptionStatus.FREE
            else BillingEventType.RENEWED
        )

        BillingEvent.objects.create(
            subscription=sub,
            event_type=evt_type,
            idempotency_key=f"lifecycle_act_{uuid.uuid4().hex[:12]}",
            metadata_json={
                "from_status": old_status,
                "to_status": SubscriptionStatus.ACTIVE,
            },
        )

    logger.info("Activated: %s (%s → ACTIVE)", sub.pk, old_status)
    return sub


def mark_past_due(subscription: Subscription) -> Subscription:
    """
    Mark subscription as past due after payment failure.

    ACTIVE → PAST_DUE (grace period 3 days starts).
    """
    _assert_transition(
        subscription,
        SubscriptionStatus.PAST_DUE,
    )

    with transaction.atomic():
        sub = Subscription.objects.select_for_update().get(
            pk=subscription.pk,
        )
        sub.status = SubscriptionStatus.PAST_DUE
        sub.save()

        BillingEvent.objects.create(
            subscription=sub,
            event_type=BillingEventType.PAYMENT_FAILED,
            idempotency_key=f"lifecycle_pd_{uuid.uuid4().hex[:12]}",
            metadata_json={
                "from_status": SubscriptionStatus.ACTIVE,
                "grace_period_days": 3,
            },
        )

    logger.info("Past due: %s", sub.pk)
    return sub


def suspend(subscription: Subscription) -> Subscription:
    """
    Suspend subscription after grace period expires.

    PAST_DUE → SUSPENDED (30-day countdown to cancel).
    """
    _assert_transition(
        subscription,
        SubscriptionStatus.SUSPENDED,
    )

    with transaction.atomic():
        sub = Subscription.objects.select_for_update().get(
            pk=subscription.pk,
        )
        sub.status = SubscriptionStatus.SUSPENDED
        sub.save()

        BillingEvent.objects.create(
            subscription=sub,
            event_type=BillingEventType.SUSPENDED,
            idempotency_key=f"lifecycle_sus_{uuid.uuid4().hex[:12]}",
            metadata_json={
                "reason": "grace_period_expired",
                "auto_cancel_days": 30,
            },
        )

    logger.info("Suspended: %s", sub.pk)
    return sub


def cancel(subscription: Subscription) -> Subscription:
    """
    Cancel subscription.

    ACTIVE → CANCELLED (user request)
    SUSPENDED → CANCELLED (30-day expiry)
    """
    _assert_transition(
        subscription,
        SubscriptionStatus.CANCELLED,
    )

    with transaction.atomic():
        sub = Subscription.objects.select_for_update().get(
            pk=subscription.pk,
        )
        old_status = sub.status
        sub.status = SubscriptionStatus.CANCELLED
        sub.plan = PlanType.FREE
        sub.tokens_limit = PLANS[PlanType.FREE].tokens_monthly
        sub.tokens_used = 0
        sub.yokassa_payment_method_id = None
        sub.save()

        BillingEvent.objects.create(
            subscription=sub,
            event_type=BillingEventType.CANCELLED,
            idempotency_key=f"lifecycle_can_{uuid.uuid4().hex[:12]}",
            metadata_json={
                "from_status": old_status,
                "reason": (
                    "user_request"
                    if old_status == SubscriptionStatus.ACTIVE
                    else "30_days_expired"
                ),
            },
        )

    logger.info("Cancelled: %s (%s)", sub.pk, old_status)
    return sub


def upgrade(
    subscription: Subscription,
    new_plan: str,
) -> Subscription:
    """
    Upgrade/downgrade plan.

    ACTIVE → ACTIVE (with new plan limits).
    """
    if subscription.status != SubscriptionStatus.ACTIVE:
        raise InvalidTransitionError(
            subscription.status,
            "upgrade",
        )

    if new_plan == subscription.plan:
        raise ValueError("Already on this plan")

    with transaction.atomic():
        sub = Subscription.objects.select_for_update().get(
            pk=subscription.pk,
        )
        old_plan = sub.plan
        new_config = PLANS[new_plan]

        is_upgrade = new_config.price_kopecks > PLANS[old_plan].price_kopecks

        sub.plan = new_plan
        sub.tokens_limit = new_config.tokens_monthly
        # Keep tokens_used (prorated in billing)
        sub.save()

        evt_type = (
            BillingEventType.UPGRADED if is_upgrade else BillingEventType.DOWNGRADED
        )

        BillingEvent.objects.create(
            subscription=sub,
            event_type=evt_type,
            idempotency_key=f"lifecycle_upg_{uuid.uuid4().hex[:12]}",
            metadata_json={
                "from_plan": old_plan,
                "to_plan": new_plan,
                "is_upgrade": is_upgrade,
            },
        )

    logger.info(
        "Plan changed: %s %s → %s",
        sub.pk,
        old_plan,
        new_plan,
    )
    return sub


# ---------------------------------------------------------------------------
# Scheduled tasks (called by Celery Beat or management command)
# ---------------------------------------------------------------------------


def process_grace_periods():
    """
    Process expired grace periods.

    Finds PAST_DUE subscriptions older than 3 days
    and moves them to SUSPENDED.
    """
    cutoff = timezone.now() - timedelta(days=3)
    past_due = Subscription.objects.filter(
        status=SubscriptionStatus.PAST_DUE,
    )

    count = 0
    for sub in past_due:
        # Check last PAYMENT_FAILED event timestamp
        last_fail = (
            BillingEvent.objects.filter(
                subscription=sub,
                event_type=BillingEventType.PAYMENT_FAILED,
            )
            .order_by("-created_at")
            .first()
        )
        if last_fail and last_fail.created_at <= cutoff:
            suspend(sub)
            count += 1

    logger.info(
        "Grace period check: %d subscriptions suspended",
        count,
    )
    return count


def process_auto_cancellations():
    """
    Process expired suspensions.

    Finds SUSPENDED subscriptions older than 30 days
    and moves them to CANCELLED.
    """
    cutoff = timezone.now() - timedelta(days=30)
    suspended = Subscription.objects.filter(
        status=SubscriptionStatus.SUSPENDED,
    )

    count = 0
    for sub in suspended:
        last_suspend = (
            BillingEvent.objects.filter(
                subscription=sub,
                event_type=BillingEventType.SUSPENDED,
            )
            .order_by("-created_at")
            .first()
        )
        if last_suspend and last_suspend.created_at <= cutoff:
            cancel(sub)
            count += 1

    logger.info(
        "Auto-cancel check: %d subscriptions cancelled",
        count,
    )
    return count


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------


def _assert_transition(
    subscription: Subscription,
    target: str,
):
    """Validate and raise on invalid transition."""
    if not validate_transition(
        subscription.status,
        target,
    ):
        raise InvalidTransitionError(
            subscription.status,
            target,
        )
