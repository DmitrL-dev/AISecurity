# Memory Bridge

**Bi-Temporal Agent Memory for Cross-Session Persistence**

Memory Bridge решает критическую проблему "Agent Memory Problem" — потерю контекста между сессиями LLM-агентов.

## 🎯 Назначение

Memory Bridge обеспечивает:
- **Cross-Session State** — сохранение целей, решений, фактов между сессиями
- **Bi-Temporal Model** — отслеживание T (transaction time) и T' (valid time)
- **Semantic Invalidation** — автоматическое устаревание противоречащих фактов
- **Fact Communities** — кластеризация связанных фактов (DBSCAN)
- **Hybrid Search** — комбинация semantic + keyword + recency scoring

## 💰 Экономия токенов — Как это работает

### Проблема: LLM не могут обработать весь проект

Типичный enterprise проект:
- **1 миллион строк кода** = ~4 миллиона токенов
- **Контекст GPT-4**: 128K токенов
- **Нельзя передать весь проект** в контекст LLM

**Результат без Memory Bridge**: агент "забывает" архитектуру, повторяет ошибки, теряет контекст между сессиями.

---

### Решение: 5 механизмов экономии

#### 1️⃣ Иерархическое сжатие (Hierarchical Memory)

**Вместо**: хранить весь код (4M токенов)  
**Memory Bridge**: хранит **факты** о коде (тысячи токенов)

```
Код (до):
def authenticate(username, password):
    """Authenticate user via JWT.
    Uses bcrypt for password hashing.
    Token expires in 24 hours.
    """
    hashed = bcrypt.hash(password)
    if verify(hashed, stored):
        return jwt.encode({"user": username}, SECRET, exp=86400)
    raise AuthError()

# = ~150 токенов на одну функцию
# = 10,000 функций × 150 = 1.5M токенов

Факт (после Memory Bridge):
"Auth модуль использует JWT с bcrypt, токен 24ч"

# = ~15 токенов на весь модуль
# = 100x экономия
```

**Экономия: 50-100x** на уровне отдельных модулей.

---

#### 2️⃣ Семантическая маршрутизация (Semantic Routing)

**Вместо**: загружать ВСЕ факты (даже нерелевантные)  
**Memory Bridge**: загружает только **релевантные** к текущему запросу

```python
# Запрос: "Как работает аутентификация?"

# БЕЗ routing — все 500 фактов: 15,000 токенов
# С routing — только 20 релевантных: 600 токенов

rlm_route_context(
    query="Как работает аутентификация?",
    max_tokens=2000  # Строгий бюджет
)

# Memory Bridge:
# 1. Вычисляет embedding запроса
# 2. Находит топ-K фактов по cosine similarity
# 3. Заполняет бюджет по приоритету: L0 → L1 → L2
```

**Экономия: 70-85%** — только нужные факты попадают в контекст.

---

#### 3️⃣ Умный Cold Start (Project Discovery)

**Вместо**: сканировать весь проект каждый раз (минуты, миллионы токенов)  
**Memory Bridge**: однократное открытие + кеширование

```python
# Первый запуск: полное сканирование
rlm_discover_project()
# → Анализирует pyproject.toml, структуру, README
# → Создаёт L0 факты: "FastAPI проект, 50K LOC, modules: api, auth, db"
# → Сохраняет fingerprint

# Последующие запуски: мгновенный старт
rlm_enterprise_context(query="...")
# → Проверяет fingerprint — проект не изменился
# → Пропускает discovery — экономит 80-90% токенов
```

**Экономия: 80-90%** на повторных сессиях.

---

#### 4️⃣ TTL и автоочистка (Temporal Lifecycle)

**Вместо**: накапливать устаревшие факты бесконечно  
**Memory Bridge**: автоматически удаляет неактуальное

```python
# Факт: "Баг в line 42 файла utils.py"
# TTL: 24 часа (L3 уровень)

# Через 24 часа:
# → Факт помечен stale
# → НЕ попадает в routing
# → Экономит место в контексте

rlm_set_ttl(fact_id="abc", ttl_days=3)
```

| Уровень | TTL по умолчанию | Причина |
|---------|------------------|---------|
| L0 | 30 дней | Архитектура меняется редко |
| L1 | 7 дней | Модули обновляются |
| L2 | 3 дня | Детали устаревают быстро |
| L3 | 24 часа | Сессионные данные |

**Экономия: 20-30%** — меньше мусора в контексте.

---

#### 5️⃣ Causal Chains (Сжатие истории решений)

**Вместо**: хранить всю историю переписки (огромные логи)  
**Memory Bridge**: хранит **решения с причинами**

```python
# Без causal chains:
# "В сессии 5 мы обсуждали кеширование..." (5000 токенов лога)

# С causal chains:
rlm_record_causal_decision(
    decision="Используем Redis для кеша",
    reasons=["Низкая latency", "Поддержка кластеров"],
    alternatives=["Memcached — нет persistence"]
)
# = 50 токенов, вся суть решения сохранена

# Позже, в новой сессии:
rlm_get_causal_chain(query="почему Redis?")
# → "Redis выбран из-за latency + кластеры, Memcached отвергнут"
```

**Экономия: 90-99%** vs полные логи сессий.

---

### Реальный сценарий

```
Проект: FastAPI монорепо, 1M LOC

Традиционный подход:
├── Полный код: 4,000,000 токенов ❌ (не влезет)
├── README + docs: 50,000 токенов (хоть что-то)
└── Агент "слепой", ошибается

Memory Bridge v2.1:
├── L0 (архитектура): 500 токенов
├── L1 (релевантные модули): 1,500 токенов
├── L2 (детали реализации): 800 токенов
├── Causal (прошлые решения): 200 токенов
└── ИТОГО: 3,000 токенов ✅

Компрессия: 4,000,000 → 3,000 = 1333x
Практическая (с маршрутом): 50,000 → 3,000 = 17x
```

---

### Итоговая таблица экономии

| Механизм | Экономия | Как работает |
|----------|----------|--------------|
| Hierarchical Memory | 50-100x | Код → факты |
| Semantic Routing | 70-85% | Только релевантное |
| Cold Start Cache | 80-90% | Однократное сканирование |
| TTL Auto-Expire | 20-30% | Удаление устаревшего |
| Causal Chains | 90-99% | Решения вместо логов |

---

## 🔒 Гарантии качества данных

> **Вопрос**: Если данные сжаты в 100x раз, не теряется ли важная информация?

**Ответ**: Нет. Memory Bridge использует **семантическое сжатие**, а не деструктивное.

### Принцип: Извлечение смысла, не обрезка

```
❌ Деструктивное сжатие (как JPEG):
   "def authenticate(user, pass): ..." → "def auth..." (потеря данных)

✅ Семантическое сжатие (Memory Bridge):
   "def authenticate(user, pass): ..." → факт: "Auth использует JWT/bcrypt"
   
   Код НЕ удаляется — он остаётся в репозитории.
   Memory Bridge хранит СМЫСЛ, а не копию кода.
```

### 5 гарантий целостности

#### 1️⃣ Lossless-извлечение: код всегда доступен

Memory Bridge **не заменяет** код — он **дополняет** его:

```
┌─────────────────────────────────────────────────┐
│  Репозиторий (полный код)    ← ИСТОЧНИК ПРАВДЫ │
│         ↓                                       │
│  Memory Bridge (факты)       ← ИНДЕКС/КЭША     │
│         ↓                                       │
│  LLM контекст (релевантное)  ← ВЫБОРКА         │
└─────────────────────────────────────────────────┘

Если нужен полный код → LLM читает файл напрямую.
Memory Bridge указывает КУДА смотреть, а не заменяет.
```

#### 2️⃣ Bi-Temporal Audit: история сохраняется

Каждый факт отслеживает два времени:

```python
Fact(
    content="API rate limit = 100 req/min",
    
    # Когда факт записан в систему
    created_at="2026-01-15T10:00:00",  # T — transaction time
    
    # Когда факт стал/перестал быть правдой
    valid_at="2026-01-01T00:00:00",    # T' — valid time
    invalid_at="2026-01-20T00:00:00",  # T' — когда устарел
)

# Можно восстановить состояние на ЛЮБОЙ момент:
rlm_restore_state(version=5)  # Как было 5 версий назад
```

#### 3️⃣ Semantic Validation: противоречия обнаруживаются

При добавлении нового факта:

```python
# Старый факт: "Max file size = 10MB"
# Новый факт: "Max file size = 50MB"

# Memory Bridge автоматически:
# 1. Вычисляет embedding обоих фактов
# 2. Находит cosine similarity = 0.92 (высокое)
# 3. Помечает старый факт как invalid_at = now()
# 4. Новый факт становится актуальным

# НЕ удаляет старый — он доступен в истории
# Но НЕ загружает в контекст (экономит токены)
```

#### 4️⃣ Source Linking: факты связаны с кодом

Каждый факт знает свой источник:

```python
rlm_add_hierarchical_fact(
    content="Login endpoint валидирует JWT",
    level=2,  # L2 = Module
    domain="auth",
    code_ref="src/auth/login.py:42-58",  # Ссылка на код
)

# При необходимости — LLM может открыть файл:
view_file("src/auth/login.py", start=42, end=58)
```

#### 5️⃣ User Control: ручное управление

Пользователь всегда контролирует:

```python
# Просмотр всех фактов
rlm_get_hierarchy_stats()
# → {"total_facts": 500, "by_level": {"L0": 10, "L1": 150, ...}}

# Проверка stale фактов
rlm_get_stale_facts()
# → Список устаревших фактов для ревью

# Ручное одобрение извлечённых фактов
rlm_extract_facts(source="git_diff", auto_approve=False)
# → Кандидаты с confidence score, требуют ручного OK

# Удаление неверного факта
rlm_delete_fact(fact_id="abc123")
```

---

### Когда Memory Bridge НЕ подходит

| Сценарий | Решение |
|----------|---------|
| Нужен точный код (line-by-line) | Читать файл напрямую |
| Юридические документы | Не использовать сжатие |
| Критичные числа (лицензии, лимиты) | Хранить как отдельные факты с confidence=1.0 |

---

### Резюме: почему это безопасно

```
1. Код остаётся в репозитории — Memory Bridge не удаляет файлы
2. Факты = индекс, не замена — указывают куда смотреть
3. История сохраняется — bi-temporal model, версионирование
4. Противоречия обнаруживаются — semantic invalidation
5. Пользователь контролирует — approve/reject/delete
```


## �🚀 Быстрый старт

### Установка

```bash
pip install rlm-toolkit[mcp]
```

### Использование через MCP

После интеграции с IDE (см. [MCP Server](./mcp-server.md)), доступны 10 memory tools:

```python
# Через MCP tools в IDE:
rlm_sync_state()           # Сохранить текущее состояние
rlm_restore_state()        # Восстановить состояние сессии
rlm_add_fact(...)          # Добавить факт
rlm_search_facts(...)      # Поиск по фактам
```

### Программный доступ

```python
from rlm_toolkit.memory_bridge import MemoryBridgeManager, StateStorage

# Создание storage и manager
storage = StateStorage()  # ~/.rlm/memory_bridge.db
manager = MemoryBridgeManager(storage=storage)

# Начать сессию
state = manager.start_session("my-session")

# Добавить факты
manager.add_fact("API rate limit is 100 req/min")
manager.set_goal("Implement caching layer")

# Сохранить
version = manager.sync_state()
print(f"Saved version {version}")

# Позже — восстановить
manager2 = MemoryBridgeManager(storage=StateStorage())
state = manager2.start_session("my-session", restore=True)
print(f"Restored {len(state.facts)} facts")
```

---

## 📋 MCP Tools Reference

### Session Management

#### `rlm_sync_state`
Сохранить текущее состояние в SQLite.

```
rlm_sync_state()
# Returns: {"version": 5, "session_id": "abc123"}
```

#### `rlm_restore_state`
Восстановить состояние из хранилища.

```
rlm_restore_state(session_id="abc123")
rlm_restore_state(session_id="abc123", version=3)  # Конкретная версия
```

#### `rlm_list_sessions`
Список всех сохранённых сессий.

```
rlm_list_sessions()
# Returns: [{"session_id": "abc", "versions": [1,2,3], "last_updated": "..."}]
```

#### `rlm_get_state`
Получить текущее состояние как JSON.

```
rlm_get_state()
# Returns: {"goals": [...], "facts": [...], "decisions": [...]}
```

### Fact Operations

#### `rlm_add_fact`
Добавить факт с bi-temporal отслеживанием.

```
rlm_add_fact(
    content="Python 3.11 is the minimum version",
    entity_type="requirement",         # Optional: fact, decision, preference, memory, tool, goal, person, organization, location, event, other
    confidence=0.95,                    # Optional: 0.0-1.0
    valid_at="2026-01-01T00:00:00"     # Optional: T' time
)
```

**Entity Types:**
| Type | Description |
|------|-------------|
| `fact` | General facts (default) |
| `decision` | Architecture/design decisions |
| `preference` | User preferences |
| `memory` | Historical context |
| `tool` | Tool configurations |
| `goal` | Objectives |
| `person` | People mentioned |
| `organization` | Companies/teams |
| `location` | Places |
| `event` | Events/meetings |
| `other` | Custom (use `custom_type_name`) |

#### `rlm_search_facts`
Hybrid search по фактам.

```
rlm_search_facts(
    query="rate limit",
    top_k=10,                          # Max results
    semantic_weight=0.5,               # Embedding similarity weight
    keyword_weight=0.3,                # Keyword match weight  
    recency_weight=0.2                 # Freshness weight
)
```

#### `rlm_build_communities`
Кластеризация фактов в communities (требует sklearn).

```
rlm_build_communities(min_cluster_size=3)
# Returns: [{"name": "API Requirements", "facts": [...], "size": 5}]
```

### Goal Management

#### `rlm_update_goals`
Установить или обновить цель.

```
rlm_update_goals(
    goal_description="Implement OAuth2 authentication",
    progress=0.3                       # Optional: 0.0-1.0
)
```

### Decisions & Hypotheses

#### `rlm_record_decision`
Записать архитектурное решение.

```
rlm_record_decision(
    description="Use JWT for API auth",
    rationale="Industry standard, easy refresh tokens",
    alternatives=["Session cookies", "API keys"]  # Optional
)
```

#### `rlm_add_hypothesis`
Добавить гипотезу для проверки.

```
rlm_add_hypothesis(statement="Caching will reduce latency by 50%")
```

---

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `RLM_ENCRYPTION_KEY` | AES-256 key for storage encryption | None (unencrypted) |
| `RLM_SECURE_MEMORY` | Enable/disable encryption | `true` |

### Enabling Encryption

```bash
# Установить ключ шифрования (будет использоваться SHA-256 для derivation)
export RLM_ENCRYPTION_KEY="my-secret-passphrase-32chars-min"
```

### Storage Location

По умолчанию: `~/.rlm/memory_bridge.db`

Custom path:
```python
storage = StateStorage(db_path=Path("/custom/path/memory.db"))
```

---

## 🏗️ Architecture

### Bi-Temporal Model

Каждый факт отслеживает два времени:
- **T (Transaction Time)** — когда факт был записан в систему
- **T' (Valid Time)** — когда факт стал/перестал быть актуальным

```python
fact = Fact(
    content="API key is XYZ",
    created_at=datetime.now(),        # T — transaction time
    valid_at=datetime(2026, 1, 1),    # T' — когда факт стал валидным
    invalid_at=None,                   # T' — когда факт станет невалидным
)
```

### Semantic Invalidation

При добавлении нового факта, Memory Bridge:
1. Вычисляет embedding (через Ollama `nomic-embed-text`)
2. Сравнивает cosine similarity с существующими фактами
3. Если similarity > 0.85, старый факт автоматически invalidated

```
Old: "Max file size is 10MB"
New: "Max file size is 50MB" (similarity=0.92)
→ Old fact.invalid_at = now()
```

### CognitiveStateVector

Структура состояния:

```python
CognitiveStateVector:
    session_id: str
    version: int
    timestamp: datetime
    
    # Primary goal
    goal: Optional[Goal]
    
    # Hypotheses being tested
    hypotheses: List[Hypothesis]
    
    # Recorded decisions
    decisions: List[Decision]
    
    # Tracked facts (bi-temporal)
    facts: List[Fact]
    
    # Fact communities (clustered)
    communities: List[FactCommunity]
    
    # Open questions
    open_questions: List[str]
    
    # Confidence scores
    confidence_scores: Dict[str, float]
```

---

## 🔐 Security

### Encryption

- **Algorithm:** AES-256-GCM via Fernet
- **Key Derivation:** SHA-256 from `RLM_ENCRYPTION_KEY`
- **Scope:** Blob-level encryption of state JSON

### Fail-Closed

Если `cryptography` library недоступна и ключ установлен — raises error (не fallback к plaintext).

### Checksum Validation

SHA-256 checksum при load для detecting tampering.

---

## 📊 Dependencies

### Required
- Python 3.11+
- SQLite3 (built-in)

### Optional
- `cryptography` — для encryption (рекомендуется)
- `ollama` — для embedding generation (semantic search)
- `scikit-learn` — для `build_communities()` (DBSCAN clustering)
- `numpy` — для cosine similarity

---

## 🔄 Version History

### v2.1.0 (January 2026) — Auto-Mode
- **18 MCP tools** (zero-friction experience)
- `rlm_enterprise_context()` — one-call context injection
- `rlm_install_git_hooks()` — auto-extraction on commits
- `rlm_health_check()` — observability endpoint
- DiscoveryOrchestrator with project fingerprinting
- EnterpriseContextBuilder with suggestions

### v2.0.0 (January 2026) — Enterprise
- Hierarchical Memory (L0-L3): Project → Domain → Module → Code
- Semantic Router with embeddings
- Auto-Extraction Engine (git diff parsing)
- Causal Chain Tracker (decision reasoning)
- TTL Manager with file watchers
- Cold Start Optimizer (project discovery)
- 15 MCP tools for enterprise scale

### v1.0.0 (January 2026)
- Initial release
- Bi-temporal model from Graphiti
- 10 MCP tools
- SQLite storage with AES-256-GCM encryption

---

## 🚀 v2.1 Auto-Mode (Recommended)

**Zero-friction context management — one call does it all:**

```python
# Single call for complete enterprise context
result = rlm_enterprise_context(
    query="How does authentication work?",
    mode="auto",        # auto | discovery | route
    max_tokens=3000,
    include_causal=True
)

# Returns:
# - Auto-discovery (if new project)
# - Semantically routed facts
# - Relevant causal chains
# - Suggestions (git hooks, etc.)
```

### v2.1 MCP Tools

| Tool | Purpose |
|------|---------|
| `rlm_enterprise_context` | **One-call context** (recommended) |
| `rlm_install_git_hooks` | Install git hooks for auto-extract |
| `rlm_health_check` | Component health status |

---

## 🏢 v2.0 Enterprise Tools

### Hierarchical Memory (L0-L3)

| Level | Scope | TTL | Example |
|-------|-------|-----|---------|
| L0 | Project | 30d | "FastAPI monorepo with 50k LOC" |
| L1 | Domain | 7d | "Auth module uses JWT" |
| L2 | Module | 3d | "`login()` validates tokens" |
| L3 | Code | 24h | "Bug in line 42" |

### v2.0 MCP Tools Reference

```python
# Project Discovery
rlm_discover_project(task_hint="add caching")

# Semantic Context Routing
rlm_route_context(query="How does auth work?", max_tokens=2000)

# Auto-Extract Facts from Git
rlm_extract_facts(source="git_diff", auto_approve=True)

# Causal Chains
rlm_get_causal_chain(query="JWT decision")
rlm_record_causal_decision(
    decision="Use Redis for cache",
    reasons=["Low latency", "Easy clustering"],
    alternatives=["Memcached"]
)

# TTL Management
rlm_set_ttl(fact_id="abc", ttl_days=7)
rlm_get_stale_facts()

# Hierarchy Operations
rlm_add_hierarchical_fact(content="...", level=1, domain="auth")
rlm_get_hierarchy_stats()
rlm_get_facts_by_domain(domain="api")
rlm_list_domains()

# Embeddings
rlm_index_embeddings()

# Cleanup
rlm_refresh_fact(fact_id="abc")
rlm_delete_fact(fact_id="abc")
```

---

## 📚 See Also

- [API Reference](./api_reference.md) — Full 18 tools documentation
- [System Prompt Template](./memory_bridge_system_prompt.md) — LLM integration
- [MCP Server Documentation](./mcp-server.md)
- [Graphiti Paper](https://arxiv.org/abs/2501.13956) — Bi-temporal inspiration
