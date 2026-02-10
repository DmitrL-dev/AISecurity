"""
SafeClaw Billing — ЮKassa SDK Wrapper.

Per billing_spec.md v1.1 §3.3, §5 Phase 2.
Handles: payment creation, recurring payments, refunds, webhook verification.
All operations are idempotent via idempotency_key.
"""

import logging
import uuid
from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings

from yookassa import Configuration, Payment, Refund
from yookassa.domain.notification import (
    WebhookNotificationEventType,
    WebhookNotificationFactory,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Configuration (initialized on first use)
# ---------------------------------------------------------------------------


def _ensure_configured():
    """Configure ЮKassa SDK with credentials from Django settings."""
    if not Configuration.account_id:
        Configuration.account_id = settings.YOOKASSA_SHOP_ID
        Configuration.secret_key = settings.YOOKASSA_SECRET_KEY


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class PaymentResult:
    """Result of a payment creation."""

    payment_id: str
    confirmation_url: str | None
    status: str
    idempotency_key: str
    payment_method_id: str | None = None


@dataclass
class WebhookEvent:
    """Parsed webhook notification from ЮKassa."""

    event_type: str
    payment_id: str
    status: str
    amount_kopecks: int
    currency: str
    payment_method_id: str | None
    metadata: dict | None
    idempotency_key: str  # ЮKassa payment ID as idem key


@dataclass
class RefundResult:
    """Result of a refund operation."""

    refund_id: str
    status: str
    amount_kopecks: int


# ---------------------------------------------------------------------------
# Payment Operations
# ---------------------------------------------------------------------------


def create_payment(
    amount_kopecks: int,
    description: str,
    return_url: str | None = None,
    save_payment_method: bool = True,
    metadata: dict | None = None,
    idempotency_key: str | None = None,
) -> PaymentResult:
    """
    Create a new payment via ЮKassa.

    Args:
        amount_kopecks: Amount in kopecks (e.g., 149000 = 1490₽).
        description: Payment description shown to user.
        return_url: URL to redirect after payment.
        save_payment_method: Save for recurring (default True).
        metadata: Extra data attached to payment.
        idempotency_key: Unique key for idempotent retry.

    Returns:
        PaymentResult with confirmation_url for redirect.
    """
    _ensure_configured()

    if idempotency_key is None:
        idempotency_key = str(uuid.uuid4())

    if return_url is None:
        return_url = settings.YOOKASSA_RETURN_URL

    amount_rub = Decimal(amount_kopecks) / 100

    payment_data = {
        "amount": {
            "value": str(amount_rub),
            "currency": "RUB",
        },
        "confirmation": {
            "type": "redirect",
            "return_url": return_url,
        },
        "capture": True,
        "description": description,
        "save_payment_method": save_payment_method,
    }
    if metadata:
        payment_data["metadata"] = metadata

    payment = Payment.create(
        payment_data,
        idempotency_key=idempotency_key,
    )

    confirmation_url = None
    if payment.confirmation and hasattr(payment.confirmation, "confirmation_url"):
        confirmation_url = payment.confirmation.confirmation_url

    pm_id = None
    if payment.payment_method:
        pm_id = payment.payment_method.id

    logger.info(
        "Payment created: id=%s status=%s amount=%s₽",
        payment.id,
        payment.status,
        amount_rub,
    )

    return PaymentResult(
        payment_id=payment.id,
        confirmation_url=confirmation_url,
        status=payment.status,
        idempotency_key=idempotency_key,
        payment_method_id=pm_id,
    )


def create_recurring_payment(
    amount_kopecks: int,
    payment_method_id: str,
    description: str,
    metadata: dict | None = None,
    idempotency_key: str | None = None,
) -> PaymentResult:
    """
    Create recurring (auto) payment using saved method.

    Args:
        amount_kopecks: Amount in kopecks.
        payment_method_id: Saved ЮKassa payment method ID.
        description: Payment description.
        metadata: Extra data.
        idempotency_key: Unique key.

    Returns:
        PaymentResult (no confirmation_url — auto-captured).
    """
    _ensure_configured()

    if idempotency_key is None:
        idempotency_key = str(uuid.uuid4())

    amount_rub = Decimal(amount_kopecks) / 100

    payment = Payment.create(
        {
            "amount": {
                "value": str(amount_rub),
                "currency": "RUB",
            },
            "capture": True,
            "payment_method_id": payment_method_id,
            "description": description,
            "metadata": metadata or {},
        },
        idempotency_key=idempotency_key,
    )

    logger.info(
        "Recurring payment created: id=%s status=%s",
        payment.id,
        payment.status,
    )

    return PaymentResult(
        payment_id=payment.id,
        confirmation_url=None,
        status=payment.status,
        idempotency_key=idempotency_key,
        payment_method_id=payment_method_id,
    )


def create_refund(
    payment_id: str,
    amount_kopecks: int,
    idempotency_key: str | None = None,
) -> RefundResult:
    """
    Create a refund for a payment.

    Args:
        payment_id: Original ЮKassa payment ID.
        amount_kopecks: Refund amount (can be partial).
        idempotency_key: Unique key.

    Returns:
        RefundResult.
    """
    _ensure_configured()

    if idempotency_key is None:
        idempotency_key = str(uuid.uuid4())

    amount_rub = Decimal(amount_kopecks) / 100

    refund = Refund.create(
        {
            "payment_id": payment_id,
            "amount": {
                "value": str(amount_rub),
                "currency": "RUB",
            },
        },
        idempotency_key=idempotency_key,
    )

    logger.info(
        "Refund created: id=%s status=%s amount=%s₽",
        refund.id,
        refund.status,
        amount_rub,
    )

    return RefundResult(
        refund_id=refund.id,
        status=refund.status,
        amount_kopecks=amount_kopecks,
    )


# ---------------------------------------------------------------------------
# Webhook Processing
# ---------------------------------------------------------------------------


def parse_webhook(request_body: str | bytes) -> WebhookEvent:
    """
    Parse and validate a ЮKassa webhook notification.

    The ЮKassa SDK handles signature verification via
    HTTP Basic Auth (shop_id:secret_key) — this must be
    configured in Django middleware/view layer.

    Args:
        request_body: Raw JSON body from webhook POST.

    Returns:
        WebhookEvent with parsed payment data.

    Raises:
        ValueError: If notification is malformed.
    """
    notification = WebhookNotificationFactory.create(
        request_body,
    )

    payment = notification.object

    # Extract amount in kopecks
    amount_kopecks = 0
    if payment.amount:
        amount_kopecks = int(Decimal(payment.amount.value) * 100)

    # Extract payment method ID (for recurring)
    pm_id = None
    if payment.payment_method and hasattr(payment.payment_method, "id"):
        pm_id = payment.payment_method.id

    # Map ЮKassa event types
    event_type = notification.event

    logger.info(
        "Webhook parsed: event=%s payment_id=%s status=%s",
        event_type,
        payment.id,
        payment.status,
    )

    return WebhookEvent(
        event_type=event_type,
        payment_id=payment.id,
        status=payment.status,
        amount_kopecks=amount_kopecks,
        currency=payment.amount.currency if payment.amount else "RUB",
        payment_method_id=pm_id,
        metadata=payment.metadata,
        idempotency_key=f"wh_{payment.id}",
    )
