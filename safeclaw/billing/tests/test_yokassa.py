"""
SafeClaw Billing — Tests for ЮKassa Integration & Webhooks.

Per billing_spec.md v1.1 §6.1 — ЮKassa (10 tests).
Uses mocks for ЮKassa SDK to avoid real API calls.
"""

import json
import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase

from billing.models import BillingEvent, Subscription
from billing.plans import (
    BillingEventType,
    PlanType,
    SubscriptionStatus,
    PLANS,
)
from billing.tests import (
    BillingEventFactory,
    SubscriptionFactory,
    UserFactory,
)
from billing.webhooks import process_webhook
from billing.yokassa import (
    PaymentResult,
    RefundResult,
    WebhookEvent,
    create_payment,
    create_recurring_payment,
    create_refund,
)


# ===================================================================
# ЮKassa SDK Wrapper Tests
# ===================================================================


class TestCreatePayment(TestCase):
    """Test create_payment wrapper."""

    @patch("billing.yokassa.Payment.create")
    @patch("billing.yokassa._ensure_configured")
    def test_create_payment(self, mock_cfg, mock_create):
        """Payment creation returns confirmation URL."""
        mock_payment = MagicMock()
        mock_payment.id = "pay_123"
        mock_payment.status = "pending"
        mock_payment.confirmation.confirmation_url = (
            "https://yookassa.ru/checkout/pay_123"
        )
        mock_payment.payment_method = None
        mock_create.return_value = mock_payment

        result = create_payment(
            amount_kopecks=149_000,
            description="Pro plan",
        )

        self.assertIsInstance(result, PaymentResult)
        self.assertEqual(result.payment_id, "pay_123")
        self.assertEqual(result.status, "pending")
        self.assertIn("yookassa.ru", result.confirmation_url)
        self.assertIsNotNone(result.idempotency_key)

    @patch("billing.yokassa.Payment.create")
    @patch("billing.yokassa._ensure_configured")
    def test_create_payment_idempotency(
        self,
        mock_cfg,
        mock_create,
    ):
        """Custom idempotency key is passed to SDK."""
        mock_payment = MagicMock()
        mock_payment.id = "pay_456"
        mock_payment.status = "pending"
        mock_payment.confirmation.confirmation_url = "url"
        mock_payment.payment_method = None
        mock_create.return_value = mock_payment

        idem_key = "my-unique-key"
        result = create_payment(
            amount_kopecks=149_000,
            description="Pro plan",
            idempotency_key=idem_key,
        )

        self.assertEqual(result.idempotency_key, idem_key)
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args
        self.assertEqual(
            call_kwargs.kwargs["idempotency_key"],
            idem_key,
        )

    @patch("billing.yokassa.Payment.create")
    @patch("billing.yokassa._ensure_configured")
    def test_create_payment_saves_method(
        self,
        mock_cfg,
        mock_create,
    ):
        """Payment method ID is extracted when present."""
        mock_pm = MagicMock()
        mock_pm.id = "pm_saved_123"
        mock_payment = MagicMock()
        mock_payment.id = "pay_789"
        mock_payment.status = "succeeded"
        mock_payment.confirmation.confirmation_url = "url"
        mock_payment.payment_method = mock_pm
        mock_create.return_value = mock_payment

        result = create_payment(
            amount_kopecks=149_000,
            description="Pro plan",
        )

        self.assertEqual(
            result.payment_method_id,
            "pm_saved_123",
        )


class TestCreateRecurringPayment(TestCase):
    """Test recurring payment creation."""

    @patch("billing.yokassa.Payment.create")
    @patch("billing.yokassa._ensure_configured")
    def test_recurring_payment_no_redirect(
        self,
        mock_cfg,
        mock_create,
    ):
        """Recurring payment has no confirmation URL."""
        mock_payment = MagicMock()
        mock_payment.id = "pay_recurring_1"
        mock_payment.status = "succeeded"
        mock_create.return_value = mock_payment

        result = create_recurring_payment(
            amount_kopecks=149_000,
            payment_method_id="pm_123",
            description="Auto-renewal",
        )

        self.assertEqual(result.payment_id, "pay_recurring_1")
        self.assertIsNone(result.confirmation_url)
        self.assertEqual(
            result.payment_method_id,
            "pm_123",
        )


class TestCreateRefund(TestCase):
    """Test refund creation."""

    @patch("billing.yokassa.Refund.create")
    @patch("billing.yokassa._ensure_configured")
    def test_refund_creation(self, mock_cfg, mock_create):
        """Refund returns correct amount."""
        mock_refund = MagicMock()
        mock_refund.id = "ref_001"
        mock_refund.status = "succeeded"
        mock_create.return_value = mock_refund

        result = create_refund(
            payment_id="pay_123",
            amount_kopecks=149_000,
        )

        self.assertIsInstance(result, RefundResult)
        self.assertEqual(result.refund_id, "ref_001")
        self.assertEqual(result.amount_kopecks, 149_000)

    @patch("billing.yokassa.Refund.create")
    @patch("billing.yokassa._ensure_configured")
    def test_refund_partial(self, mock_cfg, mock_create):
        """Partial refund uses specified amount."""
        mock_refund = MagicMock()
        mock_refund.id = "ref_002"
        mock_refund.status = "succeeded"
        mock_create.return_value = mock_refund

        result = create_refund(
            payment_id="pay_123",
            amount_kopecks=50_000,  # partial
        )

        self.assertEqual(result.amount_kopecks, 50_000)
        # Verify amount passed to SDK
        call_args = mock_create.call_args[0][0]
        self.assertEqual(
            Decimal(call_args["amount"]["value"]),
            Decimal("500"),
        )


# ===================================================================
# Webhook Processing Tests
# ===================================================================


class TestWebhookIdempotency(TestCase):
    """Test webhook idempotency (NFR-02, AC-06)."""

    def test_webhook_idempotency(self):
        """Duplicate webhook is silently ignored."""
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.FREE,
            tokens_limit=PLANS[PlanType.PRO].tokens_monthly,
        )
        idem_key = f"wh_pay_dup_{uuid.uuid4().hex[:8]}"

        event = WebhookEvent(
            event_type="payment.succeeded",
            payment_id="pay_dup",
            status="succeeded",
            amount_kopecks=149_000,
            currency="RUB",
            payment_method_id="pm_1",
            metadata={"subscription_id": str(sub.pk)},
            idempotency_key=idem_key,
        )

        # First call — processes
        result1 = process_webhook(event)
        self.assertEqual(result1, "processed")

        # Second call — duplicate
        result2 = process_webhook(event)
        self.assertEqual(result2, "duplicate")

        # Only 1 event created
        events = BillingEvent.objects.filter(
            idempotency_key=idem_key,
        )
        self.assertEqual(events.count(), 1)


class TestWebhookPaymentSucceeded(TestCase):
    """Test payment.succeeded webhook handler."""

    def test_activates_subscription(self):
        """Successful payment activates subscription."""
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.FREE,
            tokens_limit=PLANS[PlanType.PRO].tokens_monthly,
        )

        event = WebhookEvent(
            event_type="payment.succeeded",
            payment_id="pay_activate",
            status="succeeded",
            amount_kopecks=149_000,
            currency="RUB",
            payment_method_id="pm_saved",
            metadata={"subscription_id": str(sub.pk)},
            idempotency_key=f"wh_pay_a_{uuid.uuid4().hex[:8]}",
        )

        result = process_webhook(event)
        self.assertEqual(result, "processed")

        sub.refresh_from_db()
        self.assertEqual(
            sub.status,
            SubscriptionStatus.ACTIVE,
        )
        self.assertEqual(
            sub.yokassa_payment_method_id,
            "pm_saved",
        )

    def test_reactivates_past_due(self):
        """Payment reactivates PAST_DUE subscription."""
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.PAST_DUE,
            tokens_limit=PLANS[PlanType.PRO].tokens_monthly,
            tokens_used=400_000,
        )

        event = WebhookEvent(
            event_type="payment.succeeded",
            payment_id="pay_reactivate",
            status="succeeded",
            amount_kopecks=149_000,
            currency="RUB",
            payment_method_id=None,
            metadata={"subscription_id": str(sub.pk)},
            idempotency_key=f"wh_pay_r_{uuid.uuid4().hex[:8]}",
        )

        process_webhook(event)

        sub.refresh_from_db()
        self.assertEqual(
            sub.status,
            SubscriptionStatus.ACTIVE,
        )
        # Tokens reset on renewal
        self.assertEqual(sub.tokens_used, 0)


class TestWebhookPaymentFailed(TestCase):
    """Test payment.canceled webhook handler."""

    def test_payment_failed_past_due(self):
        """Failed payment moves ACTIVE → PAST_DUE."""
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=PLANS[PlanType.PRO].tokens_monthly,
        )

        event = WebhookEvent(
            event_type="payment.canceled",
            payment_id="pay_fail",
            status="canceled",
            amount_kopecks=149_000,
            currency="RUB",
            payment_method_id=None,
            metadata={"subscription_id": str(sub.pk)},
            idempotency_key=f"wh_pay_f_{uuid.uuid4().hex[:8]}",
        )

        result = process_webhook(event)
        self.assertEqual(result, "processed")

        sub.refresh_from_db()
        self.assertEqual(
            sub.status,
            SubscriptionStatus.PAST_DUE,
        )

        # BillingEvent created
        event_record = BillingEvent.objects.filter(
            subscription=sub,
            event_type=BillingEventType.PAYMENT_FAILED,
        ).first()
        self.assertIsNotNone(event_record)


class TestWebhookUnknownEvent(TestCase):
    """Test handling of unknown webhook events."""

    def test_unknown_event_returns_error(self):
        """Unknown event type returns 'error'."""
        event = WebhookEvent(
            event_type="unknown.event.type",
            payment_id="pay_unknown",
            status="unknown",
            amount_kopecks=0,
            currency="RUB",
            payment_method_id=None,
            metadata=None,
            idempotency_key="wh_unknown",
        )

        result = process_webhook(event)
        self.assertEqual(result, "error")
