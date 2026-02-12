# SafeClaw Telegram Bot — Tasks

> **Компонент:** saas/safeclaw-bot/
> **Дата:** 2026-02-12

---

## Реализованные (MVP)

- [x] T-1: Скелет бота (python-telegram-bot, polling)
- [x] T-2: Модели данных (User, Plan, APIKey)
- [x] T-3: /start — регистрация + welcome
- [x] T-4: /plan — текущий тариф
- [x] T-5: /upgrade — inline keyboard с планами
- [x] T-6: /apikey — показ + regen + confirm
- [x] T-7: /usage — статистика
- [x] T-8: /help
- [x] T-9: Callback handlers (plan select, apikey regen/confirm)
- [x] T-10: Dockerfile

## Roadmap

- [ ] T-11: YooKassa production интеграция
- [ ] T-12: Webhook mode (production)
- [ ] T-13: PostgreSQL миграция (вместо SQLite)
- [ ] T-14: Usage reset cron (monthly)
- [ ] T-15: Уведомления при 80%/100% использования
- [ ] T-16: /invoice — история платежей
- [ ] T-17: Admin-команды (/admin stats, /admin users)
