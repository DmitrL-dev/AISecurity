# RLM Steering Auto-Injection

## Problem
RLM не предотвращает "амнезию" — правила из `.kiro/steering/*.md` (TDD Iron Law и др.) не попадают в память автоматически.

## Root Cause
1. **Steering files не индексируются** — RLM не читает `.kiro/steering/` при старте
2. **L0 facts пустые** — пока вручную не добавишь, их нет
3. **Нет auto-inject** — `rlm_route_context` не вызывается перед каждой задачей

## Proposed Solution

### Option A: Steering → RLM Seed (рекомендуется)
```
/context workflow:
1. Читает .kiro/steering/*.md
2. Парсит ключевые правила
3. Добавляет как L0 facts в RLM
4. Вызывает rlm_sync_state
```

### Option B: Pre-task Context Hook
```
Перед каждым task_boundary(EXECUTION):
1. rlm_route_context("methodology TDD rules")
2. Inject в system prompt
```

### Option C: Hybrid
- Seed при /context
- Re-inject при EXECUTION mode

## Acceptance Criteria
- [ ] `rlm_search_facts("TDD")` возвращает L0 правило
- [ ] При старте сессии правила видны без мануальных действий
- [ ] Нарушение TDD детектируется ДО написания кода

## Priority
**P0** — блокирует качество работы
