# SafeClaw Billing — Requirements

> **Компонент:** saas/safeclaw/
> **Статус:** Implemented (MVP)
> **Дата:** 2026-02-12

---

## 1. Обзор

Django-based SaaS backend для SafeClaw. Два Django-приложения: **billing** (подписки, тарифы, оплата, metering) и **router** (LLM API proxy с SENTINEL Shield защитой). Реализует полный цикл: регистрация → выбор плана → оплата → API-ключ → использование LLM → metering → лимиты.

---

## 2. Функциональные требования

### FR-1: Billing App

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-1.1 | Модели: Tenant, Plan, Subscription, APIKey, UsageRecord | P0 |
| FR-1.2 | 4 тарифных плана (Free, Personal, Developer, Team) | P0 |
| FR-1.3 | API-ключи: генерация, валидация, ротация | P0 |
| FR-1.4 | Token metering: подсчёт использованных токенов per tenant | P0 |
| FR-1.5 | Lifecycle: создание tenant → подписка → usage tracking | P0 |
| FR-1.6 | YooKassa webhooks для обработки платежей | P0 |
| FR-1.7 | Notification при 80%/100% лимита | P1 |
| FR-1.8 | Audit log всех действий | P1 |

### FR-2: Router App

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-2.1 | Unified API endpoint для LLM запросов | P0 |
| FR-2.2 | Provider routing: GigaChat, DeepSeek, YandexGPT, OpenAI-compatible | P0 |
| FR-2.3 | SENTINEL Shield middleware на входящие промпты | P0 |
| FR-2.4 | SSRF protection | P0 |
| FR-2.5 | Rate limiting per API key | P1 |

### FR-3: REST API (DRF)

| ID | Endpoint | Метод | Описание |
|----|----------|-------|----------|
| FR-3.1 | `/api/billing/plans/` | GET | Список тарифов |
| FR-3.2 | `/api/billing/subscribe/` | POST | Оформление подписки |
| FR-3.3 | `/api/billing/usage/` | GET | Текущее использование |
| FR-3.4 | `/api/billing/keys/` | GET/POST | Управление API-ключами |
| FR-3.5 | `/api/billing/webhooks/yokassa/` | POST | YooKassa callback |
| FR-3.6 | `/api/router/complete/` | POST | Unified LLM API |

---

## 3. Нефункциональные требования

| ID | Требование |
|----|------------|
| NFR-1 | Django 5.x + Python 3.11+ |
| NFR-2 | DRF для API serialization |
| NFR-3 | SQLite для dev, PostgreSQL для prod |
| NFR-4 | Dogfooding: SENTINEL Shield на собственном API |
| NFR-5 | pytest + coverage > 80% |
| NFR-6 | Pre-commit hooks (black, isort, mypy) |

---

## 4. User Stories

### US-1: Разработчик подключает API

```gherkin
GIVEN я зарегистрированный tenant
WHEN я создаю API-ключ через /api/billing/keys/
THEN получаю ключ формата sc_<uuid>
AND могу вызывать /api/router/complete/ с X-API-Key header
```

### US-2: Metering учитывает токены

```gherkin
GIVEN я отправил запрос на /api/router/complete/
WHEN LLM провайдер ответил (500 токенов)
THEN UsageRecord создаётся с подсчётом токенов
AND мой usage counter обновляется
```

### US-3: Shield блокирует атаку

```gherkin
GIVEN SENTINEL Shield middleware активен
WHEN я отправляю промпт с injection
THEN запрос блокируется до отправки в LLM
AND возвращается 403 с деталями угрозы
```

---

## 5. Acceptance Criteria

- [x] AC-1: Модели Tenant, Plan, Subscription, APIKey, UsageRecord
- [x] AC-2: REST API endpoints через DRF
- [x] AC-3: 4 тарифных плана с лимитами
- [x] AC-4: Token metering per request
- [x] AC-5: YooKassa webhook handler
- [x] AC-6: LLM router (GigaChat, DeepSeek, YandexGPT)
- [x] AC-7: Shield middleware integration
- [x] AC-8: SSRF protection
- [x] AC-9: Tests (billing + router)

---

## 6. Файловая структура

```
saas/safeclaw/
├── billing/
│   ├── models.py         # Tenant, Plan, Subscription, APIKey, UsageRecord
│   ├── views.py          # DRF views
│   ├── serializers.py    # DRF serializers
│   ├── urls.py           # URL routing
│   ├── plans.py          # Plan definitions + limits
│   ├── lifecycle.py      # Tenant lifecycle management
│   ├── metering.py       # Token usage tracking
│   ├── auth.py           # API key authentication
│   ├── yokassa.py        # YooKassa payment integration
│   ├── webhooks.py       # Payment webhook handlers
│   ├── notifications.py  # Usage alerts
│   ├── middleware.py      # Auth middleware
│   ├── tasks.py          # Background tasks
│   ├── admin.py          # Django admin config
│   └── tests/
│       ├── test_api.py
│       ├── test_lifecycle.py
│       ├── test_metering.py
│       ├── test_models.py
│       ├── test_phase6.py
│       └── test_yokassa.py
├── router/
│   ├── engine.py         # LLM routing logic
│   ├── views.py          # Unified /complete/ endpoint
│   ├── serializers.py
│   ├── urls.py
│   ├── shield_middleware.py  # SENTINEL Shield integration
│   ├── ssrf_protection.py    # SSRF sanitization
│   ├── providers/
│   │   ├── base.py       # Abstract LLM provider
│   │   ├── gigachat.py   # GigaChat API
│   │   ├── deepseek.py   # DeepSeek API
│   │   ├── yandexgpt.py  # YandexGPT API
│   │   └── openai_compat.py  # OpenAI-compatible
│   └── tests/
│       ├── test_router.py
│       ├── test_shield.py
│       ├── test_ssrf.py
│       └── dogfood_shield.py
├── safeclaw/
│   ├── settings.py       # Django settings
│   ├── urls.py           # Root URL config
│   ├── wsgi.py           # WSGI entry
│   └── asgi.py           # ASGI entry
├── manage.py
├── pytest.ini
├── .env.example
├── .pre-commit-config.yaml
└── db.sqlite3
```

---

## 7. Зависимости

| Пакет | Назначение |
|-------|------------|
| Django 5.x | Web framework |
| djangorestframework | REST API |
| yokassa | YooKassa SDK |
| gigachat | Sber GigaChat SDK |
| deepseek-api | DeepSeek SDK |
| yandexcloud | YandexGPT SDK |
| pytest-django | Testing |
| black, isort | Code formatting |

---

## 8. Риски

| Риск | Митигация |
|------|-----------|
| LLM провайдер недоступен | Fallback к альтернативному провайдеру |
| YooKassa webhook не доходит | Retry с exponential backoff |
| Shield middleware тормозит | Async scan, configurable timeout |
| SQLite lock contention | Миграция на PostgreSQL в prod |
