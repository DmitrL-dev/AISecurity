---
description: Updating documentation after code changes - ОБЯЗАТЕЛЬНОЕ ПРАВИЛО
---

## Workflow: Documentation Sync

**CRITICAL RULE:** После КАЖДОГО крупного блока изменений (новый модуль, этап roadmap) ОБЯЗАТЕЛЬНО обновить ВСЮ документацию:

### 1. Основной проект (C:\AISecurity)

- [ ] `README.md` — обновить статистику, badges, фичи
- [ ] `docs/ARCHITECTURE.md` — если менялась архитектура
- [ ] `docs/CHANGELOG.md` — добавить записи об изменениях
- [ ] Подсчитать новую статистику (см. команды ниже)

### 2. Community версия (C:\AISecurity\sentinel-community)

- [ ] `README.md` — синхронизировать фичи с main
- [ ] `docs/` — обновить документацию
- [ ] `signatures/` — добавить новые сигнатуры если есть

### 3. Artifact files

- [ ] `task.md` — Mark `[ ]` → `[x]` for completed
- [ ] `walkthrough.md` — добавить секцию о выполненной работе
- [ ] `implementation_plan.md` — обновить если нужно

### 4. Команды для статистики:

```powershell
# LOC count (Python brain)
// turbo
Get-ChildItem -Path "src/brain" -Recurse -Include "*.py" | ForEach-Object { (Get-Content $_).Count } | Measure-Object -Sum

# Engine count
// turbo
Get-ChildItem -Path "src/brain/engines" -Filter "*.py" | Where-Object { $_.Name -ne "__init__.py" } | Measure-Object

# Total Python files
// turbo
Get-ChildItem -Path "src/brain" -Recurse -Filter "*.py" | Measure-Object
```

### 5. Что обновлять в README:

| Элемент              | Что менять            |
| -------------------- | --------------------- |
| Engine count badge   | Число engines         |
| LOC stats            | Total lines           |
| Features list        | Добавить новые модули |
| Architecture diagram | Новые компоненты      |

### 6. Locations:

- Main README: `C:\AISecurity\README.md`
- Community README: `C:\AISecurity\sentinel-community\README.md`
- task.md: Current conversation brain folder
- Docs: `C:\AISecurity\docs\`

// turbo-all
