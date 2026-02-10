"""
SafeClaw Billing — API Integration Tests.

Per billing_spec.md v1.1 §6.1 — REST API (15 tests).
Tests endpoints with DRF test client and API key auth.
"""

from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from billing.models import Subscription, User
from billing.plans import (
    PlanType,
    SubscriptionStatus,
)


class APITestBase(TestCase):
    """Base class with authenticated API client."""

    def setUp(self):
        self.client = APIClient()
        self.raw_key, key_hash = User.generate_api_key()
        self.user = User.objects.create(
            email="api@safeclaw.ru",
            api_key_hash=key_hash,
        )

    def auth_client(self):
        """Return client with API key header set."""
        self.client.credentials(
            HTTP_X_API_KEY=self.raw_key,
        )
        return self.client


# ===================================================================
# Public Endpoints
# ===================================================================


class TestPlanListAPI(TestCase):
    """GET /api/billing/plans/"""

    def test_list_plans(self):
        client = APIClient()
        resp = client.get("/api/billing/plans/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 4)

    def test_plans_contain_prices(self):
        client = APIClient()
        resp = client.get("/api/billing/plans/")

        names = [p["name"] for p in resp.data]
        self.assertIn("free", names)
        self.assertIn("pro", names)
        self.assertIn("team", names)
        self.assertIn("enterprise", names)


# ===================================================================
# Auth Tests
# ===================================================================


class TestAPIKeyAuth(APITestBase):
    """Test X-API-Key authentication."""

    def test_auth_valid_key(self):
        sub = Subscription.objects.create(
            user=self.user,
            plan=PlanType.FREE,
            tokens_limit=50_000,
        )
        client = self.auth_client()
        resp = client.get("/api/billing/subscription/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_auth_invalid_key(self):
        self.client.credentials(
            HTTP_X_API_KEY="invalid_key_123",
        )
        resp = self.client.get("/api/billing/subscription/")

        self.assertEqual(
            resp.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_auth_missing_key(self):
        resp = self.client.get("/api/billing/subscription/")

        self.assertEqual(
            resp.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )


# ===================================================================
# Subscription Endpoint
# ===================================================================


class TestSubscriptionAPI(APITestBase):
    """GET /api/billing/subscription/"""

    def test_get_subscription(self):
        sub = Subscription.objects.create(
            user=self.user,
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=500_000,
            tokens_used=100_000,
        )
        client = self.auth_client()
        resp = client.get("/api/billing/subscription/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["plan"], "pro")
        self.assertEqual(resp.data["tokens_used"], 100_000)
        self.assertEqual(
            resp.data["tokens_remaining"],
            400_000,
        )
        self.assertEqual(resp.data["usage_percent"], 20.0)

    def test_no_subscription_404(self):
        client = self.auth_client()
        resp = client.get("/api/billing/subscription/")

        self.assertEqual(
            resp.status_code,
            status.HTTP_404_NOT_FOUND,
        )


# ===================================================================
# Usage Endpoint
# ===================================================================


class TestUsageAPI(APITestBase):
    """GET /api/billing/usage/"""

    def test_get_usage(self):
        Subscription.objects.create(
            user=self.user,
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=500_000,
            tokens_used=250_000,
        )
        client = self.auth_client()
        resp = client.get("/api/billing/usage/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["tokens_used"], 250_000)
        self.assertEqual(resp.data["usage_percent"], 50.0)
        self.assertFalse(resp.data["is_over_limit"])


# ===================================================================
# Cancel Endpoint
# ===================================================================


class TestCancelAPI(APITestBase):
    """POST /api/billing/cancel/"""

    def test_cancel_active(self):
        Subscription.objects.create(
            user=self.user,
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=500_000,
        )
        client = self.auth_client()
        resp = client.post("/api/billing/cancel/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], "cancelled")
        self.assertEqual(resp.data["plan"], "free")

    def test_cancel_free_409(self):
        Subscription.objects.create(
            user=self.user,
            plan=PlanType.FREE,
            status=SubscriptionStatus.FREE,
            tokens_limit=50_000,
        )
        client = self.auth_client()
        resp = client.post("/api/billing/cancel/")

        self.assertEqual(
            resp.status_code,
            status.HTTP_409_CONFLICT,
        )


# ===================================================================
# Upgrade Endpoint
# ===================================================================


class TestUpgradeAPI(APITestBase):
    """POST /api/billing/upgrade/"""

    def test_upgrade_pro_to_team(self):
        Subscription.objects.create(
            user=self.user,
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=500_000,
        )
        client = self.auth_client()
        resp = client.post(
            "/api/billing/upgrade/",
            {"new_plan": "team"},
        )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["plan"], "team")

    def test_upgrade_same_plan_400(self):
        Subscription.objects.create(
            user=self.user,
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=500_000,
        )
        client = self.auth_client()
        resp = client.post(
            "/api/billing/upgrade/",
            {"new_plan": "pro"},
        )

        self.assertEqual(
            resp.status_code,
            status.HTTP_400_BAD_REQUEST,
        )


# ===================================================================
# Billing History
# ===================================================================


class TestBillingHistoryAPI(APITestBase):
    """GET /api/billing/history/"""

    def test_history_empty(self):
        Subscription.objects.create(
            user=self.user,
            plan=PlanType.FREE,
            tokens_limit=50_000,
        )
        client = self.auth_client()
        resp = client.get("/api/billing/history/")

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 0)
