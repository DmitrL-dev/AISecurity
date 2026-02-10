# SafeClaw Provider Router — Спецификация

> **Version:** 1.0
> **Дата:** 2026-02-10
> **Статус:** Draft
> **Язык:** Русский

---

## 1. Overview

### 1.1 Purpose

Мультимодельный роутер для SafeClaw — маршрутизация запросов к LLM-провайдерам
(GigaChat, DeepSeek, YandexGPT) с интеграцией Shield (защита промптов),
RLM Toolkit (память) и billing metering (подсчёт токенов).

### 1.2 Scope

**In Scope:**
- Адаптеры провайдеров (GigaChat, DeepSeek, YandexGPT, OpenAI-compatible)
- Стратегии роутинга (cost-optimized, quality-first, latency-first, failover)
- Интеграция с billing metering middleware (X-Tokens-Input/Output headers)
- Streaming API (SSE) для real-time ответов
- Retry/failover при недоступности провайдера
- Health check для каждого провайдера
- BYOK (Bring Your Own Key) — пользователь может указать свой API-ключ

**Out of Scope:**
- Shield middleware (уже есть)
- RLM memory (отдельный модуль)
- Frontend/UI
- Fine-tuning моделей

### 1.3 References

- SafeClaw Business Plan v2.0 — §Тарифные планы
- SafeClaw Detailed Plan v2.0, ЧАСТЬ VII — Недели 1-2
- billing_spec.md — Token metering (FR-07, FR-08)
- [GigaChat API](https://developers.sber.ru/docs/ru/gigachat/api/overview)
- [DeepSeek API](https://platform.deepseek.com/api-docs)
- [YandexGPT API](https://yandex.cloud/docs/foundation-models/quickstart)

---

## 2. Requirements

### 2.1 Functional Requirements

| ID | Требование | Приоритет |
|----|-----------|-----------|
| **FR-01** | Поддержка 4+ провайдеров: GigaChat, DeepSeek, YandexGPT, OpenAI-compatible | P0 |
| **FR-02** | Unified API: единый формат запроса, независимо от провайдера | P0 |
| **FR-03** | Стратегия роутинга: выбор модели по cost/quality/latency/availability | P0 |
| **FR-04** | Failover: автопереключение на резервный провайдер при ошибке | P0 |
| **FR-05** | Streaming: SSE-ответы для real-time UX | P0 |
| **FR-06** | Token counting: точный подсчёт input/output токенов, передача в headers | P0 |
| **FR-07** | Provider health check endpoint | P1 |
| **FR-08** | BYOK: пользователь может указать свой API-ключ провайдера | P1 |
| **FR-09** | Model aliases: `fast`, `smart`, `cheap` → конкретная модель | P0 |
| **FR-10** | Rate limiting per-provider (не превышать лимиты API) | P1 |
| **FR-11** | Request/response logging для аудита | P1 |
| **FR-12** | Конфигурация провайдеров через env-переменные и settings.py | P0 |

### 2.2 Non-Functional Requirements

| ID | Требование | Метрика |
|----|-----------|---------|
| **NFR-01** | Overhead роутера < 10ms | p99 < 10ms |
| **NFR-02** | Failover switch < 500ms | p99 < 500ms |
| **NFR-03** | Поддержка до 100 concurrent requests | load test |
| **NFR-04** | Zero data loss при failover | 100% |
| **NFR-05** | Retry не более 3 попыток | max 3 |

---

## 3. Design

### 3.1 Architecture

```
Client Request
    │
    ▼
┌─────────────────┐
│  POST /api/chat/ │  ← DRF View (ChatView)
└────────┬────────┘
         │
    ▼
┌─────────────────┐
│  Router Engine   │  ← Выбор провайдера по стратегии
│  (router.py)     │
└────────┬────────┘
         │
    ┌────┼────┬─────────┐
    ▼    ▼    ▼         ▼
┌──────┐┌──────┐┌──────┐┌──────────┐
│GigaC.││DeepS.││YaGPT ││OpenAI-   │
│adapt.││adapt.││adapt.││compat.   │
└──┬───┘└──┬───┘└──┬───┘└──┬───────┘
   │       │       │       │
   ▼       ▼       ▼       ▼
 External APIs (HTTPS)
```

### 3.2 Django App: `router`

```
safeclaw/
├── router/
│   ├── __init__.py
│   ├── models.py          # ProviderConfig, RequestLog  
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py        # BaseProvider ABC
│   │   ├── gigachat.py    # GigaChatProvider
│   │   ├── deepseek.py    # DeepSeekProvider
│   │   ├── yandexgpt.py   # YandexGPTProvider
│   │   └── openai_compat.py  # OpenAI-compatible
│   ├── engine.py          # RouterEngine — core logic
│   ├── strategies.py      # Routing strategies
│   ├── serializers.py     # DRF serializers
│   ├── views.py           # ChatView, HealthView
│   ├── urls.py            # /api/chat/, /api/health/
│   ├── admin.py
│   └── tests/
│       ├── __init__.py
│       ├── test_providers.py
│       ├── test_engine.py
│       ├── test_strategies.py
│       └── test_api.py
```

### 3.3 BaseProvider Interface

```python
class BaseProvider(ABC):
    name: str
    models: list[str]
    
    @abstractmethod
    async def complete(
        self, 
        messages: list[dict],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        stream: bool = False,
        **kwargs,
    ) -> CompletionResult:
        ...
    
    @abstractmethod
    async def health_check(self) -> ProviderHealth:
        ...
    
    @abstractmethod
    def count_tokens(self, text: str) -> int:
        ...
```

### 3.4 Data Models

```python
class CompletionResult:
    content: str
    model: str
    provider: str
    tokens_input: int
    tokens_output: int
    latency_ms: float
    cost_kopecks: float  # estimated cost

class ProviderHealth:
    name: str
    available: bool
    latency_ms: float
    models: list[str]
    quota_remaining: int | None

class RoutingStrategy(TextChoices):
    COST = "cost"       # cheapest first
    QUALITY = "quality" # best model first
    LATENCY = "latency" # fastest first
    FAILOVER = "failover" # primary + fallback
```

### 3.5 API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/chat/` | API key | Send chat completion request |
| POST | `/api/chat/stream/` | API key | SSE streaming completion |
| GET | `/api/providers/` | — | List available providers |
| GET | `/api/providers/health/` | API key | Health check all providers |

### 3.6 Chat Request/Response Format

**Request:**
```json
{
    "messages": [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello!"}
    ],
    "model": "smart",
    "strategy": "cost",
    "temperature": 0.7,
    "max_tokens": 4096,
    "stream": false,
    "provider_key": null
}
```

**Response:**
```json
{
    "content": "Hello! How can I help you?",
    "model": "deepseek-chat",
    "provider": "deepseek",
    "usage": {
        "input_tokens": 15,
        "output_tokens": 8,
        "total_tokens": 23,
        "cost_kopecks": 2
    },
    "latency_ms": 450
}
```

### 3.7 Model Aliases

| Alias | Primary | Fallback 1 | Fallback 2 |
|-------|---------|------------|------------|
| `fast` | DeepSeek Chat | GigaChat Lite | YandexGPT Lite |
| `smart` | DeepSeek Reasoner | GigaChat Pro | YandexGPT Pro |
| `cheap` | DeepSeek Chat | GigaChat Lite | — |

### 3.8 Provider Configuration

```python
# settings.py additions
ROUTER_PROVIDERS = {
    "gigachat": {
        "enabled": True,
        "api_key": os.environ.get("GIGACHAT_API_KEY", ""),
        "base_url": "https://gigachat.devices.sberbank.ru/api/v1",
        "models": ["GigaChat", "GigaChat-Pro", "GigaChat-Plus"],
        "rate_limit": 10,  # req/sec
        "cost_per_1k_input": 0,  # kopecks (free tier)
        "cost_per_1k_output": 0,
    },
    "deepseek": {
        "enabled": True,
        "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
        "base_url": "https://api.deepseek.com/v1",
        "models": ["deepseek-chat", "deepseek-reasoner"],
        "rate_limit": 60,
        "cost_per_1k_input": 14,   # 0.14₽
        "cost_per_1k_output": 28,  # 0.28₽
    },
    "yandexgpt": {
        "enabled": True,
        "api_key": os.environ.get("YANDEXGPT_API_KEY", ""),
        "folder_id": os.environ.get("YANDEXGPT_FOLDER_ID", ""),
        "base_url": "https://llm.api.cloud.yandex.net/foundationModels/v1",
        "models": ["yandexgpt-lite", "yandexgpt"],
        "rate_limit": 10,
        "cost_per_1k_input": 20,
        "cost_per_1k_output": 40,
    },
}
```

---

## 4. Implementation Phases

### Phase 1: Core (P0)
1. BaseProvider ABC + CompletionResult dataclass
2. DeepSeek adapter (OpenAI-compatible, самый простой)
3. Router engine + cost strategy
4. ChatView + serializers + URLs
5. Tests: 15+ unit + integration

### Phase 2: Multi-provider (P0)
6. GigaChat adapter (OAuth token + custom API)
7. YandexGPT adapter (IAM token + custom format)
8. Failover strategy
9. Model aliases
10. Tests: 10+

### Phase 3: Production (P1)
11. SSE streaming
12. BYOK support
13. Health check endpoint
14. Provider rate limiting
15. Request/response logging
16. Tests: 10+

---

## 5. Verification Plan

### Automated Tests
```bash
python -m pytest router/tests/ -v --tb=short
```

### Manual Verification
- End-to-end: POST /api/chat/ → DeepSeek response
- Failover: disable DeepSeek → auto-switch to GigaChat
- Token counting: verify X-Tokens-* headers in response
- Streaming: SSE events received correctly
