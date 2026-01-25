# SENTINEL Community Full Audit — Plan

## Цель
Найти и исправить все скрытые баги, неработающий код, несоответствия API через систематический аудит.

---

## Phase 1: Discovery (Parallel)

### Agent: Researcher (haiku)
**Задачи:**
- [ ] Список всех Python файлов с `# TODO`, `# FIXME`, `# BUG`
- [ ] Список всех `raise NotImplementedError`
- [ ] Список всех `pass` в методах (пустые реализации)
- [ ] Несоответствия версий (pyproject.toml vs __init__.py vs README)

### Agent: Type Checker (sonnet)
**Задачи:**
- [ ] Запуск mypy на всех модулях
- [ ] Сбор ошибок типизации
- [ ] Приоритизация по severity

### Agent: Test Runner (sonnet)
**Задачи:**
- [ ] pytest --collect-only (найти все тесты)
- [ ] pytest с покрытием
- [ ] Список failing tests

---

## Phase 2: Static Analysis (Parallel)

### Agent: Linter (haiku)
- [ ] ruff check (all errors)
- [ ] bandit (security issues)
- [ ] Группировка по типу

### Agent: Import Analyzer (haiku)
- [ ] Циклические импорты
- [ ] Неиспользуемые импорты
- [ ] Сломанные импорты

### Agent: API Consistency (sonnet)
- [ ] __init__.py exports vs actual modules
- [ ] Public API documentation vs implementation
- [ ] Deprecation warnings

---

## Phase 3: Deep Analysis (Sequential)

### Agent: Code Reviewer (opus)
**Приоритет: найденные проблемы Phase 1-2**
- [ ] Анализ каждого критического бага
- [ ] Оценка impact
- [ ] Предложение фиксов

### Agent: Security Scanner (opus)
- [ ] Hardcoded secrets
- [ ] Unsafe deserialization
- [ ] Input validation gaps

---

## Phase 4: Fix & Test (Pipeline)

```
Planner → Coder → Tester → Reviewer → Integrator
```

Для каждого бага:
1. **Planner**: Создаёт план фикса
2. **Coder**: Пишет код
3. **Tester**: Пишет/запускает тесты
4. **Reviewer**: Проверяет
5. **Integrator**: Коммитит

---

## Execution Strategy

### Tools Available
- `pytest` — тестирование
- `mypy` — типы
- `ruff` — линтинг
- `bandit` — security
- `grep`/`find` — поиск паттернов

### Orchestration
```
                 ┌───────────────┐
                 │  Orchestrator │
                 │    (opus)     │
                 └───────┬───────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
   ┌──────────┐   ┌──────────┐   ┌──────────┐
   │Researcher│   │Type Check│   │Test Run  │
   │ (haiku)  │   │ (sonnet) │   │ (sonnet) │
   └────┬─────┘   └────┬─────┘   └────┬─────┘
        │              │              │
        └──────────────┼──────────────┘
                       ▼
               ┌──────────────┐
               │  Aggregator  │
               │   (sonnet)   │
               └──────┬───────┘
                      ▼
               ┌──────────────┐
               │    Fixer     │
               │   (sonnet)   │
               └──────────────┘
```

---

## Expected Output

1. `audit_report.md` — полный отчёт
2. `bugs_found.json` — структурированный список багов
3. `fixes_applied.md` — что исправлено
4. Git commits для каждого фикса

---

## Start Commands

```bash
# Phase 1: Discovery
grep -rn "# TODO\|# FIXME\|# BUG" src/ --include="*.py"
grep -rn "raise NotImplementedError" src/ --include="*.py"
grep -rn "^\s*pass$" src/ --include="*.py"

# Phase 2: Static Analysis
ruff check src/ --output-format=json
mypy src/ --ignore-missing-imports
bandit -r src/ -f json

# Phase 3: Tests
pytest tests/ -v --tb=short
pytest tests/ --cov=src/ --cov-report=term-missing
```

---

## Готов начать?
Approve this plan and I'll execute Phase 1 in parallel.
