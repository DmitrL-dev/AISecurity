# RLM-Toolkit MCP Server

MCP (Model Context Protocol) Server для интеграции RLM-Toolkit с IDE.

## Установка

```bash
pip install rlm-toolkit[mcp]
```

## Быстрый старт

### 1. Проверка работоспособности

```bash
python -c "from rlm_toolkit.mcp import RLMServer; s = RLMServer(); print('OK')"
```

### 2. Конфигурация IDE

Создайте файл конфигурации MCP (зависит от IDE):

**Antigravity / Cursor / Claude Desktop:**
```json
{
  "mcpServers": {
    "rlm-toolkit": {
      "command": "python",
      "args": ["-m", "rlm_toolkit.mcp.server"]
    }
  }
}
```

### 3. Перезапустите IDE

После перезапуска RLM-Toolkit tools будут доступны.

---

## MCP Tools

### rlm_load_context
Загрузка файла или директории в контекст.

```
rlm_load_context(path="./src", name="my_project")
```

### rlm_query
Поиск в загруженном контексте.

```
rlm_query(question="where is authentication?", context_name="my_project")
```

### rlm_list_contexts
Список загруженных контекстов.

```
rlm_list_contexts()
```

### rlm_analyze
Глубокий анализ через C³ crystals.

```
rlm_analyze(goal="summarize")        # Суммаризация
rlm_analyze(goal="find_bugs")        # Поиск багов  
rlm_analyze(goal="security_audit")   # Аудит безопасности
rlm_analyze(goal="explain")          # Объяснение структуры
```

### rlm_memory
Управление H-MEM памятью.

```
rlm_memory(action="store", content="важная информация")
rlm_memory(action="recall", topic="аутентификация")
rlm_memory(action="forget", topic="устаревшее")
rlm_memory(action="consolidate")
rlm_memory(action="stats")
```

### rlm_status
Статус сервера и индекса.

```
rlm_status()
# Returns: version, crystals count, tokens, db_size, secure_mode
```

### rlm_session_stats
Статистика экономии токенов в сессии.

```
rlm_session_stats()           # Получить статистику
rlm_session_stats(reset=True) # Сбросить счётчики
```

### rlm_reindex
Реиндексация проекта (rate limit: 1 раз в 60 сек).

```
rlm_reindex()                 # Delta update
rlm_reindex(force=True)       # Полная переиндексация
rlm_reindex(path="./src")     # Конкретный путь
```

### rlm_validate
Валидация свежести индекса.

```
rlm_validate()
# Returns: symbols, stale_files, health status
```

### rlm_settings
Получение/установка настроек.

```
rlm_settings(action="get")
rlm_settings(action="set", key="ttl_hours", value="48")
```

---

## Memory Bridge Tools (NEW)

Cross-session state persistence с bi-temporal моделью. [Подробнее](./memory-bridge.md)

### rlm_sync_state
Сохранить текущее состояние агента.

```
rlm_sync_state()
# Returns: {"version": 5, "session_id": "abc123"}
```

### rlm_restore_state
Восстановить состояние сессии.

```
rlm_restore_state(session_id="abc123")
rlm_restore_state(session_id="abc123", version=3)  # Конкретная версия
```

### rlm_get_state
Получить текущее состояние как JSON.

```
rlm_get_state()
```

### rlm_list_sessions
Список сохранённых сессий.

```
rlm_list_sessions()
```

### rlm_add_fact
Добавить факт с bi-temporal tracking.

```
rlm_add_fact(content="API limit is 100 req/min", entity_type="fact", confidence=0.95)
```

### rlm_search_facts
Hybrid search по фактам (semantic + keyword + recency).

```
rlm_search_facts(query="rate limit", top_k=10)
```

### rlm_build_communities
Кластеризация фактов (требует sklearn).

```
rlm_build_communities(min_cluster_size=3)
```

### rlm_update_goals
Установить/обновить цель.

```
rlm_update_goals(goal_description="Implement auth", progress=0.5)
```

### rlm_record_decision
Записать архитектурное решение.

```
rlm_record_decision(description="Use JWT", rationale="Industry standard")
```

### rlm_add_hypothesis
Добавить гипотезу для проверки.

```
rlm_add_hypothesis(statement="Caching reduces latency by 50%")
```

---

## Конфигурация

### Переменные окружения

| Переменная | Описание | Default |
|------------|----------|---------|
| `RLM_SECURE_MEMORY` | Шифрование памяти | `true` |
| `RLM_ENCRYPTION_KEY` | Ключ шифрования (32 bytes) | auto-generated |

### Отключение шифрования (dev)

```bash
export RLM_SECURE_MEMORY=false
```

---

## Архитектура

```
┌─────────────────────────────────────────────────────┐
│                   MCP Client (IDE)                  │
└─────────────────────┬───────────────────────────────┘
                      │ stdio
┌─────────────────────▼───────────────────────────────┐
│                  RLM MCP Server                     │
│  ┌─────────────┐ ┌─────────────┐ ┌───────────────┐  │
│  │ContextMgr   │ │ C³ Crystal  │ │   H-MEM       │  │
│  │ (files)     │ │ (analysis)  │ │  (memory)     │  │
│  └─────────────┘ └─────────────┘ └───────────────┘  │
│                         │                           │
│                ┌────────▼────────┐                  │
│                │  ProviderRouter │                  │
│                │ (Ollama/Cloud)  │                  │
│                └─────────────────┘                  │
└─────────────────────────────────────────────────────┘
```

---

## Хранилище

Данные хранятся в `.rlm/` в корне проекта:

```
.rlm/
├── contexts/        # Метаданные контекстов
├── crystals/        # C³ кристаллы  
├── memory/          # H-MEM данные
├── cache/           # Кэш
└── .encryption_key  # Ключ шифрования (auto-generated)
```

---

## Безопасность

- **SecureHierarchicalMemory** включён по умолчанию
- **Encryption at rest** для всех данных памяти
- **Access logging** для аудита
- **Trust zones** для изоляции агентов

---

## Версия

v1.2.1 — January 2026

**MCP Tools (20 total):**

*Core Tools (10):*
1. `rlm_load_context` — Load file/directory
2. `rlm_query` — Search in context
3. `rlm_list_contexts` — List contexts
4. `rlm_analyze` — C³ crystal analysis
5. `rlm_memory` — H-MEM operations
6. `rlm_status` — Server status
7. `rlm_session_stats` — Token savings tracking
8. `rlm_reindex` — Reindex project (rate limited: 60s)
9. `rlm_validate` — Check freshness
10. `rlm_settings` — Get/set settings

*Memory Bridge Tools (10):*
11. `rlm_sync_state` — Save agent state
12. `rlm_restore_state` — Restore session
13. `rlm_get_state` — Get current state
14. `rlm_list_sessions` — List all sessions
15. `rlm_add_fact` — Add bi-temporal fact
16. `rlm_search_facts` — Hybrid fact search
17. `rlm_build_communities` — Cluster facts
18. `rlm_update_goals` — Set/update goals
19. `rlm_record_decision` — Record decisions
20. `rlm_add_hypothesis` — Add hypothesis

**Security (v1.2.1):**
- AES-256-GCM fail-closed (no XOR fallback)
- Rate limiting on reindex
- .gitignore for encryption keys

