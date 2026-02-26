# CaMeL Defense

> **Трек:** 05 — Стратегии защиты  
> **Урок:** 31  
> **Уровень:** Продвинутый

---

## Обзор

CaMeL (Capability-Mediated Layer) — защитная архитектура с **разделением capabilities и контента**, предотвращающая эскалацию привилегий через prompt injection.

---

## Теория

```
User Input → CaMeL Layer → LLM Core
              ↓
        [Capability Guard] + [Content Sanitizer]
```

### Принципы

1. **Разделение capabilities** — инструменты определяются вне промпта
2. **Least Privilege** — минимум необходимых прав
3. **Изоляция контента** — пользовательский текст не может давать права
4. **Детерминистическое исполнение** — правила исполняются кодом

---

## Практика

```rust
use std::collections::HashSet;

#[derive(Clone, PartialEq, Eq, Hash)]
enum Capability {
    ReadFile,
    WriteFile,
    Execute,
}

struct CaMeLContext {
    allowed: HashSet<Capability>,
    scope: String,
    max_actions: usize,
}

struct CaMeLGuard;

impl CaMeLGuard {
    fn validate(&self, ctx: &CaMeLContext, action: &Capability, target: &str) -> bool {
        if !ctx.allowed.contains(action) {
            return false;
        }
        glob_match::glob_match(&ctx.scope, target)
    }
}
```

---

## Следующий урок

→ [32. SecAlign](32-secalign.md)
