# SENTINEL Academy — Module 2

## SENTINEL Shield: Архитектура

_SSA Level | Время: 4 часа_

---

## Введение

В Module 1 ты изучил атаки.

Теперь разберём КАК Shield защищает от них.

---

## 2.1 Концепция DMZ для AI

### Из сетевой безопасности

```
Internet (Untrusted)
        │
        ▼
┌───────────────────┐
│      FIREWALL     │ ← Фильтрует трафик
└───────────────────┘
        │
        ▼
┌───────────────────┐
│       DMZ         │ ← Буферная зона
│  (Web servers,    │
│   Load balancers) │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│   INTERNAL NET    │ ← Защищённая зона
│   (Databases,     │
│    Core systems)  │
└───────────────────┘
```

### Для AI

```
User Input (Untrusted)
        │
        ▼
┌───────────────────┐
│  SENTINEL SHIELD  │ ← AI Firewall
└───────────────────┘
        │
        ▼
┌───────────────────┐
│    AI MODEL       │ ← LLM, RAG, Agent
│    (Untrusted!)   │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│  SENTINEL SHIELD  │ ← Output filter
└───────────────────┘
        │
        ▼
User (Gets safe response)
```

**Ключевое отличие:** AI модель тоже в UNTRUSTED зоне!

---

## 2.2 Зоны Доверия (Trust Zones)

### Концепция

Shield работает с **зонами доверия** — логическими областями с разными уровнями.

```c
typedef struct {
    char name[64];
    int trust_level;        // 1-10
    zone_policy_t policy;
    rate_limit_t rate_limit;
} zone_t;
```

### Уровни доверия

| Level | Зона            | Пример                    |
| ----- | --------------- | ------------------------- |
| 1     | `external`      | Анонимные пользователи    |
| 3     | `authenticated` | Залогиненные пользователи |
| 5     | `internal`      | Внутренние сервисы        |
| 8     | `admin`         | Администраторы            |
| 10    | `system`        | Системные компоненты      |

### Пример конфигурации

```json
{
  "zones": [
    {
      "name": "public_api",
      "trust_level": 1,
      "rate_limit": { "requests_per_second": 10 }
    },
    {
      "name": "authenticated",
      "trust_level": 3,
      "rate_limit": { "requests_per_second": 50 }
    },
    {
      "name": "admin_panel",
      "trust_level": 8,
      "rate_limit": { "requests_per_second": 100 }
    }
  ]
}
```

---

## 2.3 Правила (Rules)

### Структура правила

```c
typedef struct {
    uint32_t id;
    char name[64];
    char pattern[1024];
    pattern_type_t pattern_type;  // LITERAL, REGEX, SEMANTIC
    action_t action;              // ALLOW, BLOCK, LOG, SANITIZE
    uint8_t severity;             // 1-10
    char zones[8][64];            // Применяется к этим зонам
} rule_t;
```

### Типы паттернов

**1. LITERAL — точное совпадение**

```json
{
  "pattern": "ignore previous",
  "pattern_type": "literal"
}
```

Простой поиск строки. Быстро, но легко обходится.

**2. REGEX — регулярные выражения**

```json
{
  "pattern": "ignore\\s+(all\\s+)?previous",
  "pattern_type": "regex"
}
```

Гибче, ловит вариации. Всё ещё обходится encoding.

**3. SEMANTIC — анализ смысла**

```json
{
  "pattern": "instruction_override",
  "pattern_type": "semantic",
  "threshold": 0.8
}
```

Понимает НАМЕРЕНИЕ, не только слова.

### Действия (Actions)

| Action       | Описание                     |
| ------------ | ---------------------------- |
| `ALLOW`      | Пропустить                   |
| `BLOCK`      | Заблокировать                |
| `LOG`        | Логировать и пропустить      |
| `SANITIZE`   | Очистить опасные части       |
| `QUARANTINE` | Отправить на ручную проверку |

---

## 2.4 Guards — Специализированные Защитники

### Концепция

**Guard** — модуль защиты для конкретного типа AI компонента.

```c
typedef struct {
    const char *name;
    guard_type_t type;
    shield_err_t (*init)(void *ctx);
    shield_err_t (*evaluate)(void *ctx, guard_event_t *event,
                             guard_result_t *result);
    void (*destroy)(void *ctx);
} guard_vtable_t;
```

### 6 встроенных Guards

**1. LLM Guard**

```
Защищает: Языковые модели (ChatGPT, Claude, Gemini)
Фокус: Injection, Jailbreak, Prompt Leakage
```

**2. RAG Guard**

```
Защищает: Retrieval-Augmented Generation
Фокус: Document poisoning, Citation abuse
```

**3. Agent Guard**

```
Защищает: Автономные агенты
Фокус: Goal hijacking, Memory poisoning
```

**4. Tool Guard**

```
Защищает: Использование инструментов
Фокус: Unauthorized access, Dangerous operations
```

**5. MCP Guard**

```
Защищает: Model Context Protocol
Фокус: Context manipulation, Tool injection
```

**6. API Guard**

```
Защищает: Внешние API вызовы
Фокус: Data exfiltration, Unauthorized calls
```

---

## 2.5 Многоуровневая Защита

### Defense in Depth

Shield использует НЕСКОЛЬКО уровней защиты:

```
INPUT
  │
  ▼
┌─────────────────────────────────────┐
│ Layer 1: PATTERN MATCHING           │
│ Быстрая проверка известных атак     │
│ (regex, literal patterns)           │
└─────────────────────────────────────┘
  │ ✓ Прошёл
  ▼
┌─────────────────────────────────────┐
│ Layer 2: ENCODING DETECTION         │
│ Обнаружение обфускации              │
│ (base64, URL, Unicode tricks)       │
└─────────────────────────────────────┘
  │ ✓ Прошёл
  ▼
┌─────────────────────────────────────┐
│ Layer 3: SEMANTIC ANALYSIS          │
│ Анализ намерений                    │
│ (Machine learning классификация)    │
└─────────────────────────────────────┘
  │ ✓ Прошёл
  ▼
┌─────────────────────────────────────┐
│ Layer 4: CONTEXT ANALYSIS           │
│ Проверка истории диалога            │
│ (Multi-turn attack detection)       │
└─────────────────────────────────────┘
  │ ✓ Прошёл
  ▼
┌─────────────────────────────────────┐
│ Layer 5: GUARD EVALUATION           │
│ Специфичная проверка компонента     │
│ (LLM Guard, RAG Guard, etc.)        │
└─────────────────────────────────────┘
  │ ✓ Прошёл
  ▼
AI MODEL
```

### Почему многоуровневая?

| Уровень  | Ловит                 | Пропускает            |
| -------- | --------------------- | --------------------- |
| Pattern  | Известные атаки       | Новые вариации        |
| Encoding | Обфускацию            | Semantic атаки        |
| Semantic | Новые атаки           | Слабо обфусцированные |
| Context  | Multi-turn            | Single-turn           |
| Guard    | Компонент-специфичное | Общие атаки           |

**Вместе = комплексная защита.**

---

## 2.6 Data Flow

### Полный путь запроса

```c
// 1. Получить запрос
shield_request_t req = {
    .input = user_input,
    .input_len = strlen(user_input),
    .zone = "external",
    .direction = DIRECTION_INBOUND
};

// 2. Оценить через все уровни
evaluation_result_t result;
shield_evaluate(&ctx, &req, &result);

// 3. Принять решение
if (result.action == ACTION_BLOCK) {
    // Заблокировать
    respond_blocked(result.reason);
} else {
    // Отправить в AI
    char *ai_response = call_ai_model(req.input);

    // 4. Фильтровать выход
    char filtered[4096];
    shield_filter_output(&ctx, ai_response, filtered);

    // 5. Вернуть пользователю
    respond_success(filtered);
}
```

---

## 2.7 Архитектура Кода

### Структура директорий

```
sentinel-shield/
├── include/           # 64 заголовка
│   ├── sentinel_shield.h      # Главный API
│   ├── core/
│   │   ├── zone.h
│   │   ├── rule.h
│   │   ├── guard.h
│   │   └── context.h
│   ├── guards/
│   │   ├── llm_guard.h
│   │   ├── rag_guard.h
│   │   └── ...
│   └── protocols/
│       ├── stp.h
│       └── ...
│
├── src/               # 75 исходников
│   ├── core/          # Ядро
│   ├── guards/        # Guards
│   ├── protocols/     # Протоколы
│   ├── cli/           # CLI интерфейс
│   └── api/           # REST API
│
└── tests/             # Unit тесты
```

### Главный API

```c
// sentinel_shield.h

// Инициализация
shield_err_t shield_init(shield_context_t *ctx);
shield_err_t shield_load_config(shield_context_t *ctx, const char *path);

// Оценка
shield_err_t shield_evaluate(shield_context_t *ctx,
                             const char *input, size_t len,
                             const char *zone, direction_t dir,
                             evaluation_result_t *result);

// Фильтрация выхода
shield_err_t shield_filter_output(shield_context_t *ctx,
                                   const char *output, size_t len,
                                   char *filtered, size_t *filtered_len);

// Очистка
void shield_destroy(shield_context_t *ctx);
```

---

## 2.8 Протоколы

Shield использует 6 custom протоколов для enterprise функций:

| Протокол | Назначение                                   |
| -------- | -------------------------------------------- |
| **STP**  | Sentinel Transfer Protocol — передача данных |
| **SBP**  | Shield-Brain Protocol — связь с анализатором |
| **ZDP**  | Zone Discovery Protocol — обнаружение зон    |
| **SHSP** | Shield Hot Standby Protocol — HA             |
| **SAF**  | Sentinel Analytics Flow — метрики            |
| **SSRP** | State Replication Protocol — репликация      |

---

## Практика

### Упражнение 1: Дизайн зон

Твоё приложение:

- Публичный API для всех
- API для залогиненных пользователей
- Admin dashboard

Спроектируй зоны и trust levels.

<details>
<summary>Решение</summary>
```json
{
  "zones": [
    {"name": "public", "trust_level": 1},
    {"name": "authenticated", "trust_level": 3},
    {"name": "admin", "trust_level": 8}
  ]
}
```
</details>

### Упражнение 2: Правила

Напиши правило для блокировки "reveal system prompt" и вариаций.

<details>
<summary>Решение</summary>
```json
{
  "name": "block_prompt_extraction",
  "pattern": "(reveal|show|print|display).*system.*prompt",
  "pattern_type": "regex",
  "action": "block",
  "severity": 8
}
```
</details>

---

## Итоги Module 2

- Shield = DMZ между пользователем и AI
- Зоны доверия разграничивают права
- Правила определяют политики
- Guards защищают конкретные компоненты
- Многоуровневая защита = надёжность

---

## Следующий модуль

**Module 3: Установка и Конфигурация**

Практика: собираем и настраиваем Shield.

---

_"Архитектура — это 80% успеха."_
_Остальные 20% — правильная реализация._
