---
description: Update context artifacts after each work session
---

# Context Update Rule

> ⚠️ **CRITICAL RULE**: PROJECT_CONTEXT.md ДОЛЖЕН ревизироваться и поддерживаться в АКТУАЛЬНОМ состоянии на КАЖДОМ этапе проекта!

**ОБЯЗАТЕЛЬНО** после каждого завершённого блока работы обновлять:

## Artifacts to Update

1. **PROJECT_CONTEXT.md** — ГЛАВНЫЙ контекст проекта (`.agent/`)
2. **task.md** — отметить выполненные пункты `[x]`
3. **implementation_plan.md** — обновить статус и статистику
4. **walkthrough.md** — добавить что сделано в сессии

## PROJECT_CONTEXT.md — Что проверять

- [ ] **Last Updated** — дата актуальна?
- [ ] **Engine count** — 121 или изменилось?
- [ ] **Test count** — 155+ или изменилось?
- [ ] **Project Structure** — все новые модули добавлены?
- [ ] **New components** — Kernel Driver, Desktop, новые модули?

## When to Update

- После каждого крупного коммита
- После закрытия задачи
- Перед `notify_user` с результатами
- В конце рабочей сессии
- **При изменении структуры проекта**
- **При добавлении новых модулей/компонентов**

## Statistics to Update

```bash
# LOC count
find src/brain -name "*.py" -exec wc -l {} + | tail -1

# Engine count
find src/brain/engines -name "*.py" | wc -l

# Test count
grep -r "def test_" tests/ | wc -l
```

## Checklist

- [ ] PROJECT_CONTEXT.md — data актуальна?
- [ ] task.md — items marked complete?
- [ ] implementation_plan.md — stats current?
- [ ] README engine count correct?
- [ ] Community README synced?
