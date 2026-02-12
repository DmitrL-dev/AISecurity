"""
SafeClaw Billing — Unit Tests for Models and Plans.

Per billing_spec.md v1.1 — Test Plan §6.1.
Tests: Models (8), Lifecycle basics (6), Metering basics (4) = 18 tests.
"""

import pytest
from django.db import IntegrityError
from django.test import TestCase

from billing.models import (
    BillingEvent,
    Subscription,
    UsageLog,
    User,
)
from billing.plans import (
    BillingEventType,
    PlanConfig,
    PlanType,
    SubscriptionStatus,
    PLANS,
    get_plan,
)
from billing.tests import (
    BillingEventFactory,
    ProSubscriptionFactory,
    SubscriptionFactory,
    TelegramUserFactory,
    UsageLogFactory,
    UserFactory,
)


# ===================================================================
# Plan Configuration Tests
# ===================================================================


class TestPlanConfig(TestCase):
    """Test plan configuration (frozen dataclass)."""

    def test_plan_config_frozen(self):
        """PlanConfig is immutable — cannot change at runtime."""
        plan = PLANS[PlanType.PRO]
        with self.assertRaises(AttributeError):
            plan.price_kopecks = 0  # type: ignore

    def test_plan_tokens_limits(self):
        """Verify correct token limits for each plan."""
        self.assertEqual(PLANS[PlanType.FREE].tokens_monthly, 50_000)
        self.assertEqual(PLANS[PlanType.PRO].tokens_monthly, 500_000)
        self.assertEqual(PLANS[PlanType.TEAM].tokens_monthly, 2_000_000)
        self.assertEqual(PLANS[PlanType.ENTERPRISE].tokens_monthly, -1)

    def test_plan_prices(self):
        """Verify correct prices in kopecks."""
        self.assertEqual(PLANS[PlanType.FREE].price_kopecks, 0)
        self.assertEqual(PLANS[PlanType.PRO].price_kopecks, 149_000)
        self.assertEqual(PLANS[PlanType.PRO].price_rub, 1490.0)

    def test_get_plan_valid(self):
        """get_plan returns correct config."""
        plan = get_plan(PlanType.PRO)
        self.assertIsInstance(plan, PlanConfig)
        self.assertEqual(plan.name, PlanType.PRO)

    def test_get_plan_invalid(self):
        """get_plan raises KeyError for unknown plan."""
        with self.assertRaises(KeyError):
            get_plan("nonexistent")

    def test_enterprise_features_superset(self):
        """Enterprise has all features of lower plans."""
        ent = PLANS[PlanType.ENTERPRISE].features
        pro = PLANS[PlanType.PRO].features
        self.assertTrue(pro.issubset(ent))


# ===================================================================
# User Model Tests
# ===================================================================


class TestUserModel(TestCase):
    """Test User model (FR-02, FR-03, SR-01)."""

    def test_create_user_with_email(self):
        """User can be created with email."""
        user = UserFactory()
        self.assertIsNotNone(user.pk)
        self.assertIn("@", user.email)

    def test_create_user_with_telegram(self):
        """User can be created with Telegram ID."""
        user = TelegramUserFactory()
        self.assertIsNotNone(user.pk)
        self.assertIsNotNone(user.telegram_id)
        self.assertIsNone(user.email)

    def test_api_key_hash_unique(self):
        """Two users cannot have the same API key hash."""
        user1 = UserFactory()
        with self.assertRaises(IntegrityError):
            User.objects.create(
                email="dup@test.com",
                api_key_hash=user1.api_key_hash,
            )

    def test_generate_api_key_format(self):
        """Generated API keys start with 'sc_' prefix."""
        raw_key, key_hash = User.generate_api_key()
        self.assertTrue(raw_key.startswith("sc_"))
        self.assertEqual(len(key_hash), 64)  # SHA-256

    def test_hash_api_key_deterministic(self):
        """Same raw key always produces same hash."""
        raw_key, expected_hash = User.generate_api_key()
        actual_hash = User.hash_api_key(raw_key)
        self.assertEqual(actual_hash, expected_hash)

    def test_user_str_email(self):
        """User __str__ shows email when available."""
        user = UserFactory(email="test@safeclaw.ru")
        self.assertEqual(str(user), "test@safeclaw.ru")

    def test_user_str_telegram(self):
        """User __str__ shows tg:ID when no email."""
        user = TelegramUserFactory(telegram_id=12345)
        self.assertEqual(str(user), "tg:12345")


# ===================================================================
# Subscription Model Tests
# ===================================================================


class TestSubscriptionModel(TestCase):
    """Test Subscription model (FR-01, FR-07, FR-08)."""

    def test_subscription_default_free(self):
        """New subscription defaults to FREE plan."""
        sub = SubscriptionFactory()
        self.assertEqual(sub.plan, PlanType.FREE)
        self.assertEqual(sub.status, SubscriptionStatus.FREE)
        self.assertEqual(sub.tokens_used, 0)

    def test_tokens_remaining(self):
        """tokens_remaining = limit - used."""
        sub = SubscriptionFactory(
            tokens_limit=50000,
            tokens_used=30000,
        )
        self.assertEqual(sub.tokens_remaining, 20000)

    def test_tokens_remaining_unlimited(self):
        """Unlimited plan returns inf."""
        sub = SubscriptionFactory(tokens_limit=-1)
        self.assertEqual(sub.tokens_remaining, float("inf"))

    def test_usage_percent(self):
        """Usage percentage is calculated correctly."""
        sub = SubscriptionFactory(
            tokens_limit=100,
            tokens_used=80,
        )
        self.assertAlmostEqual(sub.usage_percent, 80.0)

    def test_usage_percent_unlimited(self):
        """Unlimited plan returns 0% usage."""
        sub = SubscriptionFactory(tokens_limit=-1)
        self.assertEqual(sub.usage_percent, 0.0)

    def test_is_over_limit(self):
        """is_over_limit detects exhausted tokens."""
        sub = SubscriptionFactory(
            tokens_limit=100,
            tokens_used=100,
        )
        self.assertTrue(sub.is_over_limit)

    def test_is_not_over_limit(self):
        """is_over_limit is False when tokens remain."""
        sub = SubscriptionFactory(
            tokens_limit=100,
            tokens_used=50,
        )
        self.assertFalse(sub.is_over_limit)

    def test_unlimited_never_over_limit(self):
        """Unlimited plan is never over limit."""
        sub = SubscriptionFactory(
            tokens_limit=-1,
            tokens_used=999999,
        )
        self.assertFalse(sub.is_over_limit)

    def test_auto_set_tokens_limit_from_plan(self):
        """tokens_limit auto-set from plan config if None."""
        user = UserFactory()
        sub = Subscription(
            user=user,
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=None,
        )
        sub.save()
        self.assertEqual(
            sub.tokens_limit,
            PLANS[PlanType.PRO].tokens_monthly,
        )


# ===================================================================
# BillingEvent Tests (Event Sourcing — Immutability)
# ===================================================================


class TestBillingEvent(TestCase):
    """Test BillingEvent immutability (NFR-06, AC-07)."""

    def test_create_event(self):
        """BillingEvent can be created."""
        event = BillingEventFactory(
            event_type=BillingEventType.CREATED,
            amount_kopecks=149_000,
        )
        self.assertIsNotNone(event.pk)
        self.assertEqual(event.amount_kopecks, 149_000)

    def test_event_immutable_no_update(self):
        """BillingEvent cannot be updated after creation."""
        event = BillingEventFactory()
        event.amount_kopecks = 999
        with self.assertRaises(ValueError) as ctx:
            event.save()
        self.assertIn("immutable", str(ctx.exception))

    def test_event_immutable_no_delete(self):
        """BillingEvent cannot be deleted."""
        event = BillingEventFactory()
        with self.assertRaises(ValueError) as ctx:
            event.delete()
        self.assertIn("immutable", str(ctx.exception))

    def test_idempotency_key_unique(self):
        """Duplicate idempotency keys are rejected (NFR-02)."""
        sub = SubscriptionFactory()
        BillingEventFactory(
            subscription=sub,
            idempotency_key="unique-key-1",
        )
        with self.assertRaises(IntegrityError):
            BillingEventFactory(
                subscription=sub,
                idempotency_key="unique-key-1",
            )

    def test_event_str_with_amount(self):
        """Event __str__ includes formatted amount."""
        event = BillingEventFactory(
            event_type=BillingEventType.ACTIVATED,
            amount_kopecks=149_000,
        )
        result = str(event)
        self.assertIn("1490.00₽", result)


# ===================================================================
# UsageLog Tests
# ===================================================================


class TestUsageLog(TestCase):
    """Test UsageLog model (FR-07)."""

    def test_create_usage_log(self):
        """UsageLog is created with correct fields."""
        log = UsageLogFactory(
            tokens_input=200,
            tokens_output=100,
            model_used="deepseek-v3",
            cost_kopecks=30,
        )
        self.assertEqual(log.tokens_input, 200)
        self.assertEqual(log.tokens_output, 100)
        self.assertEqual(log.model_used, "deepseek-v3")

    def test_tokens_total(self):
        """tokens_total = input + output."""
        log = UsageLogFactory(
            tokens_input=200,
            tokens_output=100,
        )
        self.assertEqual(log.tokens_total, 300)

    def test_usage_log_timestamps(self):
        """UsageLog gets timestamp on creation."""
        log = UsageLogFactory()
        self.assertIsNotNone(log.timestamp)
