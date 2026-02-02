# AI Engines Dashboard — Tasks

> **Фаза:** Phase 7 AI Engines
> **Статус:** ✅ Complete
> **Дата:** 2026-01-30

---

## Чеклист имплементации

### Task 1: Backend Engine ✅
- [x] 1.1 Создать `src/brain/engines/foundation_sec.py`
- [x] 1.2 Реализовать `analyze()` method
- [x] 1.3 Реализовать `get_reasoning_trace()`
- [x] 1.4 Реализовать `map_to_mitre()`
- [x] 1.5 Добавить health check

### Task 2: API Endpoints ✅
- [x] 2.1 Создать `/api/brain/engines/[name]/stats`
- [x] 2.2 Создать `/api/brain/engines/[name]/analyze`
- [x] 2.3 Mock данные для dev mode

### Task 3: EngineCard Component ✅
- [x] 3.1 Создать `EngineCard.tsx`
- [x] 3.2 Fetch stats from API
- [x] 3.3 Status indicator (online/offline)
- [x] 3.4 Configure button с drawer

### Task 4: EngineStatsPanel Component ✅
- [x] 4.1 Создать `EngineStatsPanel.tsx`
- [x] 4.2 Stats cards grid
- [x] 4.3 Latency percentiles
- [x] 4.4 24h mini charts

### Task 5: ReasoningViewer Component ✅
- [x] 5.1 Создать `ReasoningViewer.tsx`
- [x] 5.2 Risk score banner
- [x] 5.3 Conclusion block
- [x] 5.4 Collapsible thinking
- [x] 5.5 MITRE techniques list
- [x] 5.6 Recommendations

### Task 6: MitreAttackMap Component ✅
- [x] 6.1 Создать `MitreAttackMap.tsx`
- [x] 6.2 14 tactics timeline
- [x] 6.3 Expandable groups
- [x] 6.4 Confidence bars
- [x] 6.5 External MITRE links

### Task 7: EngineCompareView Component ✅
- [x] 7.1 Создать `EngineCompareView.tsx`
- [x] 7.2 Payload input
- [x] 7.3 Side-by-side results
- [x] 7.4 Combined assessment

### Task 8: /brain Page Extension ✅
- [x] 8.1 Добавить mainTab state
- [x] 8.2 Создать 5 tabs (Overview, AI Engines, Compare, Qwen3-Guard, Foundation-sec)
- [x] 8.3 Conditional rendering per tab
- [x] 8.4 Import all components

### Task 9: Testing
- [x] 9.1 Build без ошибок
- [ ] 9.2 Unit tests для компонентов
- [ ] 9.3 Integration tests с API

### Task 10: Documentation ✅
- [x] 10.1 Spec requirements.md
- [x] 10.2 Spec design.md
- [x] 10.3 Spec tasks.md

---

## Зависимости

```
Task 1 (Backend) ──► Task 2 (API)
                          │
                          ▼
            ┌─────────────┴─────────────┐
            ▼                           ▼
     Task 3 (Card)              Task 4 (Stats)
            │                           │
            └───────────┬───────────────┘
                        ▼
                 Task 5 (Reasoning)
                        │
                        ▼
                 Task 6 (MITRE)
                        │
                        ▼
                 Task 7 (Compare)
                        │
                        ▼
                 Task 8 (Page)
                        │
                        ▼
                 Task 9 (Tests)
                        │
                        ▼
                 Task 10 (Docs)
```

---

## Результаты

| Метрика | Значение |
|---------|----------|
| Файлов создано | 7 |
| Строк кода | ~1500 |
| Build size `/brain` | 14.2 KB |
| Время имплементации | ~2 часа |
