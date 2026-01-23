# Memory Bridge v2.0: Enterprise Amnesia Elimination

## Описание проблемы

Memory Bridge v1.1.0 решает базовую проблему cross-session persistence, но имеет ограничения:

1. **Flat Hierarchy** — все факты на одном уровне, не масштабируется для enterprise (1M+ LOC)
2. **Manual Fact Entry** — факты добавляются вручную, нет автоматической экстракции
3. **No TTL Management** — факты не устаревают автоматически
4. **Cold Start Problem** — новые проекты требуют полного discovery (15-50K токенов)
5. **No Semantic Routing** — нет умного выбора релевантных фактов для текущей задачи

## Целевые метрики

| Метрика | v1.1.0 | v2.0 Target |
|---------|--------|-------------|
| Amnesia Elimination | 70-80% | 95%+ |
| Enterprise Scale | 116K LOC | 1M+ LOC |
| Cold Start Tokens | 15-50K | 3-10K |
| Fact Relevance | Manual | Auto-routing |
| Context Freshness | Manual | TTL-based |

---

## Требования

### REQ-1: Hierarchical Memory Architecture

**MUST** реализовать иерархическую структуру памяти:

```
L0: Project Meta (always loaded, 10-20 facts)
L1: Domain/Service Clusters (loaded by task context)
L2: Module Context (loaded on-demand)
L3: Code-Level Integration (C³ Crystal)
```

**Acceptance Criteria:**
- [ ] AC-1.1: L0 facts загружаются автоматически при старте сессии
- [ ] AC-1.2: L1/L2 facts загружаются по semantic routing на основе user query
- [ ] AC-1.3: L3 интегрируется с существующим C³ Crystal compression
- [ ] AC-1.4: Поддержка проектов до 2M+ LOC без деградации quality

---

### REQ-2: Auto-Fact Extraction Engine

**MUST** автоматически извлекать факты из:
- Git commits (significant changes)
- Code changes during session
- User decisions and rationale
- README/documentation updates

**Acceptance Criteria:**
- [ ] AC-2.1: Факты извлекаются из git diff при `rlm_sync_state`
- [ ] AC-2.2: Значимые code changes (>10 lines, new files) генерируют факты
- [ ] AC-2.3: User approves/rejects auto-extracted facts (не spam)
- [ ] AC-2.4: Duplicate detection (semantic similarity >0.85 = merge)

---

### REQ-3: Semantic Fact Routing

**MUST** загружать только релевантные факты для текущей задачи:

```python
# User query: "Add authentication to payment service"
# Loaded facts:
#   L0: Project overview (always)
#   L1: auth-service cluster, payment-service cluster
#   L2: auth patterns, payment API contracts
# NOT loaded:
#   L2: reporting-service details, UI components
```

**Acceptance Criteria:**
- [ ] AC-3.1: Semantic search по query возвращает top-K релевантных facts
- [ ] AC-3.2: Cross-reference routing (если fact A связан с B, загрузить оба)
- [ ] AC-3.3: Token budget management (max 2000 tokens per injection)
- [ ] AC-3.4: Fallback to broader context если routing confidence < 0.5

---

### REQ-4: Bi-Temporal TTL Management

**MUST** автоматически управлять свежестью фактов:

| Fact Type | Default TTL | Refresh Trigger |
|-----------|-------------|-----------------|
| Architecture | 30 days | Manual or major refactor |
| API Contracts | 7 days | API file changes |
| Implementation Details | 3 days | Code changes in module |
| Session Context | 24 hours | Auto-expire |

**Acceptance Criteria:**
- [ ] AC-4.1: TTL настраивается per fact type
- [ ] AC-4.2: Expired facts помечаются как `stale`, не удаляются
- [ ] AC-4.3: Stale facts показываются с warning при injection
- [ ] AC-4.4: File watcher триггерит TTL refresh при изменениях

---

### REQ-5: Smart Cold Start

**MUST** минимизировать token consumption для новых проектов:

**Acceptance Criteria:**
- [ ] AC-5.1: Project type detection (Python/JS/Rust/Go/etc.)
- [ ] AC-5.2: Template seeding (стандартные факты для типа проекта)
- [ ] AC-5.3: Progressive discovery (только то, что нужно для первой задачи)
- [ ] AC-5.4: AST pre-indexing hook при инициализации

---

### REQ-6: Cross-Session Causal Chains

**MUST** сохранять reasoning chains между сессиями:

```
Decision: "Used FastAPI instead of Flask"
  ├── Reason: "Need async support for WebSocket"
  ├── Reason: "Team familiarity"
  └── Consequence: "Requires Python 3.9+"
      └── Consequence: "Docker base image updated"
```

**Acceptance Criteria:**
- [ ] AC-6.1: Decisions хранят связи cause → effect
- [ ] AC-6.2: Query "why did we choose X" возвращает full causal chain
- [ ] AC-6.3: Causal chains persist across sessions
- [ ] AC-6.4: Visualization в walkthrough.md

---

### REQ-7: MCP Tool Extensions

**MUST** расширить MCP API для новой функциональности:

| Tool | Description |
|------|-------------|
| `rlm_discover_project` | Cold start с smart discovery |
| `rlm_route_context` | Семантический routing facts |
| `rlm_extract_facts` | Авто-экстракция из diff |
| `rlm_get_causal_chain` | Query reasoning history |
| `rlm_set_ttl` | Управление TTL per fact |
| `rlm_get_stale_facts` | Показать устаревшие факты |

**Acceptance Criteria:**
- [ ] AC-7.1: Все tools реализованы и зарегистрированы
- [ ] AC-7.2: Backward compatibility с v1.1.0 tools
- [ ] AC-7.3: Documentation для каждого tool
- [ ] AC-7.4: Integration tests для каждого tool

---

## Non-Functional Requirements

### NFR-1: Performance

- Semantic routing: < 100ms для 1000 facts
- Fact injection: < 50ms
- Cold start discovery: < 5 seconds per 100K LOC

### NFR-2: Storage

- SQLite для < 10K facts
- Optional PostgreSQL/Redis для enterprise (> 10K facts)
- Encryption at rest (existing functionality)

### NFR-3: Compatibility

- Python 3.10+
- MCP SDK 1.x compatibility
- Works with Antigravity, Claude Desktop, VSCode + Continue

---

## Риски и Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Auto-extraction spam | High | User approval + semantic dedup |
| Semantic routing errors | Medium | Fallback to broader context |
| TTL too aggressive | Medium | Conservative defaults + override |
| Cold start slow | Low | Async background indexing |

---

## Зависимости

- Memory Bridge v1.1.0 (base)
- C³ Crystal (L3 integration)
- Sentence Transformers (semantic routing)
- File watcher (TTL refresh)
