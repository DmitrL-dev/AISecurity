#!/usr/bin/env python3
"""SafeClaw Telegram Bot — MVP.

Commands:
    /start   — Register + welcome
    /plan    — Current plan + usage
    /upgrade — Choose plan + payment
    /apikey  — Show / regenerate API key
    /usage   — Token usage stats
    /help    — Help message
"""

import logging
import html

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from config import BotConfig, PLANS
from models import (
    init_db,
    get_or_create_user,
    regenerate_api_key,
)
from payments import create_payment

logging.basicConfig(
    format=("%(asctime)s - %(name)s - " "%(levelname)s - %(message)s"),
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# -- Global state --
config = BotConfig.from_env()
SessionFactory = init_db(config.database_url.replace("sqlite+aiosqlite", "sqlite"))

WELCOME_MSG = """🛡️ <b>Добро пожаловать в SafeClaw!</b>

Ваш AI-щит для безопасной работы с большими \
языковыми моделями.

✅ Аккаунт создан
📋 Тариф: <b>{plan}</b>
🔑 API-ключ: <code>{api_key}</code>

<b>Быстрый старт:</b>
1️⃣ Скопируйте API-ключ выше
2️⃣ Добавьте в вашего AI-агента
3️⃣ Все запросы теперь под защитой Shield

Команды: /plan · /apikey · /upgrade · /usage · /help"""

RETURNING_MSG = """👋 <b>С возвращением, \
{name}!</b>

📋 Тариф: <b>{plan}</b>
📊 Использовано: {used:,} / {limit:,} токенов \
({pct:.0f}%)
🔑 API-ключ: <code>{api_key}</code>

Команды: /plan · /apikey · /upgrade · /usage · /help"""


# --- Command Handlers ---


async def cmd_start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /start — register or welcome back."""
    tg_user = update.effective_user
    if not tg_user:
        return

    session = SessionFactory()
    try:
        user, created = get_or_create_user(
            session,
            telegram_id=tg_user.id,
            username=tg_user.username,
            first_name=tg_user.first_name,
        )
        if created:
            text = WELCOME_MSG.format(
                plan=f"{user.plan_emoji} {user.plan.title()}",
                api_key=user.api_key,
            )
            logger.info(
                "New user: @%s (id=%d)",
                tg_user.username,
                tg_user.id,
            )
        else:
            name = html.escape(tg_user.first_name or tg_user.username or "User")
            text = RETURNING_MSG.format(
                name=name,
                plan=f"{user.plan_emoji} {user.plan.title()}",
                used=user.tokens_used,
                limit=user.tokens_limit,
                pct=user.usage_percent,
                api_key=user.api_key,
            )
    finally:
        session.close()

    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_plan(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /plan — show current plan details."""
    tg_user = update.effective_user
    if not tg_user:
        return

    session = SessionFactory()
    try:
        user, _ = get_or_create_user(session, telegram_id=tg_user.id)
        plan_cfg = PLANS.get(user.plan, PLANS["free"])

        features = "\n".join(f"  • {f}" for f in plan_cfg.features)
        price = (
            "Бесплатно" if plan_cfg.price_rub == 0 else f"{plan_cfg.price_rub:,} ₽/мес"
        )

        text = (
            f"📋 <b>Ваш тариф: "
            f"{plan_cfg.display_name}</b>\n\n"
            f"💰 Стоимость: {price}\n"
            f"🤖 Агенты: {user.agents_used}"
            f"/{user.agents_limit}\n"
            f"🔤 Токены: {user.tokens_used:,}"
            f"/{user.tokens_limit:,} "
            f"({user.usage_percent:.0f}%)\n\n"
            f"<b>Включено:</b>\n{features}\n\n"
            f"Хотите больше? /upgrade"
        )
    finally:
        session.close()

    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_upgrade(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /upgrade — show plan selection."""
    tg_user = update.effective_user
    if not tg_user:
        return

    session = SessionFactory()
    try:
        user, _ = get_or_create_user(session, telegram_id=tg_user.id)
        current = user.plan
    finally:
        session.close()

    buttons = []
    for name, plan in PLANS.items():
        if name == current:
            label = f"✅ {plan.display_name} (текущий)"
            callback = f"plan_info:{name}"
        elif name == "enterprise":
            label = f"{plan.display_name} — по запросу"
            callback = "plan_enterprise"
        else:
            price = f"{plan.price_rub:,} ₽/мес"
            label = f"{plan.display_name} — {price}"
            callback = f"plan_select:{name}"
        buttons.append([InlineKeyboardButton(label, callback_data=callback)])

    text = (
        "🚀 <b>Выберите тариф SafeClaw</b>\n\n"
        f"Текущий: <b>{PLANS[current].display_name}"
        "</b>\n\n"
        "Выберите новый тариф для апгрейда:"
    )
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def cmd_apikey(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /apikey — show or regenerate API key."""
    tg_user = update.effective_user
    if not tg_user:
        return

    session = SessionFactory()
    try:
        user, _ = get_or_create_user(session, telegram_id=tg_user.id)
        api_key = user.api_key
    finally:
        session.close()

    buttons = [
        [
            InlineKeyboardButton(
                "🔄 Пересоздать ключ",
                callback_data="apikey_regen",
            )
        ]
    ]
    text = (
        "🔑 <b>Ваш API-ключ:</b>\n\n"
        f"<code>{api_key}</code>\n\n"
        "📋 Скопируйте и добавьте в конфигурацию "
        "вашего AI-агента.\n\n"
        "⚠️ Не делитесь ключом — он даёт "
        "доступ к вашему аккаунту."
    )
    await update.message.reply_text(
        text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def cmd_usage(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /usage — token usage statistics."""
    tg_user = update.effective_user
    if not tg_user:
        return

    session = SessionFactory()
    try:
        user, _ = get_or_create_user(session, telegram_id=tg_user.id)

        # Progress bar
        pct = min(user.usage_percent, 100)
        filled = int(pct / 5)
        bar = "█" * filled + "░" * (20 - filled)

        text = (
            "📊 <b>Использование за текущий месяц</b>"
            "\n\n"
            f"🔤 Токены: {user.tokens_used:,} "
            f"/ {user.tokens_limit:,}\n"
            f"[{bar}] {pct:.0f}%\n\n"
            f"🤖 Агенты: {user.agents_used} "
            f"/ {user.agents_limit}\n\n"
            f"📋 Тариф: "
            f"{PLANS[user.plan].display_name}\n\n"
        )

        if pct >= 80:
            text += (
                "⚠️ Вы использовали "
                f"{pct:.0f}% лимита.\n"
                "Рассмотрите /upgrade для "
                "увеличения лимитов."
            )
    finally:
        session.close()

    await update.message.reply_text(text, parse_mode="HTML")


async def cmd_help(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle /help — show available commands."""
    text = (
        "🛡️ <b>SafeClaw Bot — Справка</b>\n\n"
        "<b>Команды:</b>\n"
        "/start — Регистрация\n"
        "/plan — Текущий тариф\n"
        "/upgrade — Сменить тариф\n"
        "/apikey — API-ключ\n"
        "/usage — Статистика\n"
        "/help — Эта справка\n\n"
        "<b>Поддержка:</b> @SafeClawSupport\n"
        "<b>Документация:</b> safeclaw.ru/docs\n"
        "<b>GitHub:</b> github.com/DmitrL-dev"
        "/AISecurity"
    )
    await update.message.reply_text(text, parse_mode="HTML")


# --- Callback Query Handlers ---


async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Handle inline keyboard callbacks."""
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    data = query.data
    tg_user = update.effective_user
    if not tg_user:
        return

    # --- API Key Regeneration ---
    if data == "apikey_regen":
        await handle_apikey_regen(query, tg_user)

    # --- Plan Selection ---
    elif data.startswith("plan_select:"):
        plan_name = data.split(":")[1]
        await handle_plan_select(query, tg_user, plan_name)

    # --- Plan Info (current) ---
    elif data.startswith("plan_info:"):
        await query.edit_message_text(
            "✅ Это ваш текущий тариф. " "Используйте /plan для деталей.",
            parse_mode="HTML",
        )

    # --- Enterprise ---
    elif data == "plan_enterprise":
        await query.edit_message_text(
            "🏛️ <b>Enterprise</b>\n\n"
            "Для Enterprise-тарифа "
            "свяжитесь с нами:\n"
            "📧 enterprise@safeclaw.ru\n"
            "💬 @SafeClawSupport",
            parse_mode="HTML",
        )

    # --- Confirm regen ---
    elif data == "apikey_confirm":
        await handle_apikey_confirm(query, tg_user)

    elif data == "apikey_cancel":
        await query.edit_message_text(
            "✅ Ключ не изменён.",
            parse_mode="HTML",
        )


async def handle_apikey_regen(query, tg_user):
    """Ask for confirmation before regenerating."""
    buttons = [
        [
            InlineKeyboardButton(
                "✅ Да, пересоздать",
                callback_data="apikey_confirm",
            ),
            InlineKeyboardButton(
                "❌ Отмена",
                callback_data="apikey_cancel",
            ),
        ]
    ]
    await query.edit_message_text(
        "⚠️ <b>Пересоздать API-ключ?</b>\n\n"
        "Старый ключ перестанет работать "
        "немедленно. Все агенты потребуют "
        "обновления.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def handle_apikey_confirm(query, tg_user):
    """Actually regenerate the API key."""
    session = SessionFactory()
    try:
        user, _ = get_or_create_user(session, telegram_id=tg_user.id)
        new_key = regenerate_api_key(session, user)
    finally:
        session.close()

    await query.edit_message_text(
        "🔑 <b>Новый API-ключ:</b>\n\n"
        f"<code>{new_key}</code>\n\n"
        "✅ Старый ключ деактивирован.\n"
        "Обновите конфигурацию ваших агентов.",
        parse_mode="HTML",
    )


async def handle_plan_select(query, tg_user, plan_name):
    """Handle plan selection and payment."""
    plan = PLANS.get(plan_name)
    if not plan:
        await query.edit_message_text("❌ Тариф не найден.")
        return

    result = create_payment(config, tg_user.id, plan_name)

    if result.success:
        buttons = [
            [
                InlineKeyboardButton(
                    "💳 Оплатить",
                    url=result.payment_url,
                )
            ]
        ]
        await query.edit_message_text(
            f"💳 <b>Оплата: {plan.display_name}"
            f"</b>\n\n"
            f"Сумма: {plan.price_rub:,} ₽/мес\n\n"
            "Нажмите кнопку для оплаты:",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(buttons),
        )
    else:
        await query.edit_message_text(
            f"⏳ {result.error}\n\n"
            "На данный момент доступен "
            "бесплатный тариф Free.\n"
            "Платные тарифы скоро будут доступны!",
            parse_mode="HTML",
        )


# --- Application ---


def main() -> None:
    """Start the bot."""
    if not config.bot_token:
        print(
            "❌ SAFECLAW_BOT_TOKEN not set!\n"
            "Set it: export SAFECLAW_BOT_TOKEN="
            "'your-token-from-botfather'"
        )
        return

    app = Application.builder().token(config.bot_token).build()

    # Command handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("plan", cmd_plan))
    app.add_handler(CommandHandler("upgrade", cmd_upgrade))
    app.add_handler(CommandHandler("apikey", cmd_apikey))
    app.add_handler(CommandHandler("usage", cmd_usage))
    app.add_handler(CommandHandler("help", cmd_help))

    # Callback handler for inline keyboards
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("🛡️ SafeClaw Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
