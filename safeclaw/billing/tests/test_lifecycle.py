"""
SafeClaw Billing — Tests for Subscription Lifecycle.

Per billing_spec.md v1.1 §6.1 — Lifecycle (12 tests).
Tests all state transitions including invalid ones.
"""

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from billing.lifecycle import (
    InvalidTransitionError,
    activate,
    cancel,
    mark_past_due,
    process_auto_cancellations,
    process_grace_periods,
    suspend,
    upgrade,
    validate_transition,
)
from billing.models import BillingEvent, Subscription
from billing.plans import (
    BillingEventType,
    PlanType,
    SubscriptionStatus,
    PLANS,
)
from billing.tests import SubscriptionFactory


# ===================================================================
# Transition Validation
# ===================================================================


class TestTransitionValidation(TestCase):
    """Test state machine transition table."""

    def test_free_to_active(self):
        self.assertTrue(
            validate_transition(
                SubscriptionStatus.FREE,
                SubscriptionStatus.ACTIVE,
            )
        )

    def test_active_to_past_due(self):
        self.assertTrue(
            validate_transition(
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.PAST_DUE,
            )
        )

    def test_active_to_cancelled(self):
        self.assertTrue(
            validate_transition(
                SubscriptionStatus.ACTIVE,
                SubscriptionStatus.CANCELLED,
            )
        )

    def test_past_due_to_active(self):
        self.assertTrue(
            validate_transition(
                SubscriptionStatus.PAST_DUE,
                SubscriptionStatus.ACTIVE,
            )
        )

    def test_past_due_to_suspended(self):
        self.assertTrue(
            validate_transition(
                SubscriptionStatus.PAST_DUE,
                SubscriptionStatus.SUSPENDED,
            )
        )

    def test_suspended_to_active(self):
        self.assertTrue(
            validate_transition(
                SubscriptionStatus.SUSPENDED,
                SubscriptionStatus.ACTIVE,
            )
        )

    def test_suspended_to_cancelled(self):
        self.assertTrue(
            validate_transition(
                SubscriptionStatus.SUSPENDED,
                SubscriptionStatus.CANCELLED,
            )
        )

    def test_invalid_free_to_suspended(self):
        self.assertFalse(
            validate_transition(
                SubscriptionStatus.FREE,
                SubscriptionStatus.SUSPENDED,
            )
        )

    def test_invalid_cancelled_to_active(self):
        """CANCELLED is terminal — no transitions out."""
        self.assertFalse(
            validate_transition(
                SubscriptionStatus.CANCELLED,
                SubscriptionStatus.ACTIVE,
            )
        )


# ===================================================================
# Lifecycle Operations
# ===================================================================


class TestActivate(TestCase):
    """Test activate() operation."""

    def test_free_to_active(self):
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.FREE,
            tokens_limit=PLANS[PlanType.PRO].tokens_monthly,
        )
        result = activate(sub, payment_method_id="pm_1")

        result.refresh_from_db()
        self.assertEqual(
            result.status,
            SubscriptionStatus.ACTIVE,
        )
        self.assertEqual(result.tokens_used, 0)
        self.assertIsNotNone(result.expires_at)
        self.assertEqual(
            result.yokassa_payment_method_id,
            "pm_1",
        )

    def test_creates_billing_event(self):
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.FREE,
            tokens_limit=PLANS[PlanType.PRO].tokens_monthly,
        )
        activate(sub)

        events = BillingEvent.objects.filter(
            subscription=sub,
            event_type=BillingEventType.ACTIVATED,
        )
        self.assertEqual(events.count(), 1)

    def test_reactivate_suspended(self):
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.SUSPENDED,
            tokens_limit=PLANS[PlanType.PRO].tokens_monthly,
            tokens_used=300_000,
        )
        result = activate(sub)

        result.refresh_from_db()
        self.assertEqual(
            result.status,
            SubscriptionStatus.ACTIVE,
        )
        self.assertEqual(result.tokens_used, 0)


class TestMarkPastDue(TestCase):
    """Test mark_past_due() operation."""

    def test_active_to_past_due(self):
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=PLANS[PlanType.PRO].tokens_monthly,
        )
        result = mark_past_due(sub)

        result.refresh_from_db()
        self.assertEqual(
            result.status,
            SubscriptionStatus.PAST_DUE,
        )


class TestSuspend(TestCase):
    """Test suspend() operation."""

    def test_past_due_to_suspended(self):
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.PAST_DUE,
            tokens_limit=PLANS[PlanType.PRO].tokens_monthly,
        )
        result = suspend(sub)

        result.refresh_from_db()
        self.assertEqual(
            result.status,
            SubscriptionStatus.SUSPENDED,
        )


class TestCancel(TestCase):
    """Test cancel() operation."""

    def test_active_to_cancelled(self):
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=PLANS[PlanType.PRO].tokens_monthly,
        )
        result = cancel(sub)

        result.refresh_from_db()
        self.assertEqual(
            result.status,
            SubscriptionStatus.CANCELLED,
        )
        self.assertEqual(result.plan, PlanType.FREE)
        self.assertIsNone(
            result.yokassa_payment_method_id,
        )

    def test_cancel_from_suspended(self):
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.SUSPENDED,
            tokens_limit=PLANS[PlanType.PRO].tokens_monthly,
        )
        result = cancel(sub)

        result.refresh_from_db()
        self.assertEqual(
            result.status,
            SubscriptionStatus.CANCELLED,
        )


class TestInvalidTransitions(TestCase):
    """Test that invalid transitions raise errors."""

    def test_free_to_suspended_raises(self):
        sub = SubscriptionFactory(
            status=SubscriptionStatus.FREE,
            tokens_limit=50_000,
        )
        with self.assertRaises(InvalidTransitionError):
            suspend(sub)

    def test_cancelled_to_active_raises(self):
        sub = SubscriptionFactory(
            status=SubscriptionStatus.CANCELLED,
            tokens_limit=50_000,
        )
        with self.assertRaises(InvalidTransitionError):
            activate(sub)


class TestUpgrade(TestCase):
    """Test upgrade/downgrade operation."""

    def test_upgrade_pro_to_team(self):
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=PLANS[PlanType.PRO].tokens_monthly,
        )
        result = upgrade(sub, PlanType.TEAM)

        result.refresh_from_db()
        self.assertEqual(result.plan, PlanType.TEAM)
        self.assertEqual(
            result.tokens_limit,
            PLANS[PlanType.TEAM].tokens_monthly,
        )

        events = BillingEvent.objects.filter(
            subscription=sub,
            event_type=BillingEventType.UPGRADED,
        )
        self.assertEqual(events.count(), 1)

    def test_downgrade_team_to_pro(self):
        sub = SubscriptionFactory(
            plan=PlanType.TEAM,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=PLANS[PlanType.TEAM].tokens_monthly,
        )
        result = upgrade(sub, PlanType.PRO)

        result.refresh_from_db()
        self.assertEqual(result.plan, PlanType.PRO)

        events = BillingEvent.objects.filter(
            subscription=sub,
            event_type=BillingEventType.DOWNGRADED,
        )
        self.assertEqual(events.count(), 1)

    def test_upgrade_same_plan_raises(self):
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=PLANS[PlanType.PRO].tokens_monthly,
        )
        with self.assertRaises(ValueError):
            upgrade(sub, PlanType.PRO)


# ===================================================================
# Scheduled Tasks
# ===================================================================


class TestGracePeriod(TestCase):
    """Test grace period processing (3 days)."""

    def test_grace_period_3_days(self):
        """PAST_DUE > 3 days → SUSPENDED."""
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.PAST_DUE,
            tokens_limit=PLANS[PlanType.PRO].tokens_monthly,
        )
        # Create a PAYMENT_FAILED event 4 days ago
        event = BillingEvent.objects.create(
            subscription=sub,
            event_type=BillingEventType.PAYMENT_FAILED,
            idempotency_key="grace_test_1",
        )
        # Manually backdate
        BillingEvent.objects.filter(pk=event.pk).update(
            created_at=timezone.now() - timedelta(days=4),
        )

        count = process_grace_periods()
        self.assertEqual(count, 1)

        sub.refresh_from_db()
        self.assertEqual(
            sub.status,
            SubscriptionStatus.SUSPENDED,
        )


class TestAutoCancel(TestCase):
    """Test auto-cancellation (30 days)."""

    def test_auto_cancel_30_days(self):
        """SUSPENDED > 30 days → CANCELLED."""
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.SUSPENDED,
            tokens_limit=PLANS[PlanType.PRO].tokens_monthly,
        )
        event = BillingEvent.objects.create(
            subscription=sub,
            event_type=BillingEventType.SUSPENDED,
            idempotency_key="autocancel_test_1",
        )
        BillingEvent.objects.filter(pk=event.pk).update(
            created_at=timezone.now() - timedelta(days=31),
        )

        count = process_auto_cancellations()
        self.assertEqual(count, 1)

        sub.refresh_from_db()
        self.assertEqual(
            sub.status,
            SubscriptionStatus.CANCELLED,
        )
