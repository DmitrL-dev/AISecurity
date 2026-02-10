# SafeClaw Billing Module — Спецификация

> **Version:** 1.1
> **Дата:** 2026-02-10
> **Статус:** Approved
> **Язык:** Русский

---

## 1. Overview

### 1.1 Purpose

Production-grade модуль биллинга для SafeClaw — управление подписками, тарифами, платежами и учётом потребления токенов. Обеспечивает рекуррентные платежи через ЮKassa, соответствие 54-ФЗ (онлайн-касса), и полный аудит-трейл всех финансовых операций.

### 1.2 Scope

**In Scope:**
- Тарифные планы (Free / Pro / Team / Enterprise)
- Интеграция с ЮKassa (платежи, рекуррент, возвраты, чеки)
- Учёт потребления токенов (metering)
- Rate limiting по тарифу
- JWT-аутентификация + API-ключи
- Webhook-обработка (idempotent)
- Event sourcing для финансовых операций
- PostgreSQL как хранилище

**Out of Scope:**
- Frontend/UI (отдельная спецификация)
- Telegram-бот (отдельная спецификация)
- Интеграция с конкретными LLM-провайдерами (Provider Router — отдельный модуль)
- Сертификация ФСТЭК
- Бухгалтерская отчётность (аутсорс)

### 1.3 References

- [ЮKassa API Documentation](https://yookassa.ru/developers/)
- [ЮKassa Python SDK](https://github.com/yoomoney/yookassa-sdk-python)
- SafeClaw Business Plan v2.0 (safeclaw_business_plan.md)
- SafeClaw Detailed Plan v2.0 (safeclaw_detailed_plan.md)
- 54-ФЗ «О применении ККТ»
- 152-ФЗ «О персональных данных»

---

## 2. Requirements

### 2.1 Functional Requirements

| ID | Требование | Приоритет |
|----|-----------|-----------|
| **FR-01** | Система поддерживает 4 тарифных плана: Free, Pro (1490₽), Team (4990₽ + 990₽/user), Enterprise (от 49900₽) | P0 |
| **FR-02** | Пользователь может зарегистрироваться через email или Telegram ID | P0 |
| **FR-03** | При регистрации генерируется уникальный API-ключ (256-bit, хэшируется SHA-256 для хранения) | P0 |
| **FR-04** | Пользователь может создать платёж через ЮKassa для перехода на платный план | P0 |
| **FR-05** | После успешной оплаты подписка активируется автоматически через webhook | P0 |
| **FR-06** | Рекуррентные платежи: автосписание каждые 30 дней через сохранённый payment method | P0 |
| **FR-07** | Token metering: каждый API-запрос учитывает потреблённые input/output tokens | P0 |
| **FR-08** | Rate limiting: при превышении лимита плана возвращается HTTP 429 с описанием | P0 |
| **FR-09** | Возврат платежа (refund) через API | P1 |
| **FR-10** | Апгрейд/даунгрейд плана с пропорциональным перерасчётом | P1 |
| **FR-11** | Grace period (3 дня) при неудавшемся автосписании | P1 |
| **FR-12** | Overage billing: доп. токены сверх лимита по цене плана | P2 |
| **FR-13** | Пользователь получает email-уведомление при 80% и 100% лимита | P2 |
| **FR-14** | Admin API для ручного управления подписками | P1 |
| **FR-15** | Usage dashboard endpoint — статистика потребления за период | P1 |

### 2.2 Non-Functional Requirements

| ID | Требование | Метрика |
|----|-----------|---------|
| **NFR-01** | Латентность metering не добавляет >5ms к запросу | p99 < 5ms |
| **NFR-02** | Webhook обработка — idempotent (повторный вызов безопасен) | 100% |
| **NFR-03** | Данные не теряются при крэше сервера | WAL + ACID |
| **NFR-04** | Система обрабатывает до 1000 concurrent пользователей | load test |
| **NFR-05** | API-ключ невозможно восстановить из хранимого хэша | SHA-256 |
| **NFR-06** | Все финансовые операции имеют полный audit trail | Event sourcing |
| **NFR-07** | Время восстановления после сбоя < 5 минут | RTO |
| **NFR-08** | Бэкап базы — ежедневно, retention 30 дней | pg_dump |

### 2.3 Security Requirements

| ID | Требование |
|----|-----------|
| **SR-01** | API-ключи хранятся только как SHA-256 хэши (оригинал показывается один раз) |
| **SR-02** | Webhook подписи ЮKassa верифицируются через HTTP Basic Auth (shop_id:secret_key) |
| **SR-03** | Все платёжные данные (номера карт) НЕ проходят через SafeClaw — только через ЮKassa |
| **SR-04** | Admin endpoints защищены отдельным JWT с ролью `admin` |
| **SR-05** | Rate limiter защищён от timing attacks (constant-time comparison для API ключей) |
| **SR-06** | PII в billing events минимизировано (email хэшируется в логах) |
| **SR-07** | Все webhook endpoints доступны только по HTTPS |

---

## 3. Architecture

### 3.1 Component Diagram

```
┌──────────────────────────────────────────────────────────┐
│                     SafeClaw API Gateway                  │
│               (Django 5.1 + DRF + Admin)                  │
├───────────┬────────────┬──────────────┬──────────────────┤
│           │            │              │                   │
│  billing/ │  billing/  │  billing/    │  billing/         │
│  views.py │ yokassa.py │ metering.py  │ lifecycle.py      │
│           │            │              │                   │
│  DRF      │  ЮKassa    │  Token       │  Subscription     │
│  endpoints│  SDK       │  counter     │  state machine    │
│           │  wrapper   │  middleware  │                   │
├───────────┴────────────┴──────────────┴──────────────────┤
│                    billing/models.py                       │
│            Django ORM + built-in migrations                │
│                    billing/admin.py                        │
│          Django Admin (управление подписками)              │
├──────────────────────────────────────────────────────────┤
│                      PostgreSQL 16                        │
│              (ACID, WAL, pg_dump backups)                  │
└──────────────────────────────────────────────────────────┘
         │                              ▲
         ▼                              │
  ┌──────────────┐              ┌───────────────┐
  │   ЮKassa     │              │  LLM Provider │
  │   API        │              │  Router       │
  │  (payments)  │──webhook──▶  │  (usage data) │
  └──────────────┘              └───────────────┘
```

### 3.2 Subscription State Machine

```
                         register
                            │
                            ▼
                      ┌───────────┐
                      │   FREE    │◀─────── downgrade
                      └─────┬─────┘
                            │ payment.succeeded
                            ▼
                      ┌───────────┐  auto-renew
              ┌──────▶│  ACTIVE   │◀──────────┐
              │       └─────┬─────┘            │
              │             │                  │
              │    payment.failed    payment.succeeded
              │             │                  │
              │             ▼                  │
              │       ┌───────────┐            │
              │       │ PAST_DUE  │────────────┘
              │       └─────┬─────┘
              │             │ 3 days elapsed, no payment
              │             ▼
              │       ┌───────────┐
              │       │ SUSPENDED │
              │       └─────┬─────┘
              │             │ payment.succeeded
              └─────────────┘
                            │ 30 days elapsed
                            ▼
                      ┌───────────┐
                      │ CANCELLED │
                      └───────────┘

Valid transitions:
  FREE      → ACTIVE     (payment.succeeded)
  ACTIVE    → PAST_DUE   (payment.failed)
  ACTIVE    → CANCELLED  (user.cancel)
  ACTIVE    → ACTIVE     (auto-renew)
  PAST_DUE  → ACTIVE     (payment.succeeded)
  PAST_DUE  → SUSPENDED  (grace_period_expired)
  SUSPENDED → ACTIVE     (payment.succeeded)
  SUSPENDED → CANCELLED  (30_days_expired)
  ACTIVE    → ACTIVE     (upgrade/downgrade)
```

### 3.3 Data Flow: Payment

```
1. Клиент → POST /billing/subscribe {plan: "pro"}
2. API создаёт Payment через ЮKassa SDK
   → idempotency_key = uuid4()
   → save_payment_method = true (для рекуррента)
   → confirmation.type = "redirect"
3. API возвращает confirmation_url → клиент перенаправляется на ЮKassa
4. Клиент оплачивает на странице ЮKassa
5. ЮKassa → POST /billing/webhook {event: "payment.succeeded"}
   → верификация подписи
   → idempotency check (уже обрабатывали?)
   → INSERT billing_event
   → UPDATE subscription.status = ACTIVE
6. API обновляет лимиты пользователя
```

### 3.4 Data Flow: Token Metering

```
1. Клиент → POST /api/chat {prompt: "..."}
2. Middleware:
   → SELECT api_key_hash, plan, tokens_used, tokens_limit
     FROM subscriptions WHERE api_key_hash = SHA256(key)
   → IF tokens_used >= tokens_limit → HTTP 429
   → ELSE → pass request to LLM router
3. LLM Router → ответ от провайдера (token count in response)
4. Middleware:
   → INSERT usage_log (tokens_in, tokens_out, model, cost)
   → UPDATE subscriptions SET tokens_used += total_tokens
     WHERE id = sub_id (atomic, SELECT FOR UPDATE)
5. Возвращаем ответ клиенту
```

---

## 4. API Design

### 4.1 Data Types

```python
# Enums
class PlanType(str, Enum):
    FREE = "free"
    PRO = "pro"
    TEAM = "team"
    ENTERPRISE = "enterprise"

class SubscriptionStatus(str, Enum):
    FREE = "free"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"

class BillingEventType(str, Enum):
    CREATED = "subscription.created"
    ACTIVATED = "subscription.activated"
    RENEWED = "subscription.renewed"
    PAYMENT_FAILED = "payment.failed"
    SUSPENDED = "subscription.suspended"
    CANCELLED = "subscription.cancelled"
    UPGRADED = "subscription.upgraded"
    DOWNGRADED = "subscription.downgraded"
    REFUNDED = "payment.refunded"
    TOKENS_RESET = "tokens.reset"

# Plan Configuration (immutable)
@dataclass(frozen=True)
class PlanConfig:
    name: PlanType
    price_rub: int           # копейки (0 для Free)
    tokens_monthly: int      # лимит токенов/мес
    max_agents: int
    features: frozenset[str]

PLANS = {
    PlanType.FREE: PlanConfig(
        name=PlanType.FREE,
        price_rub=0,
        tokens_monthly=50_000,
        max_agents=1,
        features=frozenset({"shield_basic"}),
    ),
    PlanType.PRO: PlanConfig(
        name=PlanType.PRO,
        price_rub=149_000,  # 1490₽ в копейках
        tokens_monthly=500_000,
        max_agents=5,
        features=frozenset({
            "shield_full", "rlm_memory",
            "priority_routing",
        }),
    ),
    PlanType.TEAM: PlanConfig(
        name=PlanType.TEAM,
        price_rub=499_000,  # 4990₽ base
        tokens_monthly=2_000_000,
        max_agents=20,
        features=frozenset({
            "shield_full", "rlm_memory",
            "priority_routing", "workspace",
            "shared_memory",
        }),
    ),
    PlanType.ENTERPRISE: PlanConfig(
        name=PlanType.ENTERPRISE,
        price_rub=4_990_000,  # 49900₽ base
        tokens_monthly=-1,  # unlimited
        max_agents=-1,      # unlimited
        features=frozenset({
            "shield_full", "rlm_memory",
            "priority_routing", "workspace",
            "shared_memory", "on_prem",
            "sla", "strike_audit",
            "dedicated_support",
        }),
    ),
}
```

### 4.2 Database Models (Django ORM)

```python
import uuid
from django.db import models


class User(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    email = models.EmailField(unique=True, null=True, blank=True)
    telegram_id = models.BigIntegerField(unique=True, null=True, blank=True)
    api_key_hash = models.CharField(
        max_length=64, unique=True, db_index=True,
        help_text="SHA-256 hash of API key. Original shown once.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "billing_users"
        constraints = [
            models.CheckConstraint(
                check=models.Q(email__isnull=False) | models.Q(telegram_id__isnull=False),
                name="user_has_email_or_telegram",
            ),
        ]

    def __str__(self):
        return self.email or f"tg:{self.telegram_id}"


class Subscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name="subscription")
    plan = models.CharField(max_length=20, choices=PlanType.choices)
    status = models.CharField(
        max_length=20, choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.FREE,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    tokens_used = models.PositiveIntegerField(default=0)
    tokens_limit = models.IntegerField(help_text="-1 = unlimited")
    yokassa_payment_method_id = models.CharField(
        max_length=255, null=True, blank=True,
    )

    class Meta:
        db_table = "billing_subscriptions"

    def __str__(self):
        return f"{self.user} — {self.plan} ({self.status})"

    @property
    def tokens_remaining(self) -> int:
        if self.tokens_limit == -1:
            return float("inf")
        return max(0, self.tokens_limit - self.tokens_used)


class BillingEvent(models.Model):
    """Immutable event log — never UPDATE, only INSERT."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    subscription = models.ForeignKey(
        Subscription, on_delete=models.PROTECT, related_name="events",
    )
    event_type = models.CharField(max_length=40, choices=BillingEventType.choices)
    amount_kopeks = models.PositiveIntegerField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="RUB")
    yokassa_payment_id = models.CharField(
        max_length=255, null=True, blank=True,
    )
    idempotency_key = models.CharField(
        max_length=255, unique=True, db_index=True,
    )
    metadata_json = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "billing_events"
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.pk and BillingEvent.objects.filter(pk=self.pk).exists():
            raise ValueError("BillingEvents are immutable — cannot update")
        super().save(*args, **kwargs)


class UsageLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    subscription = models.ForeignKey(
        Subscription, on_delete=models.PROTECT, related_name="usage_logs",
    )
    tokens_input = models.PositiveIntegerField()
    tokens_output = models.PositiveIntegerField()
    model_used = models.CharField(max_length=100)
    cost_kopeks = models.PositiveIntegerField(help_text="Our cost")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "billing_usage_logs"
        ordering = ["-timestamp"]
```

### 4.3 Django Admin Configuration

```python
# billing/admin.py
from django.contrib import admin

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ["email", "telegram_id", "created_at"]
    search_fields = ["email", "telegram_id"]
    readonly_fields = ["api_key_hash", "created_at"]

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ["user", "plan", "status", "tokens_used", "tokens_limit", "expires_at"]
    list_filter = ["plan", "status"]
    readonly_fields = ["started_at", "events_count"]
    actions = ["suspend_selected", "activate_selected"]

    def events_count(self, obj):
        return obj.events.count()

    @admin.action(description="Suspend selected")
    def suspend_selected(self, request, queryset):
        # lifecycle.suspend() for each
        pass

@admin.register(BillingEvent)
class BillingEventAdmin(admin.ModelAdmin):
    list_display = ["subscription", "event_type", "amount_kopeks", "created_at"]
    list_filter = ["event_type"]
    readonly_fields = ["__all__"]  # Immutable

    def has_change_permission(self, request, obj=None):
        return False  # Events are immutable

    def has_delete_permission(self, request, obj=None):
        return False  # Events are immutable
```

### 4.4 REST API Endpoints (DRF)

```
# Auth
POST   /billing/register          → {api_key, user_id}
POST   /billing/login             → {jwt_token}

# Subscriptions
GET    /billing/plans             → [{plan, price, features}]
POST   /billing/subscribe         → {confirmation_url}
DELETE /billing/subscribe         → cancel subscription
PATCH  /billing/subscribe         → upgrade/downgrade

# Usage
GET    /billing/usage             → {tokens_used, tokens_limit, %}
GET    /billing/usage/history     → [{date, tokens, model, cost}]

# Webhooks (internal, from ЮKassa)
POST   /billing/webhook           → 200 OK

# Admin (protected)
GET    /billing/admin/users       → [{user, plan, usage}]
PATCH  /billing/admin/users/:id   → override plan/limits
```

### 4.5 DRF Serializers

```python
# billing/serializers.py
from rest_framework import serializers

class PlanSerializer(serializers.Serializer):
    name = serializers.CharField()
    price_rub = serializers.IntegerField()
    tokens_monthly = serializers.IntegerField()
    max_agents = serializers.IntegerField()
    features = serializers.ListField(child=serializers.CharField())

class SubscriptionSerializer(serializers.ModelSerializer):
    tokens_remaining = serializers.ReadOnlyField()
    class Meta:
        model = Subscription
        fields = ["id", "plan", "status", "tokens_used",
                  "tokens_limit", "tokens_remaining", "expires_at"]

class UsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = UsageLog
        fields = ["tokens_input", "tokens_output", "model_used",
                  "cost_kopeks", "timestamp"]

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    telegram_id = serializers.IntegerField(required=False)

    def validate(self, data):
        if not data.get("email") and not data.get("telegram_id"):
            raise serializers.ValidationError(
                "Either email or telegram_id is required"
            )
        return data
```

### 4.6 Error Handling

| Code | Error | Description |
|------|-------|-------------|
| 401 | `invalid_api_key` | API ключ не найден или отозван |
| 402 | `payment_required` | Требуется оплата для этого действия |
| 403 | `plan_limit` | Фича недоступна на текущем плане |
| 429 | `tokens_exhausted` | Лимит токенов исчерпан; включает `retry_after` и `upgrade_url` |
| 409 | `idempotency_conflict` | Запрос с таким idempotency_key уже обработан |
| 502 | `payment_gateway_error` | ЮKassa недоступна; grace period активен |

---

## 5. Implementation Plan

### Phase 1: Data Layer (P0)
- [ ] Django project: `django-admin startproject safeclaw`
- [ ] Django app: `python manage.py startapp billing`
- [ ] Models (User, Subscription, BillingEvent, UsageLog)
- [ ] Django Admin configuration
- [ ] `python manage.py makemigrations && migrate`
- [ ] Unit tests для моделей

### Phase 2: ЮKassa Integration (P0)
- [ ] ЮKassa SDK wrapper (`yokassa.py`)
- [ ] Create payment flow
- [ ] Webhook handler (idempotent, signature verification)
- [ ] Рекуррентные платежи (saved payment method)
- [ ] Sandbox тесты

### Phase 3: Subscription Lifecycle (P0)
- [ ] State machine implementation (`lifecycle.py`)
- [ ] Transition validation (invalid transitions → error)
- [ ] Grace period (3 дня PAST_DUE → SUSPENDED)
- [ ] Auto-cancellation (30 дней SUSPENDED → CANCELLED)
- [ ] Scheduled tasks (cron/APScheduler)
- [ ] Unit tests для каждого перехода

### Phase 4: Token Metering (P0)
- [ ] Django middleware (`metering.py`)
- [ ] Atomic token counter (F() expressions + SELECT FOR UPDATE)
- [ ] Rate limiter (HTTP 429)
- [ ] Monthly reset (django-celery-beat / management command)
- [ ] Load tests (1000 concurrent)

### Phase 5: REST API (P0)
- [ ] DRF ViewSets + Serializers (`views.py`, `serializers.py`)
- [ ] DRF Authentication backend (API key → user lookup)
- [ ] Registration flow
- [ ] URL routing (`urls.py`)
- [ ] Usage dashboard endpoint
- [ ] Integration tests

### Phase 6: Production Hardening (P1)
- [ ] Refund flow
- [ ] Upgrade/downgrade with proration
- [ ] Email notifications (80%, 100% limit) via `django.core.mail`
- [ ] Django Admin actions (suspend, activate, refund)
- [ ] Monitoring (django-prometheus)
- [ ] Backup automation (pg_dump cron)
- [ ] `settings/production.py` (security hardening)

---

## 6. Test Plan

### 6.1 Unit Tests (~40 тестов)

**Models (8 тестов):**
- `test_create_user_with_email`
- `test_create_user_with_telegram`
- `test_api_key_hash_unique`
- `test_subscription_default_free`
- `test_billing_event_immutable`
- `test_usage_log_timestamps`
- `test_plan_config_frozen`
- `test_plan_tokens_limits`

**Lifecycle (12 тестов):**
- `test_transition_free_to_active`
- `test_transition_active_to_past_due`
- `test_transition_past_due_to_active`
- `test_transition_past_due_to_suspended`
- `test_transition_suspended_to_active`
- `test_transition_suspended_to_cancelled`
- `test_transition_active_to_cancelled`
- `test_invalid_transition_free_to_suspended`
- `test_invalid_transition_cancelled_to_active`
- `test_grace_period_3_days`
- `test_auto_cancel_30_days`
- `test_upgrade_pro_to_team`

**Metering (10 тестов):**
- `test_token_count_increments`
- `test_token_limit_enforced`
- `test_rate_limit_429_response`
- `test_unlimited_plan_no_limit`
- `test_monthly_reset`
- `test_concurrent_metering_atomic`
- `test_usage_log_created`
- `test_cost_calculation`
- `test_overage_billing`
- `test_metering_latency_under_5ms`

**ЮKassa (10 тестов):**
- `test_create_payment`
- `test_webhook_payment_succeeded`
- `test_webhook_idempotency`
- `test_webhook_invalid_signature_rejected`
- `test_webhook_payment_failed`
- `test_recurring_payment_creation`
- `test_refund_creation`
- `test_refund_partial`
- `test_payment_gateway_timeout_handling`
- `test_sandbox_mode`

### 6.2 Integration Tests (~10 тестов)

- `test_register_subscribe_use_flow`
- `test_payment_webhook_activates_subscription`
- `test_token_limit_blocks_request`
- `test_upgrade_changes_limits`
- `test_failed_payment_suspends_after_grace`
- `test_api_key_rotation`
- `test_concurrent_users_isolation`
- `test_admin_override`
- `test_full_lifecycle_free_active_cancel`
- `test_recovery_after_db_restart`

### 6.3 Load Tests

- 1000 concurrent users, 100 req/sec → metering latency < 5ms p99
- ЮKassa webhook storm (100 webhooks/sec) → no duplicates

---

## 7. Risks & Mitigations

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| ЮKassa API downtime | Платежи не проходят | Low (99.9% SLA) | Grace period + retry queue |
| Double charging | Финансовые потери, репутация | Medium | Idempotency keys на каждый запрос |
| Token metering race condition | Пользователь «ворует» токены | Medium | SELECT FOR UPDATE (row-level lock) |
| API key leak | Несанкционированный доступ | Medium | SHA-256 storage, key rotation endpoint |
| PostgreSQL data loss | Потеря финансовых данных | Low | WAL + daily pg_dump + replication |
| ЮKassa изменит API | Интеграция ломается | Low | SDK version pinning + alerting |
| ФЗ-54 нарушение (чеки) | Штраф до 100% выручки | Medium | ЮKassa автоматические чеки |

---

## 8. Acceptance Criteria

- [ ] **AC-01:** Пользователь может зарегистрироваться и получить API-ключ за < 3 секунды
- [ ] **AC-02:** Оплата Pro-плана через ЮKassa завершается успешно (sandbox)
- [ ] **AC-03:** После оплаты, webhook активирует подписку < 5 секунд
- [ ] **AC-04:** Token metering корректно блокирует при превышении лимита (429)
- [ ] **AC-05:** Рекуррентный платёж создаётся автоматически через 30 дней
- [ ] **AC-06:** Повторный webhook НЕ создаёт дубликат платежа
- [ ] **AC-07:** Все финансовые операции имеют запись в billing_events
- [ ] **AC-08:** API ключ хранится как SHA-256 хэш, оригинал не восстановим
- [ ] **AC-09:** 40+ unit тестов проходят
- [ ] **AC-10:** Load test: 1000 concurrent users, metering p99 < 5ms

---

## 9. Dependencies

| Dependency | Version | Purpose |
|-----------|---------|---------|
| `django` | >=5.1 | Web framework (ORM, Admin, Auth, Migrations) |
| `djangorestframework` | >=3.15 | REST API (ViewSets, Serializers, Auth) |
| `yookassa` | >=3.0.0 | ЮKassa Python SDK |
| `psycopg[binary]` | >=3.1 | PostgreSQL driver (Django native) |
| `django-celery-beat` | >=2.6 | Scheduled tasks (grace period, token reset) |
| `celery[redis]` | >=5.3 | Task queue |
| `gunicorn` | >=22.0 | WSGI production server |
| `django-cors-headers` | >=4.3 | CORS |
| `pytest` | >=8.0 | Testing |
| `pytest-django` | >=4.8 | Django test integration |
| `factory-boy` | >=3.3 | Test fixtures |
