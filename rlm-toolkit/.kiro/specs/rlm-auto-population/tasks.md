# RLM Auto-Population Enhancement - Tasks

## Порядок имплементации

### Task 1: Создать структуру extractors (2-3 часа)

**Файлы:**
- `[NEW] src/rlm_mcp_server/extractors/__init__.py`
- `[NEW] src/rlm_mcp_server/extractors/base.py`
- `[NEW] src/rlm_mcp_server/extractors/code_extractor.py`
- `[NEW] src/rlm_mcp_server/extractors/config_extractor.py`

**Acceptance:**
- [ ] BaseExtractor абстрактный класс
- [ ] CodeExtractor парсит README, docstrings
- [ ] ConfigExtractor парсит package.json, pyproject.toml

---

### Task 2: Реализовать rlm_discover_deep (2-3 часа)

**Файлы:**
- `[MODIFY] src/rlm_mcp_server/tools.py` — добавить tool
- `[NEW] src/rlm_mcp_server/extractors/orchestrator.py`

**Acceptance:**
- [ ] Tool зарегистрирован в MCP
- [ ] Возвращает FactCandidate list
- [ ] Извлекает ≥20 фактов для типичного проекта

---

### Task 3: Реализовать ConversationExtractor (2 часа)

**Файлы:**
- `[NEW] src/rlm_mcp_server/extractors/conversation_extractor.py`
- `[MODIFY] src/rlm_mcp_server/tools.py` — добавить rlm_extract_from_conversation

**Acceptance:**
- [ ] Детектирует паттерны решений
- [ ] Создаёт candidates с requires_approval=True

---

### Task 4: Реализовать GitExtractor (2 часа)

**Файлы:**
- `[NEW] src/rlm_mcp_server/extractors/git_extractor.py`
- `[MODIFY] src/rlm_mcp_server/tools.py`

**Acceptance:**
- [ ] Парсит conventional commits
- [ ] Извлекает domain из scope

---

### Task 5: UI для candidates в VSCode (3-4 часа)

**Файлы:**
- `[MODIFY] rlm-vscode-extension/src/dashboardProvider.ts`
- `[NEW] rlm-vscode-extension/src/candidatesView.ts`

**Acceptance:**
- [ ] Список candidates в sidebar
- [ ] Approve/Reject кнопки
- [ ] Bulk approve

---

### Task 6: File Watcher (опционально) (2 часа)

**Файлы:**
- `[NEW] src/rlm_mcp_server/watcher.py`
- `[MODIFY] src/rlm_mcp_server/tools.py`

**Acceptance:**
- [ ] rlm_watch_start/stop tools
- [ ] Debounce работает
- [ ] Не блокирует event loop

---

## Verification Plan

### Unit Tests

```bash
# Запуск всех тестов
cd rlm-toolkit
python -m pytest tests/ -v

# Конкретный extractor
python -m pytest tests/test_extractors.py -v
```

### Integration Test

```bash
# Запуск MCP сервера и вызов discover_deep
python -m rlm_mcp_server
# В другом терминале:
python tests/test_integration_discover.py
```

### Manual Test (VSCode)

1. Открыть проект SENTINEL в VSCode
2. Открыть RLM Dashboard
3. Нажать "Discover Deep" (новая кнопка)
4. Проверить что появились candidates
5. Approve 1 candidate, проверить что стал fact
6. Reject 1 candidate, проверить что удалился

---

## Dependencies

```
# Новые зависимости в pyproject.toml
gitpython>=3.1.0  # для GitExtractor
watchfiles>=0.21  # для File Watcher
```

---

## Estimate

| Task | Часы | Приоритет |
|------|------|-----------|
| Task 1: extractors структура | 2-3 | HIGH |
| Task 2: discover_deep | 2-3 | HIGH |
| Task 3: ConversationExtractor | 2 | HIGH |
| Task 4: GitExtractor | 2 | MEDIUM |
| Task 5: VSCode UI | 3-4 | MEDIUM |
| Task 6: File Watcher | 2 | LOW |
| **Total** | **13-16** | |
