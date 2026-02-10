"""
SafeClaw Billing — Notification Service.

Sends notifications via email (SMTP) and Telegram Bot API.
All notifications are async-safe (called from Celery tasks).
"""

import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import Subscription

logger = logging.getLogger(__name__)


def _send_email(
    user,
    subject: str,
    message: str,
) -> bool:
    """Send email notification to user (if email set)."""
    if not user.email:
        return False

    try:
        send_mail(
            subject=f"[SafeClaw] {subject}",
            message=message,
            from_email=getattr(
                settings,
                "DEFAULT_FROM_EMAIL",
                "billing@safeclaw.dev",
            ),
            recipient_list=[user.email],
            fail_silently=False,
        )
        logger.info(
            "Email sent to %s: %s",
            user.email,
            subject,
        )
        return True
    except Exception as e:
        logger.exception(
            "Email failed to %s: %s",
            user.email,
            e,
        )
        return False


def _send_telegram(
    user,
    message: str,
) -> bool:
    """
    Send Telegram notification (if telegram_id set).

    Requires TELEGRAM_BOT_TOKEN in settings.
    """
    if not user.telegram_id:
        return False

    bot_token = getattr(
        settings,
        "TELEGRAM_BOT_TOKEN",
        None,
    )
    if not bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN not configured")
        return False

    try:
        import requests

        resp = requests.post(
            f"https://api.telegram.org/" f"bot{bot_token}/sendMessage",
            json={
                "chat_id": user.telegram_id,
                "text": message,
                "parse_mode": "HTML",
            },
            timeout=10,
        )
        resp.raise_for_status()
        logger.info(
            "Telegram sent to %s: ok",
            user.telegram_id,
        )
        return True
    except Exception as e:
        logger.exception(
            "Telegram failed to %s: %s",
            user.telegram_id,
            e,
        )
        return False


def _notify(
    sub: Subscription,
    subject: str,
    message: str,
):
    """Send notification via all available channels."""
    _send_email(sub.user, subject, message)
    _send_telegram(sub.user, message)


# -----------------------------------------------------------
# Public notification functions
# -----------------------------------------------------------


def notify_approaching_limit(sub: Subscription):
    """Notify user: 80%+ tokens used."""
    pct = round(sub.usage_percent)
    _notify(
        sub,
        subject=f"Использовано {pct}% токенов",
        message=(
            f"⚠️ <b>SafeClaw:</b> Вы использовали "
            f"{pct}% лимита токенов "
            f"({sub.tokens_used:,} / "
            f"{sub.tokens_limit:,}).\n\n"
            f"Рекомендуем обновить план для "
            f"продолжения работы."
        ),
    )


def notify_over_limit(sub: Subscription):
    """Notify user: 100% tokens used, requests blocked."""
    _notify(
        sub,
        subject="Лимит токенов исчерпан",
        message=(
            f"🚫 <b>SafeClaw:</b> Лимит токенов "
            f"исчерпан ({sub.tokens_used:,} / "
            f"{sub.tokens_limit:,}).\n\n"
            f"API-запросы будут отклоняться "
            f"(HTTP 429) до обновления плана "
            f"или начала нового периода."
        ),
    )


def notify_subscription_suspended(sub: Subscription):
    """Notify user: subscription suspended."""
    _notify(
        sub,
        subject="Подписка приостановлена",
        message=(
            "⏸ <b>SafeClaw:</b> Ваша подписка "
            "приостановлена из-за неоплаты.\n\n"
            "Оплатите в течение 30 дней, чтобы "
            "возобновить доступ. После этого "
            "подписка будет автоматически отменена."
        ),
    )


def notify_subscription_cancelled(sub: Subscription):
    """Notify user: subscription cancelled."""
    _notify(
        sub,
        subject="Подписка отменена",
        message=(
            "❌ <b>SafeClaw:</b> Ваша подписка "
            "отменена. Вы переведены на бесплатный "
            "план (50,000 токенов/мес).\n\n"
            "Вы можете оформить новую подписку "
            "в любое время."
        ),
    )


def notify_payment_success(
    sub: Subscription,
    amount_rub: float,
):
    """Notify user: payment processed."""
    _notify(
        sub,
        subject=f"Оплата {amount_rub:.0f}₽ принята",
        message=(
            f"✅ <b>SafeClaw:</b> Оплата "
            f"{amount_rub:.0f}₽ успешно обработана.\n"
            f"План: {sub.get_plan_display()}\n"
            f"Токены: {sub.tokens_limit:,}/мес"
        ),
    )
