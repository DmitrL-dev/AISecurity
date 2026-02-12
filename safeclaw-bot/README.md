# SafeClaw Telegram Bot

Telegram-бот для управления подпиской SafeClaw.

## Быстрый старт

```bash
# 1. Установите зависимости
pip install -r requirements.txt

# 2. Установите токен бота
export SAFECLAW_BOT_TOKEN="your-token-from-botfather"

# 3. Запустите
python bot.py
```

## Команды бота

| Команда | Описание |
|---------|----------|
| `/start` | Регистрация + приветствие |
| `/plan` | Текущий тариф + usage |
| `/upgrade` | Выбор тарифа |
| `/apikey` | API-ключ (показать / пересоздать) |
| `/usage` | Статистика токенов |
| `/help` | Справка |

## Переменные окружения

| Переменная | Обязательна | Описание |
|-----------|-------------|----------|
| `SAFECLAW_BOT_TOKEN` | ✅ | Токен от @BotFather |
| `SAFECLAW_DB_URL` | ❌ | SQLite по умолчанию |
| `SAFECLAW_ADMIN_IDS` | ❌ | Telegram ID администраторов |
| `YOOKASSA_SHOP_ID` | ❌ | ЮKassa shop ID |
| `YOOKASSA_SECRET` | ❌ | ЮKassa secret key |

## Docker

```bash
docker build -t safeclaw-bot .
docker run -d \
  -e SAFECLAW_BOT_TOKEN="..." \
  --name safeclaw-bot \
  safeclaw-bot
```
