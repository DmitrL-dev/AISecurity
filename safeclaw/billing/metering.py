"""
SafeClaw Billing — Token Metering Service.

Per billing_spec.md v1.1 §3.4, §5 Phase 4.
Atomic token counting with F() expressions and SELECT FOR UPDATE.
Thread-safe, race-condition-free token consumption.
"""

import logging

from django.db import transaction
from django.db.models import F

from .models import Subscription, UsageLog
from .plans import SubscriptionStatus

logger = logging.getLogger(__name__)


class TokenLimitExceeded(Exception):
    """Raised when subscription token limit is exceeded."""

    def __init__(self, subscription_id, tokens_used, tokens_limit):
        self.subscription_id = subscription_id
        self.tokens_used = tokens_used
        self.tokens_limit = tokens_limit
        super().__init__(f"Token limit exceeded: {tokens_used}/{tokens_limit}")


class SubscriptionNotActive(Exception):
    """Raised when subscription is not in active state."""

    def __init__(self, subscription_id, status):
        self.subscription_id = subscription_id
        self.status = status
        super().__init__(f"Subscription {subscription_id} is {status}")


def check_quota(subscription: Subscription) -> bool:
    """
    Check if subscription has remaining token quota.

    Returns True if tokens are available, False otherwise.
    Does NOT consume tokens — use consume_tokens() for that.
    """
    if subscription.status != SubscriptionStatus.ACTIVE:
        if subscription.status != SubscriptionStatus.FREE:
            return False

    if subscription.tokens_limit == -1:
        return True  # unlimited

    return subscription.tokens_used < subscription.tokens_limit


def consume_tokens(
    subscription: Subscription,
    tokens_input: int,
    tokens_output: int,
    model_used: str,
    cost_kopecks: int = 0,
) -> UsageLog:
    """
    Consume tokens atomically using F() expressions.

    1. SELECT FOR UPDATE (locks row)
    2. Check quota
    3. Increment counter with F('tokens_used')
    4. Create UsageLog for audit

    Args:
        subscription: User's subscription.
        tokens_input: Input tokens consumed.
        tokens_output: Output tokens generated.
        model_used: LLM model identifier.
        cost_kopecks: Internal cost for analytics.

    Returns:
        UsageLog record.

    Raises:
        SubscriptionNotActive: If not ACTIVE/FREE.
        TokenLimitExceeded: If over limit.
    """
    total_tokens = tokens_input + tokens_output

    with transaction.atomic():
        # Lock row for update
        sub = Subscription.objects.select_for_update().get(
            pk=subscription.pk,
        )

        # Check status
        if sub.status not in (
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.FREE,
        ):
            raise SubscriptionNotActive(
                sub.pk,
                sub.status,
            )

        # Check limit (skip for unlimited)
        if sub.tokens_limit != -1:
            if sub.tokens_used + total_tokens > sub.tokens_limit:
                raise TokenLimitExceeded(
                    sub.pk,
                    sub.tokens_used + total_tokens,
                    sub.tokens_limit,
                )

        # Atomic increment — no race conditions
        Subscription.objects.filter(pk=sub.pk).update(
            tokens_used=F("tokens_used") + total_tokens,
        )

        # Create usage log
        usage_log = UsageLog.objects.create(
            subscription=sub,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
            model_used=model_used,
            cost_kopecks=cost_kopecks,
        )

    logger.debug(
        "Consumed %d tokens (sub=%s, model=%s)",
        total_tokens,
        sub.pk,
        model_used,
    )

    return usage_log


def reset_monthly_tokens(subscription: Subscription) -> int:
    """
    Reset monthly token counter to 0.

    Called by Celery Beat on billing cycle renewal.

    Returns:
        Previous tokens_used value.
    """
    with transaction.atomic():
        sub = Subscription.objects.select_for_update().get(
            pk=subscription.pk,
        )
        previous = sub.tokens_used
        sub.tokens_used = 0
        sub.save()

    logger.info(
        "Reset tokens: sub=%s (was %d)",
        sub.pk,
        previous,
    )
    return previous


def get_usage_stats(
    subscription: Subscription,
) -> dict:
    """
    Get current usage statistics for a subscription.

    Returns dict with tokens_used, tokens_limit,
    tokens_remaining, usage_percent, is_over_limit.
    """
    sub = Subscription.objects.get(pk=subscription.pk)
    return {
        "tokens_used": sub.tokens_used,
        "tokens_limit": sub.tokens_limit,
        "tokens_remaining": sub.tokens_remaining,
        "usage_percent": round(sub.usage_percent, 1),
        "is_over_limit": sub.is_over_limit,
        "plan": sub.plan,
        "status": sub.status,
    }
