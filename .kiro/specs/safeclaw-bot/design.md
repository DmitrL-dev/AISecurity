# SafeClaw Telegram Bot — Design

> **Компонент:** saas/safeclaw-bot/
> **Статус:** Implemented (MVP)
> **Дата:** 2026-02-12

---

## 1. Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    SafeClaw Telegram Bot                      │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐       │
│  │ Telegram  │    │   bot.py     │    │  models.py   │       │
│  │  User     │◄──►│  (Handlers)  │◄──►│  (SQLite)    │       │
│  └──────────┘    └──────┬───────┘    └──────────────┘       │
│                         │                                     │
│                    ┌────┴─────┐                               │
│                    │ YooKassa │                               │
│                    │ Payments │                               │
│                    └──────────┘                               │
│                                                               │
│  Commands: /start /plan /upgrade /apikey /usage /help         │
│  Callbacks: plan:<name> apikey:{regen,confirm}                │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Компоненты

### 2.1 Command Handlers (bot.py)

| Handler | Trigger | Описание |
|---------|---------|----------|
| `cmd_start` | /start | Регистрация или welcome-back |
| `cmd_plan` | /plan | Текущий план + usage bar |
| `cmd_upgrade` | /upgrade | Inline keyboard с планами |
| `cmd_apikey` | /apikey | Показ ключа + кнопка regen |
| `cmd_usage` | /usage | Статистика с progress bar |
| `cmd_help` | /help | Список команд |

### 2.2 Callback Handlers (bot.py)

| Handler | Callback Data | Описание |
|---------|---------------|----------|
| `handle_plan_select` | `plan:<name>` | Создаёт Telegram Payment |
| `handle_apikey_regen` | `apikey:regen` | Показывает подтверждение |
| `handle_apikey_confirm` | `apikey:confirm` | Генерирует новый ключ |

### 2.3 Message Templates

Все сообщения в HTML parse mode с эмодзи:

```
WELCOME_MSG: 
  🛡️ Добро пожаловать в SafeClaw!
  ✅ Аккаунт создан
  📋 Тариф: <b>{plan}</b>
  🔑 API-ключ: <code>{api_key}</code>

RETURNING_MSG:
  👋 С возвращением, {name}!
  📋 Тариф: <b>{plan}</b>
  📊 Использовано: {used:,} / {limit:,} токенов ({pct:.0f}%)
  🔑 API-ключ: <code>{api_key}</code>
```

### 2.4 Data Model (models.py)

```python
class User:
    tg_id: int          # Telegram user ID (primary key)
    name: str           # Display name
    plan: str           # free|personal|developer|team
    api_key: str        # sc_<uuid>
    tokens_used: int    # Current period usage
    tokens_limit: int   # Plan limit
    created_at: datetime
    
class Plan:
    name: str           # free, personal, developer, team
    display: str        # "Free", "Personal", etc.
    tokens: int         # Monthly limit
    price_rub: int      # Price in rubles
```

### 2.5 Payment Flow

```
/upgrade → Inline keyboard (4 plans)
    → User taps "Developer (₽2,999)"
    → callback_handler → handle_plan_select
    → bot.send_invoice(
        title="SafeClaw Developer",
        description="1M tokens/month",
        prices=[LabeledPrice("Developer", 299900)]  # kopeks
      )
    → User pays in Telegram → successful_payment
    → Update user.plan + user.tokens_limit
    → Send confirmation message
```

---

## 3. Config (config.py)

```python
BOT_TOKEN = os.getenv("BOT_TOKEN")
YOKASSA_PROVIDER_TOKEN = os.getenv("YOKASSA_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///safeclaw.db")
SENTINEL_API_URL = os.getenv("SENTINEL_API", "http://localhost:8000")
```

---

## 4. Docker

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "bot.py"]
```

---

## 5. Verification Plan

### Tests
```bash
cd saas/safeclaw-bot
python -m pytest  # if tests exist
```

### Manual Testing
1. Запустить бота локально: `BOT_TOKEN=xxx python bot.py`
2. Отправить /start → проверить создание аккаунта
3. /plan → проверить отображение тарифа
4. /apikey → проверить показ ключа и кнопку regen
5. /upgrade → проверить inline keyboard
