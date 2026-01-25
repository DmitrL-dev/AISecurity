# DevKit Prompts

> Адаптированные промпты для agent-first разработки в SENTINEL

## Архитектура промптов

```
prompts/
├── README.md           # Этот файл
├── reviewer.md         # Промпт для Reviewer Agent
├── fixer.md            # Промпт для Fixer Agent
└── security-audit.md   # Промпт для Security Auditor
```

---

## Философия

Промпты DevKit следуют принципам:
1. **Explicit > Implicit** — чёткие инструкции, не полагаться на "понимание"
2. **Structured Output** — JSON/Markdown форматы для парсинга
3. **Guardrails** — лимиты, эскалация, safety checks
4. **SENTINEL-aware** — знание архитектуры проекта

---

## Базовые промпты

### reviewer.md

См. отдельный файл `reviewer.md`

### fixer.md

См. отдельный файл `fixer.md`

### security-audit.md

См. отдельный файл `security-audit.md`
