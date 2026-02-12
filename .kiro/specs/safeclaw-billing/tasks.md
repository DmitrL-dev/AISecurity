# SafeClaw Billing — Tasks

> **Компонент:** saas/safeclaw/
> **Дата:** 2026-02-12

---

## Реализованные (MVP)

### Billing App
- [x] T-1: Django project setup (safeclaw/)
- [x] T-2: Models (Tenant, Plan, Subscription, APIKey, UsageRecord)
- [x] T-3: DRF serializers + views
- [x] T-4: API key auth middleware
- [x] T-5: Plan definitions + limits
- [x] T-6: Tenant lifecycle management
- [x] T-7: Token metering
- [x] T-8: YooKassa integration + webhooks
- [x] T-9: Notification stubs
- [x] T-10: Admin panel config
- [x] T-11: Tests (api, lifecycle, metering, models, yokassa)

### Router App
- [x] T-12: LLM routing engine
- [x] T-13: Provider: GigaChat
- [x] T-14: Provider: DeepSeek
- [x] T-15: Provider: YandexGPT
- [x] T-16: Provider: OpenAI-compatible
- [x] T-17: SENTINEL Shield middleware
- [x] T-18: SSRF protection
- [x] T-19: Tests (router, shield, ssrf)

### Infra
- [x] T-20: .env.example
- [x] T-21: pytest.ini
- [x] T-22: .pre-commit-config.yaml

## Roadmap

- [ ] T-23: PostgreSQL migration (prod)
- [ ] T-24: Celery + Redis для background tasks
- [ ] T-25: Usage analytics dashboard
- [ ] T-26: Auto-upgrade/downgrade flows
- [ ] T-27: Multi-tenant isolation hardening
- [ ] T-28: Stripe integration (international)
- [ ] T-29: Docker Compose (safeclaw + postgres + redis)
- [ ] T-30: CI/CD pipeline
