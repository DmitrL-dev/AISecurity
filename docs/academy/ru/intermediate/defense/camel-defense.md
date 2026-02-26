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

```python
from enum import Enum
from dataclasses import dataclass

class Capability(Enum):
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EXECUTE = "execute_code"

@dataclass
class CaMeLContext:
    allowed: set
    scope: str
    max_actions: int = 10

class CaMeLGuard:
    def validate(self, ctx: CaMeLContext, action: Capability, target: str) -> bool:
        if action not in ctx.allowed:
            return False
        return fnmatch.fnmatch(target, ctx.scope)
```

---

## Следующий урок

→ [32. SecAlign](32-secalign.md)
