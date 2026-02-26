# Tutorial 8: Pattern Engineering

> **SSP Module 2.6**

---

## 🎯 Цель

Научиться создавать эффективные паттерны:

- Evasion-resistant regex
- Semantic patterns
- Multi-layer detection
- Performance optimization

---

## Шаг 1: Проблема простых паттернов

### Простой паттерн

```json
{ "pattern": "ignore previous", "pattern_type": "literal" }
```

### Как его обходят

| Evasion   | Пример                          |
| --------- | ------------------------------- |
| Case      | "IGNORE PREVIOUS"               |
| Spacing   | "ignore previous"               |
| Insertion | "ig.nore prev.ious"             |
| Unicode   | "іgnore prevіous" (кириллица і) |
| Encoding  | "aWdub3JlIHByZXZpb3Vz" (base64) |
| Synonyms  | "disregard prior"               |

---

## Шаг 2: Case-Insensitive Patterns

```json
{
  "name": "ignore_previous_v2",
  "pattern": "(?i)ignore\\s+previous",
  "pattern_type": "regex"
}
```

`(?i)` = case-insensitive flag

Ловит:

- ✅ "ignore previous"
- ✅ "IGNORE PREVIOUS"
- ✅ "Ignore Previous"

---

## Шаг 3: Flexible Spacing

```json
{
  "name": "ignore_previous_v3",
  "pattern": "(?i)ignore\\s+previous",
  "pattern_type": "regex"
}
```

`\\s+` = один или более пробелов

Ловит:

- ✅ "ignore previous"
- ✅ "ignore previous" (2 пробела)
- ✅ "ignore\tprevious" (tab)

---

## Шаг 4: Character Insertion Resistance

```json
{
  "name": "ignore_previous_v4",
  "pattern": "(?i)i[^a-z]*g[^a-z]*n[^a-z]*o[^a-z]*r[^a-z]*e\\s+p[^a-z]*r[^a-z]*e[^a-z]*v[^a-z]*i[^a-z]*o[^a-z]*u[^a-z]*s",
  "pattern_type": "regex"
}
```

Ловит:

- ✅ "i.g.n.o.r.e p.r.e.v.i.o.u.s"
- ✅ "i-g-n-o-r-e previous"

⚠️ Но становится медленным и сложным.

---

## Шаг 5: Synonym Groups

Лучший подход — группы синонимов:

```json
{
  "name": "instruction_override",
  "pattern": "(?i)(ignore|disregard|forget|overlook|dismiss)\\s+(all\\s+)?(previous|prior|above|earlier|preceding)\\s*(instructions?|rules?|guidelines?|directives?)?",
  "pattern_type": "regex",
  "action": "block",
  "severity": 9
}
```

Ловит:

- ✅ "ignore previous instructions"
- ✅ "disregard prior rules"
- ✅ "forget all earlier guidelines"
- ✅ "overlook preceding directives"

---

## Шаг 6: Semantic Fallback

Regex не поймает новые формулировки.

Добавляем semantic:

```json
{
  "rules": [
    {
      "id": 1,
      "name": "injection_regex",
      "pattern": "(?i)(ignore|disregard)\\s+previous",
      "pattern_type": "regex",
      "action": "block",
      "severity": 9
    },
    {
      "id": 2,
      "name": "injection_semantic",
      "pattern": "instruction_override",
      "pattern_type": "semantic",
      "threshold": 0.85,
      "action": "block",
      "severity": 9
    }
  ]
}
```

**Порядок важен:**

1. Regex — быстрый, ловит известные
2. Semantic — медленнее, ловит новые

---

## Шаг 7: Encoding Detection Layer

Shield автоматически декодирует перед проверкой:

```json
{
  "preprocessing": {
    "base64_decode": true,
    "url_decode": true,
    "unicode_normalize": true,
    "strip_invisible": true
  }
}
```

| Input                       | After preprocessing |
| --------------------------- | ------------------- |
| "aWdub3JlIHByZXZpb3Vz"      | "ignore previous"   |
| "ignore%20previous"         | "ignore previous"   |
| "іgnore" (cyrillic і)       | "ignore"            |
| "ig\u200bnore" (zero-width) | "ignore"            |

---

## Шаг 8: Composite Patterns

Для сложных атак — составные правила:

```json
{
  "composite_rules": [
    {
      "name": "sophisticated_injection",
      "conditions": [
        { "type": "contains", "value": "instruction" },
        { "type": "regex", "value": "(?i)(new|different|changed)" },
        { "type": "semantic", "value": "role_manipulation", "threshold": 0.7 }
      ],
      "operator": "AND",
      "action": "block",
      "severity": 9
    }
  ]
}
```

Все три условия должны совпасть.

---

## Шаг 9: Pattern Testing Tool

### CLI

```bash
Shield> test-pattern "(?i)ignore\\s+previous"
Enter test inputs (empty line to finish):
> ignore previous
MATCH
> IGNORE PREVIOUS
MATCH
> disregard prior
NO MATCH
>
```

### API

```bash
curl -X POST http://localhost:8080/api/v1/test-pattern \
  -d '{
    "pattern": "(?i)ignore\\s+previous",
    "pattern_type": "regex",
    "inputs": [
      "ignore previous",
      "IGNORE PREVIOUS",
      "disregard prior"
    ]
  }'
```

```json
{
  "results": [
    { "input": "ignore previous", "match": true },
    { "input": "IGNORE PREVIOUS", "match": true },
    { "input": "disregard prior", "match": false }
  ]
}
```

---

## Шаг 10: Performance Optimization

### Порядок правил

```json
{
  "rules": [
    { "id": 1, "pattern_type": "literal" }, // Fastest
    { "id": 2, "pattern_type": "regex" }, // Medium
    { "id": 3, "pattern_type": "semantic" } // Slowest
  ]
}
```

### Benchmarking

```bash
Shield> benchmark-rules

Rule Performance:
┌─────────────────────────┬──────────────┬─────────────┐
│ Rule                    │ Avg Time     │ 99th %ile   │
├─────────────────────────┼──────────────┼─────────────┤
│ block_keyword (literal) │ 0.02ms       │ 0.05ms      │
│ injection_regex (regex) │ 0.15ms       │ 0.32ms      │
│ semantic_check (semantic)│ 2.50ms       │ 5.10ms      │
└─────────────────────────┴──────────────┴─────────────┘
```

### Оптимизация regex

```regex
# BAD: Catastrophic backtracking
.*ignore.*previous.*

# GOOD: Bounded matching
.{0,50}ignore.{0,20}previous
```

---

## Шаг 11: C Integration

```c
#include "sentinel_shield.h"

int main(void) {
    shield_context_t ctx;
    shield_init(&ctx);
    shield_load_config(&ctx, "config.json");

    // Тестирование паттерна
    pattern_test_result_t result;
    const char *inputs[] = {
        "ignore previous",
        "IGNORE PREVIOUS",
        "disregard prior",
        NULL
    };

    shield_test_pattern(&ctx,
                        "(?i)ignore\\s+previous",
                        PATTERN_REGEX,
                        inputs,
                        &result);

    printf("Matches: %d/%d\n", result.match_count, result.total_count);

    for (int i = 0; i < result.total_count; i++) {
        printf("[%s] %s\n",
               result.matches[i] ? "MATCH" : "NO MATCH",
               inputs[i]);
    }

    shield_destroy(&ctx);
    return 0;
}
```

---

## 🎉 Что ты узнал

- ✅ Evasion-resistant regex
- ✅ Synonym groups
- ✅ Semantic fallback
- ✅ Encoding detection
- ✅ Performance optimization
- ✅ Pattern testing

---

## Следующий tutorial

**Tutorial 9:** Monitoring — Prometheus, Grafana, Alerting

---

_"Хороший паттерн — как хороший замок. Сложно взломать, легко использовать."_
