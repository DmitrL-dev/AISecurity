# RLM-Toolkit MCP Server: Детальные задачи

## Обзор

| Фаза | Длительность | Задачи | Статус |
|------|--------------|--------|--------|
| MVP | 2 недели | 8 | ⬜ |
| C³ | 2-3 недели | 7 | ⬜ |
| H-MEM | 2 недели | 6 | ⬜ |
| Polish | 2 недели | 5 | ⬜ |
| **Итого** | **8-9 недель** | **26** | |

---

## Фаза 1: MVP (Неделя 1-2)

### T1.1: Инициализация модуля
- [ ] Создать `rlm_toolkit/mcp/__init__.py`
- [ ] Добавить `mcp` в pyproject.toml
- [ ] Настроить entry point
- **Оценка:** 2 час
- **Зависимости:** Нет

### T1.2: MCP Server базовый
- [ ] Реализовать `server.py` с stdio transport
- [ ] Добавить lifecycle handlers (init, shutdown)
- [ ] Настроить логирование
- **Оценка:** 4 часа
- **Зависимости:** T1.1

### T1.3: Tool rlm_load_context
- [ ] Загрузка файла (text, py, md, json)
- [ ] Загрузка директории (рекурсивно)
- [ ] Подсчёт токенов
- [ ] Сохранение в памяти
- **Оценка:** 4 часа
- **Зависимости:** T1.2

### T1.4: Tool rlm_query (простой)
- [ ] Keyword search в загруженном контексте
- [ ] Возврат релевантных чанков
- [ ] Форматирование ответа
- **Оценка:** 4 часа
- **Зависимости:** T1.3

### T1.5: Tool rlm_list_contexts
- [ ] Список загруженных контекстов
- [ ] Метаданные (размер, токены, время)
- **Оценка:** 2 часа
- **Зависимости:** T1.3

### T1.6: Provider auto-detect
- [ ] Проверка Ollama доступности
- [ ] Fallback на Cloud
- [ ] Конфигурация через ENV
- **Оценка:** 3 часа
- **Зависимости:** T1.2

### T1.7: Context persistence
- [ ] Сохранение в `.rlm/contexts/`
- [ ] Загрузка при старте
- [ ] Очистка по запросу
- **Оценка:** 3 часа
- **Зависимости:** T1.3

### T1.8: Интеграционный тест
- [ ] Тест в Antigravity
- [ ] Документация настройки
- **Оценка:** 4 часа
- **Зависимости:** T1.1-T1.7

**Итого MVP:** ~26 часов

---

## Фаза 2: C³ Integration (Неделя 3-4)

### T2.1: C³ модуль production
- [ ] Перенести PoC в `rlm_toolkit/crystal/`
- [ ] Рефакторинг под production
- [ ] Unit tests
- **Оценка:** 8 часов
- **Зависимости:** Фаза 1

### T2.2: spaCy NER интеграция
- [ ] Добавить spaCy dependency
- [ ] Заменить regex на NER
- [ ] Relation extraction
- **Оценка:** 12 часов
- **Зависимости:** T2.1

### T2.3: Иерархия crystals
- [ ] `ProjectCrystal` класс
- [ ] `ModuleCrystal` класс
- [ ] `FileCrystal` класс
- [ ] Связи между уровнями
- **Оценка:** 12 часов
- **Зависимости:** T2.1

### T2.4: Incremental update
- [ ] File watcher
- [ ] Partial rebuild
- [ ] Dependency tracking
- **Оценка:** 8 часов
- **Зависимости:** T2.3

### T2.5: SQLite storage
- [ ] Schema для crystals
- [ ] CRUD operations
- [ ] Индексы для поиска
- **Оценка:** 6 часов
- **Зависимости:** T2.3

### T2.6: Tool rlm_analyze
- [ ] Интеграция C³ в MCP
- [ ] Goals: summarize, find_bugs, security_audit
- [ ] Форматирование результата
- **Оценка:** 6 часов
- **Зависимости:** T2.1-T2.5

### T2.7: Benchmarks
- [ ] Тест на SENTINEL (217 files)
- [ ] Метрики: время, память, accuracy
- [ ] Документация результатов
- **Оценка:** 4 часа
- **Зависимости:** T2.6

**Итого C³:** ~56 часов

---

## Фаза 3: H-MEM Integration (Неделя 5-6)

### T3.1: H-MEM модуль
- [ ] Перенести концепт в `rlm_toolkit/memory/`
- [ ] Episode storage (SQLite)
- [ ] Trace storage
- **Оценка:** 8 часов
- **Зависимости:** Фаза 2

### T3.2: Консолидация
- [ ] Алгоритм консолидации
- [ ] Выбор модели (local vs cloud)
- [ ] Conflict detection
- **Оценка:** 12 часов
- **Зависимости:** T3.1

### T3.3: Per-project isolation
- [ ] `.rlm/memory/` structure
- [ ] Project identification
- [ ] Migration tool
- **Оценка:** 4 часа
- **Зависимости:** T3.1

### T3.4: Шифрование
- [ ] AES-256-GCM implementation
- [ ] Key management
- [ ] Encrypted storage
- **Оценка:** 6 часов
- **Зависимости:** T3.3

### T3.5: Tool rlm_memory
- [ ] recall: получить воспоминания
- [ ] forget: удалить
- [ ] consolidate: принудительно консолидировать
- [ ] list: показать статистику
- **Оценка:** 6 часов
- **Зависимости:** T3.1-T3.4

### T3.6: Integration tests
- [ ] Multi-session тест
- [ ] Memory persistence тест
- **Оценка:** 4 часа
- **Зависимости:** T3.5

**Итого H-MEM:** ~40 часов

---

## Фаза 4: Polish (Неделя 7-8)

### T4.1: Rate limiting
- [ ] Token counter
- [ ] Exponential backoff
- [ ] User notification
- **Оценка:** 4 часа

### T4.2: Error handling
- [ ] Graceful fallbacks
- [ ] User-friendly messages
- [ ] Recovery mechanisms
- **Оценка:** 6 часов

### T4.3: Documentation
- [ ] README update
- [ ] docs/mcp-server.md
- [ ] Examples
- **Оценка:** 4 часа

### T4.4: CLI tool
- [ ] `rlm memory list`
- [ ] `rlm crystal build`
- [ ] `rlm server start`
- **Оценка:** 6 часов

### T4.5: Release
- [ ] Version bump
- [ ] Changelog
- [ ] PyPI publish
- **Оценка:** 2 часа

**Итого Polish:** ~22 часов

---

## Сводка по времени

| Фаза | Часы | Недели (40ч/нед) |
|------|------|------------------|
| MVP | 26 | 0.7 |
| C³ | 56 | 1.4 |
| H-MEM | 40 | 1.0 |
| Polish | 22 | 0.6 |
| **Итого** | **144** | **3.6** |

**Реалистичная оценка с buffer:** 8-9 недель

---

*Статус: ГОТОВО К РЕВЬЮ*
