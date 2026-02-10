"""
SafeClaw Billing — Phase 6 Tests.

Tests for:
- Token metering middleware
- Celery tasks (grace, auto-cancel, monthly reset)
- Notifications (email, telegram)
- Refund API endpoint
"""

import hashlib
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.test import (
    RequestFactory,
    TestCase,
    override_settings,
)
from django.utils import timezone
from rest_framework.test import APIClient

from billing.metering import consume_tokens
from billing.middleware import TokenMeteringMiddleware
from billing.models import (
    BillingEvent,
    Subscription,
    User,
)
from billing.notifications import (
    notify_approaching_limit,
    notify_over_limit,
    notify_payment_success,
    notify_subscription_cancelled,
    notify_subscription_suspended,
)
from billing.plans import (
    PlanType,
    SubscriptionStatus,
)
from billing.tasks import (
    task_check_usage_alerts,
    task_monthly_token_reset,
    task_process_auto_cancellations,
    task_process_grace_periods,
)


class RefundAPITest(TestCase):
    """Test POST /api/billing/refund/."""

    def setUp(self):
        self.raw_key = "test-refund-key-12345"
        self.user = User.objects.create(
            email="refund@test.com",
            api_key_hash=hashlib.sha256(self.raw_key.encode()).hexdigest(),
        )
        self.sub = Subscription.objects.create(
            user=self.user,
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=500_000,
        )
        # SEC-05: Create BillingEvents so IDOR check passes
        for pid in ("pay_123", "pay_456", "pay_fail"):
            BillingEvent.objects.create(
                subscription=self.sub,
                event_type="activated",
                amount_kopecks=99900,
                yokassa_payment_id=pid,
                idempotency_key=f"wh_{pid}",
            )
        self.client = APIClient()
        self.client.credentials(
            HTTP_X_API_KEY=self.raw_key,
        )

    def test_refund_requires_payment_id(self):
        """POST without payment_id returns 400."""
        resp = self.client.post(
            "/api/billing/refund/",
            {},
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("payment_id", resp.data["detail"])

    def test_refund_no_auth_returns_401(self):
        """POST without API key returns 401."""
        client = APIClient()
        resp = client.post(
            "/api/billing/refund/",
            {"payment_id": "pay_123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 401)

    @patch("billing.views.create_refund")
    def test_refund_success(self, mock_refund):
        """POST with valid data creates a refund."""
        mock_refund.return_value = MagicMock(
            refund_id="ref_abc",
            status="succeeded",
            amount_kopecks=99900,
        )
        resp = self.client.post(
            "/api/billing/refund/",
            {"payment_id": "pay_123"},
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(
            resp.data["refund_id"],
            "ref_abc",
        )
        mock_refund.assert_called_once_with(
            payment_id="pay_123",
            amount_kopecks=None,
        )

    @patch("billing.views.create_refund")
    def test_refund_partial(self, mock_refund):
        """POST with amount_kopecks creates partial."""
        mock_refund.return_value = MagicMock(
            refund_id="ref_partial",
            status="succeeded",
            amount_kopecks=50000,
        )
        resp = self.client.post(
            "/api/billing/refund/",
            {
                "payment_id": "pay_456",
                "amount_kopecks": 50000,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(
            resp.data["amount_kopecks"],
            50000,
        )
        mock_refund.assert_called_once_with(
            payment_id="pay_456",
            amount_kopecks=50000,
        )

    @patch("billing.views.create_refund")
    def test_refund_yokassa_error(self, mock_refund):
        """POST when ЮKassa fails returns 502."""
        mock_refund.side_effect = Exception("Gateway error")
        resp = self.client.post(
            "/api/billing/refund/",
            {"payment_id": "pay_fail"},
            format="json",
        )
        self.assertEqual(resp.status_code, 502)


class MiddlewareTest(TestCase):
    """Test TokenMeteringMiddleware."""

    def setUp(self):
        self.raw_key = "test-mw-key-12345"
        self.user = User.objects.create(
            email="mw@test.com",
            api_key_hash=hashlib.sha256(self.raw_key.encode()).hexdigest(),
        )
        self.sub = Subscription.objects.create(
            user=self.user,
            plan=PlanType.FREE,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=100,
            tokens_used=0,
        )
        self.factory = RequestFactory()

    def _get_response_200(self, request):
        from django.http import HttpResponse

        return HttpResponse("OK")

    def test_exempt_path_skipped(self):
        """Billing paths are not metered."""
        mw = TokenMeteringMiddleware(
            self._get_response_200,
        )
        request = self.factory.get(
            "/api/billing/plans/",
        )
        resp = mw(request)
        self.assertEqual(resp.status_code, 200)

    def test_no_api_key_passes_through(self):
        """Requests without API key pass through."""
        mw = TokenMeteringMiddleware(
            self._get_response_200,
        )
        request = self.factory.get("/api/scan/")
        resp = mw(request)
        self.assertEqual(resp.status_code, 200)

    def test_over_limit_returns_429(self):
        """Requests over token limit return 429."""
        self.sub.tokens_used = 100
        self.sub.save()

        mw = TokenMeteringMiddleware(
            self._get_response_200,
        )
        request = self.factory.get("/api/scan/")
        request.META["HTTP_X_API_KEY"] = self.raw_key
        resp = mw(request)
        self.assertEqual(resp.status_code, 429)


class CeleryTaskTest(TestCase):
    """Test Celery task functions."""

    def setUp(self):
        self.user = User.objects.create(
            email="tasks@test.com",
            api_key_hash="abc123hash",
        )

    @patch("billing.tasks.process_grace_periods")
    def test_grace_period_task(self, mock_fn):
        """Grace period task calls lifecycle fn."""
        mock_fn.return_value = 3
        result = task_process_grace_periods()
        self.assertEqual(result, 3)
        mock_fn.assert_called_once()

    @patch(
        "billing.tasks.process_auto_cancellations",
    )
    def test_auto_cancel_task(self, mock_fn):
        """Auto-cancel task calls lifecycle fn."""
        mock_fn.return_value = 1
        result = task_process_auto_cancellations()
        self.assertEqual(result, 1)
        mock_fn.assert_called_once()

    def test_monthly_reset_task(self):
        """Monthly reset resets active subscriptions."""
        sub = Subscription.objects.create(
            user=self.user,
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=500_000,
            tokens_used=250_000,
        )
        count = task_monthly_token_reset()
        self.assertEqual(count, 1)
        sub.refresh_from_db()
        self.assertEqual(sub.tokens_used, 0)

    @patch("billing.tasks.notify_over_limit")
    @patch("billing.tasks.notify_approaching_limit")
    def test_usage_alerts_task(
        self,
        mock_approach,
        mock_over,
    ):
        """Usage alerts fires for 80%+ usage."""
        Subscription.objects.create(
            user=self.user,
            plan=PlanType.FREE,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=100,
            tokens_used=85,
        )
        count = task_check_usage_alerts()
        self.assertEqual(count, 1)
        mock_approach.assert_called_once()
        mock_over.assert_not_called()


class NotificationTest(TestCase):
    """Test notification functions."""

    def setUp(self):
        self.user = User.objects.create(
            email="notify@test.com",
            telegram_id="123456",
            api_key_hash="notifyhash",
        )
        self.sub = Subscription.objects.create(
            user=self.user,
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=500_000,
            tokens_used=400_000,
        )

    @patch("billing.notifications.send_mail")
    def test_email_sent_for_approaching_limit(
        self,
        mock_mail,
    ):
        """Email sent when approaching token limit."""
        notify_approaching_limit(self.sub)
        mock_mail.assert_called_once()
        call_args = mock_mail.call_args
        self.assertIn(
            "80%",
            call_args[1]["subject"],
        )

    @patch("billing.notifications.send_mail")
    def test_email_not_sent_without_email(
        self,
        mock_mail,
    ):
        """No email if user has no email address."""
        self.user.email = ""
        self.user.save()
        notify_approaching_limit(self.sub)
        mock_mail.assert_not_called()

    @patch("billing.notifications.send_mail")
    def test_over_limit_notification(
        self,
        mock_mail,
    ):
        """Over limit sends notification."""
        notify_over_limit(self.sub)
        mock_mail.assert_called_once()

    @patch("billing.notifications.send_mail")
    def test_payment_success_notification(
        self,
        mock_mail,
    ):
        """Payment success sends notification."""
        notify_payment_success(self.sub, 999.0)
        mock_mail.assert_called_once()
        call_args = mock_mail.call_args
        self.assertIn(
            "999",
            call_args[1]["subject"],
        )

    @patch("billing.notifications.send_mail")
    def test_subscription_suspended(
        self,
        mock_mail,
    ):
        """Suspended notification sent."""
        notify_subscription_suspended(self.sub)
        mock_mail.assert_called_once()

    @patch("billing.notifications.send_mail")
    def test_subscription_cancelled(
        self,
        mock_mail,
    ):
        """Cancelled notification sent."""
        notify_subscription_cancelled(self.sub)
        mock_mail.assert_called_once()
