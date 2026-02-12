"""
SafeClaw Billing — Webhook Handler Service.

Per billing_spec.md v1.1 §3.3, §2.2 (NFR-02: idempotent webhooks).
Processes ЮKassa webhook notifications and updates subscriptions.
"""

import logging
from typing import Literal

from django.db import IntegrityError, transaction

from .models import BillingEvent, Subscription
from .plans import (
    BillingEventType,
    SubscriptionStatus,
    PLANS,
)
from .yokassa import WebhookEvent

logger = logging.getLogger(__name__)


# Result type for webhook processing
WebhookResult = Literal["processed", "duplicate", "error"]


def process_webhook(event: WebhookEvent) -> WebhookResult:
    """
    Process a parsed ЮKassa webhook event.

    Idempotent: duplicate events (same idempotency_key)
    are detected and silently ignored.

    Args:
        event: Parsed WebhookEvent from yokassa.parse_webhook.

    Returns:
        "processed" — event handled successfully
        "duplicate" — event already processed (idempotent)
        "error" — processing failed
    """
    # Check for duplicate (idempotent processing)
    if BillingEvent.objects.filter(
        idempotency_key=event.idempotency_key,
    ).exists():
        logger.info(
            "Duplicate webhook ignored: %s",
            event.idempotency_key,
        )
        return "duplicate"

    # Route by event type
    handlers = {
        "payment.succeeded": _handle_payment_succeeded,
        "payment.canceled": _handle_payment_failed,
        "payment.waiting_for_capture": _handle_payment_waiting,
        "refund.succeeded": _handle_refund_succeeded,
    }

    handler = handlers.get(event.event_type)
    if handler is None:
        logger.warning(
            "Unknown webhook event: %s",
            event.event_type,
        )
        return "error"

    try:
        handler(event)
        return "processed"
    except Exception:
        logger.exception(
            "Webhook processing failed: %s %s",
            event.event_type,
            event.payment_id,
        )
        return "error"


# ---------------------------------------------------------------------------
# Event handlers
# ---------------------------------------------------------------------------


def _handle_payment_succeeded(event: WebhookEvent):
    """
    Handle successful payment.

    1. Find subscription by metadata.subscription_id
    2. Activate subscription
    3. Save payment method for recurring
    4. Create immutable BillingEvent
    """
    sub_id = _extract_subscription_id(event)
    if sub_id is None:
        logger.error(
            "No subscription_id in payment metadata: %s",
            event.payment_id,
        )
        return

    with transaction.atomic():
        sub = Subscription.objects.select_for_update().get(
            pk=sub_id,
        )

        # Determine event type
        if sub.status == SubscriptionStatus.FREE:
            evt_type = BillingEventType.ACTIVATED
        elif sub.status in (
            SubscriptionStatus.PAST_DUE,
            SubscriptionStatus.SUSPENDED,
        ):
            evt_type = BillingEventType.RENEWED
        else:
            evt_type = BillingEventType.RENEWED

        # Update subscription
        sub.status = SubscriptionStatus.ACTIVE

        # Save payment method for recurring
        if event.payment_method_id:
            sub.yokassa_payment_method_id = event.payment_method_id

        # Reset tokens on renewal
        plan_config = PLANS.get(sub.plan)
        if plan_config:
            sub.tokens_used = 0
            sub.tokens_limit = plan_config.tokens_monthly

        sub.save()

        # Create immutable event
        BillingEvent.objects.create(
            subscription=sub,
            event_type=evt_type,
            amount_kopecks=event.amount_kopecks,
            yokassa_payment_id=event.payment_id,
            idempotency_key=event.idempotency_key,
            metadata_json={
                "payment_method_id": event.payment_method_id,
                "currency": event.currency,
            },
        )

    logger.info(
        "Payment succeeded: sub=%s → %s",
        sub_id,
        SubscriptionStatus.ACTIVE,
    )


def _handle_payment_failed(event: WebhookEvent):
    """
    Handle failed/cancelled payment.

    Moves ACTIVE subscription to PAST_DUE (grace period starts).
    """
    sub_id = _extract_subscription_id(event)
    if sub_id is None:
        return

    with transaction.atomic():
        sub = Subscription.objects.select_for_update().get(
            pk=sub_id,
        )

        if sub.status == SubscriptionStatus.ACTIVE:
            sub.status = SubscriptionStatus.PAST_DUE
            sub.save()

            BillingEvent.objects.create(
                subscription=sub,
                event_type=BillingEventType.PAYMENT_FAILED,
                amount_kopecks=event.amount_kopecks,
                yokassa_payment_id=event.payment_id,
                idempotency_key=event.idempotency_key,
                metadata_json={
                    "reason": "payment_cancelled",
                },
            )

            logger.info(
                "Payment failed: sub=%s → PAST_DUE",
                sub_id,
            )


def _handle_payment_waiting(event: WebhookEvent):
    """Handle payment waiting for capture (informational)."""
    logger.info(
        "Payment waiting for capture: %s",
        event.payment_id,
    )


def _handle_refund_succeeded(event: WebhookEvent):
    """
    Handle successful refund.

    Creates BillingEvent for audit trail.
    """
    sub_id = _extract_subscription_id(event)
    if sub_id is None:
        return

    with transaction.atomic():
        sub = Subscription.objects.select_for_update().get(
            pk=sub_id,
        )

        try:
            BillingEvent.objects.create(
                subscription=sub,
                event_type=BillingEventType.REFUNDED,
                amount_kopecks=event.amount_kopecks,
                yokassa_payment_id=event.payment_id,
                idempotency_key=event.idempotency_key,
                metadata_json={
                    "refund": True,
                },
            )
        except IntegrityError:
            # Duplicate refund event — ignore
            logger.info(
                "Duplicate refund event: %s",
                event.idempotency_key,
            )
            return

    logger.info(
        "Refund succeeded: sub=%s amount=%s kopecks",
        sub_id,
        event.amount_kopecks,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_subscription_id(
    event: WebhookEvent,
) -> str | None:
    """Extract subscription_id from payment metadata."""
    if event.metadata and "subscription_id" in event.metadata:
        return event.metadata["subscription_id"]
    return None
