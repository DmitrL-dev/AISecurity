"""SafeClaw Bot — ЮKassa Payment Integration (Stub).

Full implementation requires:
- ЮKassa shop_id + secret_key
- HTTPS webhook endpoint
- ИП/ООО registration

This module provides the interface; actual ЮKassa
calls are gated behind config.yookassa_shop_id check.
"""

import logging
from dataclasses import dataclass

from config import PLANS, BotConfig

logger = logging.getLogger(__name__)


@dataclass
class PaymentResult:
    """Result of payment creation."""

    success: bool
    payment_url: str = ""
    payment_id: str = ""
    error: str = ""


def create_payment(
    config: BotConfig,
    user_telegram_id: int,
    plan_name: str,
) -> PaymentResult:
    """Create ЮKassa payment for plan upgrade.

    Returns PaymentResult with confirmation URL.
    """
    if not config.yookassa_shop_id:
        return PaymentResult(
            success=False,
            error=(
                "ЮKassa не настроена. "
                "Установите YOOKASSA_SHOP_ID "
                "и YOOKASSA_SECRET."
            ),
        )

    plan = PLANS.get(plan_name)
    if not plan or plan.price_rub == 0:
        return PaymentResult(
            success=False,
            error=f"Тариф '{plan_name}' не найден " "или бесплатный.",
        )

    try:
        # ЮKassa SDK integration point
        # from yookassa import Configuration, Payment
        # Configuration.account_id = config.yookassa_shop_id
        # Configuration.secret_key = config.yookassa_secret
        # payment = Payment.create({
        #     "amount": {
        #         "value": str(plan.price_rub) + ".00",
        #         "currency": "RUB"
        #     },
        #     "confirmation": {
        #         "type": "redirect",
        #         "return_url": f"https://t.me/SafeClawBot"
        #     },
        #     "capture": True,
        #     "description": f"SafeClaw {plan.display_name}",
        #     "metadata": {
        #         "telegram_id": user_telegram_id,
        #         "plan": plan_name,
        #     }
        # })
        # return PaymentResult(
        #     success=True,
        #     payment_url=payment.confirmation.confirmation_url,
        #     payment_id=payment.id,
        # )

        logger.info(
            "Payment stub: %s -> %s (%d RUB)",
            user_telegram_id,
            plan_name,
            plan.price_rub,
        )
        return PaymentResult(
            success=False,
            error="ЮKassa интеграция в разработке. " "Свяжитесь с @SafeClawSupport.",
        )

    except Exception as e:
        logger.error("Payment error: %s", e)
        return PaymentResult(
            success=False,
            error=f"Ошибка платежа: {e}",
        )


def handle_webhook_notification(
    data: dict,
) -> dict | None:
    """Process ЮKassa webhook notification.

    Returns dict with user info if payment succeeded.
    """
    event_type = data.get("event")
    if event_type != "payment.succeeded":
        return None

    obj = data.get("object", {})
    metadata = obj.get("metadata", {})
    telegram_id = metadata.get("telegram_id")
    plan = metadata.get("plan")

    if telegram_id and plan:
        return {
            "telegram_id": int(telegram_id),
            "plan": plan,
            "payment_id": obj.get("id"),
            "amount": obj.get("amount", {}).get("value"),
        }
    return None
