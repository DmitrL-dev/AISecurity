# Dashboard V3 — Production Architecture

> **Цель:** Переход от MVP к production-ready с фокусом на:
> - 🔧 Современность решений
> - 🔒 Безопасность
> - 📈 Масштабируемость

---

## 1. Authentication & Authorization ✅ DECIDED

### Решение: **Keycloak** (self-hosted)

| Критерий | Keycloak |
|----------|----------|
| Self-hosted | ✅ Полный контроль над данными |
| SSO/SAML | ✅ Enterprise интеграция |
| MFA/2FA | ✅ TOTP (Google Authenticator) |
| LDAP/AD | ✅ Native |
| Стоимость | Free (open-source) |
| Compliance | ✅ SOC2, ISO27001 ready |

### RBAC — Роли

| Роль | Права |
|------|-------|
| **admin** | Полный доступ: users, engines, settings |
| **analyst** | Analyze, audit read, engine view |
| **viewer** | Read-only: dashboard, metrics |
| **api-only** | API access только (для интеграций) |

**Кастомные роли:** Granular permission assignment per object (в плане развития).

### 2FA

**TOTP** (Time-based One-Time Password):
- Google Authenticator / Authy / 1Password
- 6-digit codes, 30s rotation
- Backup codes for recovery

---

## 2. Database Layer ✅ DECIDED

### Решение

| Слой | Технология | Назначение |
|------|------------|------------|
| **OLTP** | PostgreSQL | users, settings, policies, tenants |
| **Analytics** | ClickHouse | audit logs, metrics, threat analytics |
| **Cache** | Redis Cluster | sessions, real-time state, pub/sub |

### ⚠️ Analytics Abstraction Layer

> **Требование:** Возможность замены ClickHouse на аналог или своё решение

```python
# src/brain/analytics/interface.py
from abc import ABC, abstractmethod

class AnalyticsBackend(ABC):
    """Abstract interface for analytics backends."""
    
    @abstractmethod
    async def insert_events(self, events: List[AuditEvent]) -> None:
        """Bulk insert events."""
        pass
    
    @abstractmethod
    async def query_metrics(self, query: MetricQuery) -> MetricResult:
        """Query aggregated metrics."""
        pass
    
    @abstractmethod
    async def search_logs(self, filters: LogFilter) -> List[AuditLog]:
        """Search audit logs."""
        pass

# Implementations:
# - ClickHouseBackend (current)
# - TimescaleBackend (fallback)
# - CustomSentinelAnalytics (future)
```

**Конфигурация:**
```yaml
analytics:
  backend: clickhouse  # or: timescale, sentinel-analytics
  clickhouse:
    host: clickhouse.sentinel.local
    database: sentinel_analytics
  fallback:
    backend: timescale
```

**Vendor-independence:**
- Interface-based design
- Config-driven backend selection
- Migration tools между backends

---

## 3. Swarm Architecture (Рой) ✅ DECIDED

> **Решение:** NATS JetStream + безмастерный кластер BRAIN-ов

### Текущее состояние
- Single BRAIN instance
- Shield имеет HA с SSRP/SHSP протоколами
- Dashboard polling каждые 5 секунд

### ✅ Уже заложено в BRAIN

**`src/brain/core/collective_immunity.py`** — Federated Learning:

```python
class CollectiveImmunity:
    """Federated learning system for collective threat defense."""
    
    def export_for_federation(self) -> Dict:
        """Export privacy-safe data for federation with other nodes."""
    
    def import_federation_data(self, data: Dict):
        """Import data from federated node."""
    
    def contribute_pattern(self, pattern: str, risk_score: float):
        """Contribute threat pattern with Differential Privacy."""
```

**Ключевые фичи:**
- ✅ `export_for_federation()` — экспорт для других нод
- ✅ `import_federation_data()` — импорт от других нод
- ✅ Differential Privacy (Laplace noise)
- ✅ Pattern hashing для конфиденциальности
- ✅ Threat intelligence sharing

**Нужно добавить:**
- Transport layer (gRPC / NATS / Redis Pub/Sub)
- Discovery (регистрация нод)
- Health / heartbeat

### Паттерны из Shield HA (Module 8)

| Паттерн | Описание | Применимость для BRAIN |
|---------|----------|------------------------|
| **Active-Active** | Все ноды обрабатывают трафик | ✅ Идеально — нет мастера |
| **N+1** | N активных + 1 spare | ✅ Для auto-scaling |
| **SSRP** | State Sync Replication Protocol | ✅ Синхронизация конфигов |
| **Quorum** | Большинство для решений | ✅ Split-brain prevention |
| **Fencing** | Изоляция сбойной ноды | ✅ Для safety |

### Предлагаемая архитектура BRAIN Swarm

```
┌─────────────────────────────────────────────────────────────────────┐
│                         BRAIN SWARM                                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │                   COORDINATION LAYER                         │    │
│  │                                                              │    │
│  │   ┌──────────────┐   ┌──────────────┐   ┌──────────────┐   │    │
│  │   │ etcd/Consul  │   │ Redis Cluster│   │  NATS/Kafka  │   │    │
│  │   │ (Discovery)  │   │ (State/Cache)│   │  (Events)    │   │    │
│  │   └──────────────┘   └──────────────┘   └──────────────┘   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                              │                                       │
│         ┌────────────────────┼────────────────────┐                 │
│         │                    │                    │                 │
│     ┌───▼───┐            ┌───▼───┐            ┌───▼───┐            │
│     │BRAIN-1│◄──────────►│BRAIN-2│◄──────────►│BRAIN-N│            │
│     │       │  Gossip    │       │  Gossip    │       │            │
│     │       │  Protocol  │       │  Protocol  │       │            │
│     └───┬───┘            └───┬───┘            └───┬───┘            │
│         │                    │                    │                 │
│         └────────────────────┴────────────────────┘                 │
│                              │                                       │
│                    ┌─────────▼─────────┐                            │
│                    │   Local Redis     │                            │
│                    │  (Per-node cache) │                            │
│                    └───────────────────┘                            │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                          DASHBOARD                                   │
│  • WebSocket connections to ALL BRAIN nodes                          │
│  • Aggregated view of swarm                                          │
│  • Real-time events from each node                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Компоненты

| Компонент | Решение | Назначение |
|-----------|---------|------------|
| **Discovery** | etcd / Consul / K8s DNS | Регистрация и обнаружение нод |
| **State Sync** | Redis Cluster | Конфиги, engine states, blocklists |
| **Events** | NATS JetStream | Real-time события между нодами |
| **Load Balancing** | HAProxy / Envoy | Распределение трафика |

### Протоколы

1. **BRAIN Gossip Protocol (BGP)** — peer discovery, health checks
2. **BRAIN State Sync (BSS)** — config/blocklist replication
3. **BRAIN Event Stream (BES)** — threat events broadcast

### Безмастерная топология

```
Вместо:            Нужно:
   ┌───────┐          ┌───────┐   ┌───────┐   ┌───────┐
   │MASTER │          │BRAIN-1│◄─►│BRAIN-2│◄─►│BRAIN-3│
   └───┬───┘          └───────┘   └───────┘   └───────┘
       │                    │          │          │
   ┌───▼───┐                └──────────┴──────────┘
   │WORKER │                    Mesh Topology
   └───────┘                    (No master)
```

**Преимущества:**
- Нет single point of failure
- Любая нода может принять любой запрос
- Горизонтальное масштабирование

### Dashboard Integration

```
Dashboard                        Swarm
   │                              │
   ├──WebSocket─────────────────►│ BRAIN-1 (events)
   ├──WebSocket─────────────────►│ BRAIN-2 (events)
   ├──WebSocket─────────────────►│ BRAIN-N (events)
   │                              │
   ├──HTTP GET /swarm/status────►│ Any BRAIN (aggregated)
   │                              │
   └──HTTP POST /analyze────────►│ Load Balancer → Any BRAIN
```

### Варианты реализации

| Вариант | Сложность | Рекомендация |
|---------|-----------|--------------|
| **Kubernetes Native** | Средняя | ✅ Если уже K8s |
| **HashiCorp Stack** | Высокая | Enterprise |
| **Redis + NATS** | Низкая | ✅ Quick start |
| **Custom Gossip** | Очень высокая | Не рекомендуется |

### Рекомендация: Redis Cluster + NATS

```yaml
# docker-compose.swarm.yml
services:
  brain-1:
    image: sentinel/brain
    environment:
      - SWARM_MODE=true
      - SWARM_REDIS_URL=redis://redis:6379
      - SWARM_NATS_URL=nats://nats:4222
      - BRAIN_NODE_ID=brain-1

  brain-2:
    image: sentinel/brain
    environment:
      - SWARM_MODE=true
      - SWARM_REDIS_URL=redis://redis:6379
      - SWARM_NATS_URL=nats://nats:4222
      - BRAIN_NODE_ID=brain-2

  redis:
    image: redis:7-alpine

  nats:
    image: nats:2.10-alpine
    command: --js  # Enable JetStream
```

### Geo-Distribution (Multi-Region)

```
┌─────────────────────┐    WAN Link    ┌─────────────────────┐
│   REGION: EU-WEST   │    (50-100ms)  │  REGION: US-EAST    │
│                     │◄──────────────►│                     │
│  ┌───────────────┐  │                │  ┌───────────────┐  │
│  │ NATS Gateway  │  │                │  │ NATS Gateway  │  │
│  └───────┬───────┘  │                │  └───────┬───────┘  │
│          │          │                │          │          │
│  BRAIN-EU-1/2/3     │                │  BRAIN-US-1/2/3     │
│  (Local cluster)    │                │  (Local cluster)    │
└─────────────────────┘                └─────────────────────┘
```

**NATS Features:**
- **Leaf Nodes** — локальные кластеры с WAN bridge
- **Super Cluster** — объединение через gateway
- **Interest-based routing** — сообщения только к подписчикам
- **JetStream replication** — store-and-forward между регионами

**Subject Routing:**
```
brain.eu.*.events     → Только EU
brain.us.*.events     → Только US
brain.global.events   → Все регионы (federation)
brain.analyze.local   → Lowest latency BRAIN
```

**Data Sovereignty:**
- Threat patterns (hashed) → глобально
- PII → остаётся локально
- GDPR/CCPA compliant

### SOC/SIEM Friendly Traffic

| Фактор | NATS Поведение |
|--------|----------------|
| **Порты** | Фиксированные: 4222, 6222, 7222 |
| **Протокол** | TCP/TLS — не UDP flood |
| **Pattern** | Persistent connections |
| **mTLS** | Certificate-based, не anonymous |

**Whitelist для Firewall:**
```
ALLOW TCP 4222  # NATS client
ALLOW TCP 6222  # NATS cluster  
ALLOW TCP 7222  # NATS gateway
```

**SIEM Integration:**
```
NATS → Prometheus → SIEM
  - nats_connections_total
  - nats_messages_sent
  - nats_bytes_received
→ Baseline visibility
→ Anomaly detection
```

---
## 4. Multi-tenant / Multi-user

### Модели

| Модель | Описание | Изоляция | Стоимость |
|--------|----------|----------|-----------|
| **Single-tenant** | Отдельный instance на клиента | ★★★★★ | $$$$ |
| **Multi-tenant shared DB** | Одна БД, tenant_id | ★★★ | $ |
| **Multi-tenant schema** | Отдельная schema на tenant | ★★★★ | $$ |
| **Hybrid** | Shared + dedicated для enterprise | ★★★★ | $$ |

### Для SENTINEL

Учитывая security-focused продукт:
- **Enterprise:** Single-tenant или schema isolation
- **Community/SMB:** Shared DB с RLS (Row-Level Security)

### Обсуждение
- Какой deployment model? (SaaS, self-hosted, hybrid?)
- Compliance requirements? (SOC2, ISO27001, GDPR?)

---

## 5. Deployment & Infrastructure

### Варианты

| Платформа | Pros | Cons | Рекомендация |
|-----------|------|------|--------------|
| **Vercel** | Zero-config Next.js | Vendor lock, limits | Dev/staging |
| **Docker Compose** | Simple, portable | Not scalable | Self-hosted SMB |
| **Kubernetes** | Production-grade | Complexity | Enterprise |
| **Fly.io** | Edge deployment, простота | Размер | Mid-scale |

### Recommended Stack

```yaml
Production:
  Frontend: Vercel / Cloudflare Pages
  Backend: 
    - BRAIN: Kubernetes (GPU nodes)
    - API: Kubernetes / Cloud Run
  Database: 
    - Managed PostgreSQL (Cloud SQL / RDS)
    - Redis Cluster (Elasticache / Upstash)
  Observability:
    - Prometheus + Grafana
    - OpenTelemetry
```

---

## 6. Security Hardening

### Checklist

| Область | MVP | Production |
|---------|-----|------------|
| HTTPS | ✅ | ✅ + HSTS, cert pinning |
| Auth | localStorage token | HttpOnly cookies, refresh rotation |
| CSRF | ❌ | ✅ SameSite + tokens |
| CSP | ❌ | ✅ Strict policy |
| Rate limiting | ❌ | ✅ Per-user, per-IP |
| Input validation | Basic | Zod schemas everywhere |
| Audit logging | ✅ | ✅ + tamper-proof (blockchain/merkle) |
| Secrets | env vars | Vault / Secret Manager |

---

## 7. Резюме — Roadmap V3

### ✅ Все решения

| Область | Решение |
|---------|---------|
| **Auth** | Keycloak (self-hosted) |
| **2FA** | TOTP |
| **RBAC** | admin, analyst, viewer, api-only + custom |
| **Swarm Transport** | NATS JetStream |
| **Database OLTP** | PostgreSQL |
| **Database Analytics** | ClickHouse + Abstraction Layer |
| **Cache** | Redis Cluster |
| **Deployment** | Enterprise now, SaaS-ready |
| **Multi-tenant** | Tenant-aware schema now, full isolation later |
| **Geo-distribution** | NATS SuperCluster |

---

## 8. Compliance & Certification Readiness

> **Требование:** Готовность к сертификации как ИБ-инструмент в России, Европе и США

### Регуляторные требования

| Регион | Сертификация | Требования |
|--------|--------------|------------|
| **Россия** | ФСТЭК, ФСБ, ФЗ-152 | ГОСТ Р 56939, криптография ГОСТ, локализация ПДн |
| **Европа** | CE, GDPR, NIS2 | Data residency, audit trail, DPO |
| **США** | FedRAMP, SOC2, HIPAA | FIPS 140-2, encryption at rest |

### 🔴 ФЗ-152 — Персональные данные (Россия)

> **Критическое требование для российского рынка**

**Основные требования:**

| Требование | Описание | Реализация |
|------------|----------|------------|
| **Локализация ПДн** | ПДн граждан РФ хранятся в РФ | Geo-routing + RU data center |
| **Согласие** | Явное согласие субъекта | Consent management UI |
| **Уведомление РКН** | Регистрация оператора ПДн | Процедура |
| **Защита ПДн** | Технические меры защиты | Encryption, access control |
| **Права субъекта** | Доступ, изменение, удаление | API endpoints |
| **Инцидент-менеджмент** | Уведомление 24ч | Alerting + workflow |

**Архитектурные требования:**

```yaml
# config/regions/russia.yaml
region: RU
data_residency:
  personal_data: 
    storage: ru-moscow-1  # Only Russian DC
    encryption: GOST      # GOST R 34.12-2015
  
  consent:
    required: true
    expiry_days: 365
    audit_trail: true
  
  subject_rights:
    access_request: true
    rectification: true
    erasure: true         # "Право на забвение"
    portability: true
  
  breach_notification:
    authority: РКН
    deadline_hours: 24
```

**Классы защищённости (ФСТЭК):**

| Класс | Объём ПДн | Требования |
|-------|-----------|------------|
| **К4** | <1000 субъектов | Базовый |
| **К3** | 1000-100 000 | Повышенный |
| **К2** | >100 000 или спецкат | Высокий |
| **К1** | Биометрия, здоровье | Максимальный |

**Для SENTINEL:** минимум **К3** (enterprise клиенты = много пользователей)

### Архитектурные implications

**Криптография:**
```python
# Abstraction for crypto providers
class CryptoProvider(ABC):
    @abstractmethod
    def encrypt(self, data: bytes) -> bytes: pass
    
    @abstractmethod  
    def sign(self, data: bytes) -> bytes: pass

# Implementations:
# - OpenSSLProvider (default, AES-256, RSA)
# - GOSTProvider (Russia, ГОСТ 28147-89)
# - FIPSProvider (USA, FIPS 140-2 validated)
```

**Audit Trail:**
- Immutable logs (append-only)
- Tamper-proof (Merkle tree / blockchain)
- Long retention (7+ years)
- Exportable for auditors

**Data Residency:**
- Region-locked storage (EU data stays in EU)
- Configurable per tenant
- NATS subject routing by region

**Access Control:**
- Full audit of admin actions
- Separation of duties
- Key management (HSM-ready)

### Compliance Checklist

| Требование | Статус | Примечание |
|------------|--------|------------|
| Encryption at rest | 🔄 Planned | PostgreSQL TDE, ClickHouse encryption |
| Encryption in transit | ✅ | TLS 1.3, mTLS |
| Audit logging | ✅ | HMAC signatures |
| RBAC | ✅ | Keycloak |
| MFA/2FA | ✅ | TOTP |
| Key management | 🔄 Planned | Vault / HSM |
| Data residency | ✅ | NATS geo-routing |
| GOST crypto | 🔄 Planned | Abstraction layer |
| FIPS 140-2 | 🔄 Planned | Abstraction layer |

---

## 9. Implementation Phases

### Phase 6: Auth & Users
- [ ] Keycloak deployment + realm setup
- [ ] Dashboard OIDC integration
- [ ] User table, sessions
- [ ] RBAC implementation
- [ ] TOTP 2FA flow
- [ ] API keys per user

### Phase 7: Database Migration
- [ ] PostgreSQL schema design (tenant-aware)
- [ ] ClickHouse setup + abstraction layer
- [ ] Drizzle ORM setup
- [ ] Migration scripts

### Phase 8: BRAIN Swarm
- [ ] NATS JetStream cluster
- [ ] `CollectiveImmunity` transport layer
- [ ] Discovery / registration
- [ ] Health / heartbeat
- [ ] Dashboard multi-BRAIN view

### Phase 9: Multi-tenant & SaaS
- [ ] Tenant model (Keycloak realms)
- [ ] RLS policies
- [ ] Tenant isolation tests
- [ ] Usage metering

### Phase 10: Production & Compliance
- [ ] Security headers (HSTS, CSP)
- [ ] Rate limiting
- [ ] E2E tests (Playwright)
- [ ] Monitoring (Prometheus + Grafana)
- [ ] Crypto abstraction layer
- [ ] Compliance documentation

---

**Документ завершён:** 2026-01-29
