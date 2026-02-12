"""
SafeClaw Billing — Celery Tasks for Scheduled Operations.

Handles:
1. Grace period processing (3 days past_due → suspended)
2. Auto-cancellation (30 days suspended → cancelled)
3. Monthly token reset
4. Notification dispatch

For Celery Beat, add to settings:
    CELERY_BEAT_SCHEDULE = {
        'process-grace-periods': {
            'task': 'billing.tasks.task_process_grace_periods',
            'schedule': crontab(hour=3, minute=0),  # daily 3am
        },
        'process-auto-cancellations': {
            'task': 'billing.tasks.task_process_auto_cancellations',
            'schedule': crontab(hour=4, minute=0),  # daily 4am
        },
        'process-monthly-reset': {
            'task': 'billing.tasks.task_monthly_token_reset',
            'schedule': crontab(day_of_month=1, hour=0, minute=0),
        },
    }
"""

import logging

from .lifecycle import (
    process_auto_cancellations,
    process_grace_periods,
)
from .metering import reset_monthly_tokens
from .models import Subscription
from .notifications import (
    notify_approaching_limit,
    notify_over_limit,
)
from .plans import SubscriptionStatus

logger = logging.getLogger(__name__)

# Try to import Celery; if not installed, tasks are
# plain functions callable from management commands
try:
    from celery import shared_task
except ImportError:
    # Fallback: decorator that does nothing
    def shared_task(func=None, **kwargs):
        if func:
            return func
        return lambda f: f


@shared_task(name="billing.tasks.process_grace_periods")
def task_process_grace_periods():
    """Process subscriptions in grace period (3 days)."""
    count = process_grace_periods()
    logger.info(
        "Grace period processing: %d suspended",
        count,
    )
    return count


@shared_task(
    name="billing.tasks.process_auto_cancellations",
)
def task_process_auto_cancellations():
    """Auto-cancel subscriptions suspended 30+ days."""
    count = process_auto_cancellations()
    logger.info(
        "Auto-cancel processing: %d cancelled",
        count,
    )
    return count


@shared_task(name="billing.tasks.monthly_token_reset")
def task_monthly_token_reset():
    """Reset token counters on 1st of each month."""
    subs = Subscription.objects.filter(
        status__in=[
            SubscriptionStatus.ACTIVE,
            SubscriptionStatus.FREE,
        ],
    )
    count = 0
    for sub in subs:
        prev = reset_monthly_tokens(sub)
        if prev > 0:
            count += 1
    logger.info(
        "Monthly reset: %d subscriptions reset",
        count,
    )
    return count


@shared_task(name="billing.tasks.check_usage_alerts")
def task_check_usage_alerts():
    """Check for subscriptions approaching token limit."""
    subs = Subscription.objects.filter(
        status=SubscriptionStatus.ACTIVE,
        tokens_limit__gt=0,
    )

    alerts_sent = 0
    for sub in subs:
        pct = sub.usage_percent
        if sub.is_over_limit:
            notify_over_limit(sub)
            alerts_sent += 1
        elif pct >= 80:
            notify_approaching_limit(sub)
            alerts_sent += 1

    logger.info(
        "Usage alerts: %d sent",
        alerts_sent,
    )
    return alerts_sent
