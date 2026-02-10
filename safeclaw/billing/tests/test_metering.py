"""
SafeClaw Billing — Tests for Token Metering.

Per billing_spec.md v1.1 §6.1 — Metering (10 tests).
Tests atomic token consumption, quota checks, limits, and reset.
"""

from django.test import TestCase

from billing.metering import (
    SubscriptionNotActive,
    TokenLimitExceeded,
    check_quota,
    consume_tokens,
    get_usage_stats,
    reset_monthly_tokens,
)
from billing.models import Subscription, UsageLog
from billing.plans import (
    PlanType,
    SubscriptionStatus,
    PLANS,
)
from billing.tests import SubscriptionFactory


class TestCheckQuota(TestCase):
    """Test quota pre-flight checks."""

    def test_active_has_quota(self):
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=500_000,
            tokens_used=100_000,
        )
        self.assertTrue(check_quota(sub))

    def test_active_over_limit(self):
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=500_000,
            tokens_used=500_000,
        )
        self.assertFalse(check_quota(sub))

    def test_unlimited_always_has_quota(self):
        sub = SubscriptionFactory(
            plan=PlanType.ENTERPRISE,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=-1,
            tokens_used=99_999_999,
        )
        self.assertTrue(check_quota(sub))

    def test_suspended_no_quota(self):
        sub = SubscriptionFactory(
            status=SubscriptionStatus.SUSPENDED,
            tokens_limit=500_000,
        )
        self.assertFalse(check_quota(sub))

    def test_free_tier_has_quota(self):
        sub = SubscriptionFactory(
            plan=PlanType.FREE,
            status=SubscriptionStatus.FREE,
            tokens_limit=50_000,
            tokens_used=10_000,
        )
        self.assertTrue(check_quota(sub))


class TestConsumeTokens(TestCase):
    """Test atomic token consumption."""

    def test_consume_creates_usage_log(self):
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=500_000,
            tokens_used=0,
        )
        log = consume_tokens(
            sub,
            tokens_input=100,
            tokens_output=200,
            model_used="deepseek-v3",
            cost_kopecks=15,
        )

        self.assertIsInstance(log, UsageLog)
        self.assertEqual(log.tokens_input, 100)
        self.assertEqual(log.tokens_output, 200)
        self.assertEqual(log.model_used, "deepseek-v3")
        self.assertEqual(log.cost_kopecks, 15)

    def test_consume_increments_counter(self):
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=500_000,
            tokens_used=1_000,
        )
        consume_tokens(
            sub,
            tokens_input=500,
            tokens_output=500,
            model_used="gigachat-lite",
        )

        sub.refresh_from_db()
        self.assertEqual(sub.tokens_used, 2_000)

    def test_consume_exceeds_limit_raises(self):
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=500_000,
            tokens_used=499_900,
        )

        with self.assertRaises(TokenLimitExceeded) as ctx:
            consume_tokens(
                sub,
                tokens_input=100,
                tokens_output=100,  # total 200 > 100 remaining
                model_used="deepseek-v3",
            )

        self.assertEqual(ctx.exception.tokens_limit, 500_000)

    def test_consume_unlimited_no_limit_check(self):
        sub = SubscriptionFactory(
            plan=PlanType.ENTERPRISE,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=-1,
            tokens_used=99_000_000,
        )

        # Should not raise
        log = consume_tokens(
            sub,
            tokens_input=1_000_000,
            tokens_output=1_000_000,
            model_used="gpt-4",
        )
        self.assertIsNotNone(log)

    def test_consume_inactive_raises(self):
        sub = SubscriptionFactory(
            status=SubscriptionStatus.SUSPENDED,
            tokens_limit=500_000,
        )

        with self.assertRaises(SubscriptionNotActive):
            consume_tokens(
                sub,
                tokens_input=100,
                tokens_output=100,
                model_used="deepseek-v3",
            )


class TestResetMonthlyTokens(TestCase):
    """Test monthly token reset."""

    def test_reset_returns_previous(self):
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=500_000,
            tokens_used=350_000,
        )
        previous = reset_monthly_tokens(sub)

        self.assertEqual(previous, 350_000)

        sub.refresh_from_db()
        self.assertEqual(sub.tokens_used, 0)


class TestGetUsageStats(TestCase):
    """Test usage statistics retrieval."""

    def test_stats_correct(self):
        sub = SubscriptionFactory(
            plan=PlanType.PRO,
            status=SubscriptionStatus.ACTIVE,
            tokens_limit=500_000,
            tokens_used=250_000,
        )
        stats = get_usage_stats(sub)

        self.assertEqual(stats["tokens_used"], 250_000)
        self.assertEqual(stats["tokens_limit"], 500_000)
        self.assertEqual(stats["tokens_remaining"], 250_000)
        self.assertEqual(stats["usage_percent"], 50.0)
        self.assertFalse(stats["is_over_limit"])
        self.assertEqual(stats["plan"], PlanType.PRO)
