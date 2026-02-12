# SafeClaw Telegram Bot — Requirements

> **Компонент:** saas/safeclaw-bot/
> **Статус:** Implemented (MVP)
> **Дата:** 2026-02-12

---

## 1. Обзор

Telegram бот для управления подписками SafeClaw. Пользователи регистрируются, получают API-ключ, выбирают тарифный план, оплачивают через Telegram Payments (YooKassa), и мониторят использование токенов — всё через привычный интерфейс Telegram.

---

## 2. Функциональные требования

### FR-1: Команды бота

| ID | Команда | Описание | Приоритет |
|----|---------|----------|-----------|
| FR-1.1 | `/start` | Регистрация + welcome message, создание аккаунта и API-ключа | P0 |
| FR-1.2 | `/plan` | Текущий план: тариф, лимиты, использование | P0 |
| FR-1.3 | `/upgrade` | Выбор плана через inline keyboard | P0 |
| FR-1.4 | `/apikey` | Показать или перегенерировать API-ключ | P0 |
| FR-1.5 | `/usage` | Статистика использования токенов | P0 |
| FR-1.6 | `/help` | Список доступных команд | P0 |

### FR-2: Тарифные планы

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-2.1 | Free: 1,000 токенов/мес, 0₽ | P0 |
| FR-2.2 | Personal: 100,000 токенов/мес, 499₽ | P0 |
| FR-2.3 | Developer: 1,000,000 токенов/мес, 2,999₽ | P0 |
| FR-2.4 | Team: 10,000,000 токенов/мес, 9,999₽ | P0 |
| FR-2.5 | Отображение лимита и текущего usage в процентах | P0 |

### FR-3: Оплата

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-3.1 | Telegram Payments API через YooKassa | P0 |
| FR-3.2 | Инвойс с описанием плана и ценой | P0 |
| FR-3.3 | Webhook обработка successful_payment | P0 |
| FR-3.4 | Автоматическое обновление плана после оплаты | P0 |

### FR-4: API Key Management

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-4.1 | Генерация ключа формата `sc_<uuid>` при /start | P0 |
| FR-4.2 | Показ текущего ключа через /apikey | P0 |
| FR-4.3 | Перегенерация с подтверждением (inline button) | P0 |
| FR-4.4 | Inline keyboard: "🔄 Перегенерировать" → "⚠️ Подтвердить" | P0 |

### FR-5: Inline Keyboard Callbacks

| ID | Callback ID | Описание | Приоритет |
|----|-------------|----------|-----------|
| FR-5.1 | `plan:<plan_name>` | Выбор конкретного плана | P0 |
| FR-5.2 | `apikey:regen` | Запрос перегенерации ключа | P0 |
| FR-5.3 | `apikey:confirm` | Подтверждение перегенерации | P0 |

---

## 3. Нефункциональные требования

| ID | Требование |
|----|------------|
| NFR-1 | Ответ на команду < 2 секунды |
| NFR-2 | Бот работает в polling mode (development) и webhook mode (production) |
| NFR-3 | Docker-образ для деплоя |
| NFR-4 | Язык интерфейса: русский |
| NFR-5 | HTML parsing mode для форматированных сообщений |

---

## 4. User Stories

### US-1: Регистрация

```gherkin
GIVEN я новый пользователь
WHEN я отправляю /start боту
THEN бот создаёт аккаунт
AND показывает welcome-сообщение с тарифом и API-ключом
AND даёт инструкцию быстрого старта
```

### US-2: Апгрейд

```gherkin
GIVEN я на тарифе Free
WHEN я отправляю /upgrade
THEN вижу inline-клавиатуру с тарифами (Personal, Developer, Team)
WHEN я нажимаю "Developer"
THEN получаю Telegram Payment инвойс на 2,999₽
WHEN оплата проходит
THEN мой тариф обновляется до Developer
```

### US-3: Перегенерация ключа

```gherkin
GIVEN у меня есть API-ключ
WHEN я отправляю /apikey
THEN вижу текущий ключ и кнопку "🔄 Перегенерировать"
WHEN я нажимаю кнопку
THEN вижу "⚠️ Старый ключ перестанет работать. Подтвердить?"
WHEN я нажимаю "Подтвердить"
THEN получаю новый ключ
```

---

## 5. Acceptance Criteria

- [x] AC-1: /start создаёт аккаунт и отдаёт API-ключ
- [x] AC-2: /plan показывает текущий тариф и usage
- [x] AC-3: /upgrade показывает inline-клавиатуру с планами
- [x] AC-4: /apikey показывает ключ и кнопку перегенерации
- [x] AC-5: /usage показывает процент использования
- [x] AC-6: /help выводит список команд
- [x] AC-7: Callback handlers обрабатывают нажатия
- [ ] AC-8: Telegram Payments интеграция с YooKassa

---

## 6. Файловая структура

```
saas/safeclaw-bot/
├── bot.py              # Main bot (команды, callbacks, payment)
├── config.py           # ENV config (BOT_TOKEN, YOKASSA_TOKEN)
├── models.py           # SQLite models (User, Plan, APIKey)
├── payments.py         # YooKassa Telegram Payments integration
├── requirements.txt    # python-telegram-bot, etc.
├── Dockerfile          # Production container
└── README.md
```

---

## 7. Зависимости

| Пакет | Версия | Назначение |
|-------|--------|------------|
| python-telegram-bot | 20.x | Telegram Bot API framework |
| yokassa | 3.x | YooKassa платежи |
| aiosqlite | 0.20+ | Async SQLite |

---

## 8. Риски

| Риск | Митигация |
|------|-----------|
| YooKassa отклоняет AI-сервис | Альтернатива: Stars (Telegram), Stripe |
| Rate limiting Telegram API | Polling с интервалом, webhook в prod |
| Потеря SQLite при рестарте | Persistent volume в Docker |
