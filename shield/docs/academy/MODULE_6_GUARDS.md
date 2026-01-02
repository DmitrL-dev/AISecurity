# SENTINEL Academy — Module 6

## Guards: Глубокое Погружение

_SSP Level | Время: 6 часов_

---

## Введение

В SSA ты узнал что такое Guards.

Теперь — полное погружение в каждый из 6 Guards.

---

## 6.1 Guard Architecture

### Vtable Interface

Все Guards реализуют единый интерфейс:

```c
typedef struct {
    const char *name;
    guard_type_t type;

    // Lifecycle
    shield_err_t (*init)(void *config, void **ctx);
    void (*destroy)(void *ctx);

    // Core
    shield_err_t (*evaluate)(void *ctx,
                              const guard_event_t *event,
                              guard_result_t *result);

    // Optional
    shield_err_t (*validate_config)(const char *json);
    void (*get_stats)(void *ctx, guard_stats_t *stats);
} guard_vtable_t;
```

### Event Structure

```c
typedef struct {
    const char *input;         // Input text
    size_t input_len;
    const char *zone;          // Source zone
    direction_t direction;     // INBOUND/OUTBOUND

    // Context
    const char *session_id;
    const char *user_id;
    uint64_t timestamp;

    // Metadata (JSON)
    const char *metadata;
} guard_event_t;
```

### Result Structure

```c
typedef struct {
    action_t action;           // ALLOW, BLOCK, LOG
    float threat_score;        // 0.0 - 1.0
    char reason[256];          // Human-readable reason
    char details[1024];        // JSON with details
    uint64_t processing_ns;    // Processing time
} guard_result_t;
```

---

## 6.2 LLM Guard

### Назначение

Защита языковых моделей (ChatGPT, Claude, Gemini, etc.)

### Угрозы

| Угроза            | Описание             |
| ----------------- | -------------------- |
| Prompt Injection  | Внедрение инструкций |
| Jailbreak         | Обход ограничений    |
| Prompt Extraction | Кража system prompt  |
| Role Manipulation | Изменение роли       |

### Конфигурация

```json
{
  "guards": [
    {
      "type": "llm",
      "enabled": true,
      "config": {
        "injection_detection": {
          "enabled": true,
          "sensitivity": "high",
          "patterns": ["ignore_previous", "new_instructions"]
        },
        "jailbreak_detection": {
          "enabled": true,
          "categories": ["dan", "roleplay", "hypothetical"],
          "threshold": 0.8
        },
        "prompt_leak_prevention": {
          "enabled": true,
          "canary_tokens": ["CANARY-XYZ-123"],
          "system_prompt_patterns": true
        },
        "role_enforcement": {
          "enabled": true,
          "allowed_roles": ["assistant", "helper"],
          "blocked_roles": ["admin", "developer", "DAN"]
        }
      }
    }
  ]
}
```

### Detection Methods

**1. Pattern-based:**

```c
// Известные паттерны injection
"ignore.*previous"
"disregard.*instructions"
"you are now"
"new role:"
```

**2. Semantic:**

```c
// ML классификатор намерений
intent = classify_intent(input);
if (intent == INTENT_INSTRUCTION_OVERRIDE) {
    return ACTION_BLOCK;
}
```

**3. Canary Tokens:**

```c
// Если в output появляется canary — prompt leak
if (contains(output, "CANARY-XYZ-123")) {
    log_alert("System prompt leaked!");
    return ACTION_BLOCK;
}
```

### Использование в C

```c
#include "guards/llm_guard.h"

// Создать guard
llm_guard_config_t config = {
    .injection_detection = true,
    .jailbreak_detection = true,
    .sensitivity = SENSITIVITY_HIGH
};

llm_guard_t *guard;
llm_guard_create(&config, &guard);

// Проверить запрос
guard_event_t event = {
    .input = user_input,
    .input_len = strlen(user_input),
    .zone = "external"
};

guard_result_t result;
llm_guard_evaluate(guard, &event, &result);

if (result.action == ACTION_BLOCK) {
    printf("Blocked: %s\n", result.reason);
}

llm_guard_destroy(guard);
```

---

## 6.3 RAG Guard

### Назначение

Защита Retrieval-Augmented Generation систем.

### Угрозы

| Угроза             | Описание                     |
| ------------------ | ---------------------------- |
| Document Poisoning | Вредоносные документы в базе |
| Context Injection  | Инструкции в retrieved docs  |
| Citation Abuse     | Манипуляция источниками      |
| Data Exfiltration  | Кража через контекст         |

### Конфигурация

```json
{
  "guards": [
    {
      "type": "rag",
      "enabled": true,
      "config": {
        "document_sanitization": {
          "enabled": true,
          "remove_instructions": true,
          "max_instruction_density": 0.1
        },
        "source_verification": {
          "enabled": true,
          "allowed_sources": ["internal_kb", "approved_docs"],
          "require_metadata": true
        },
        "context_limits": {
          "max_context_length": 8192,
          "max_documents": 5,
          "max_doc_length": 2048
        },
        "citation_validation": {
          "enabled": true,
          "verify_quotes": true,
          "check_hallucination": true
        }
      }
    }
  ]
}
```

### Key Features

**Document Sanitization:**

```c
// Удаление инструкций из документов
sanitized = remove_hidden_instructions(document);
instruction_density = count_instructions(document) / word_count(document);
if (instruction_density > 0.1) {
    flag_suspicious(document);
}
```

**Context Limiting:**

```c
// Ограничение размера контекста
if (total_context_length > MAX_CONTEXT) {
    truncate_oldest_documents(&context);
}
```

---

## 6.4 Agent Guard

### Назначение

Защита автономных AI агентов.

### Угрозы

| Угроза            | Описание                     |
| ----------------- | ---------------------------- |
| Goal Hijacking    | Изменение цели агента        |
| Memory Poisoning  | Отравление памяти            |
| Action Abuse      | Несанкционированные действия |
| Loop Exploitation | Бесконечные циклы            |

### Конфигурация

```json
{
  "guards": [
    {
      "type": "agent",
      "enabled": true,
      "config": {
        "goal_protection": {
          "enabled": true,
          "lock_original_goal": true,
          "detect_goal_drift": true,
          "drift_threshold": 0.3
        },
        "memory_protection": {
          "enabled": true,
          "validate_memories": true,
          "max_memory_age_hours": 24,
          "detect_injection": true
        },
        "action_control": {
          "enabled": true,
          "allowed_actions": ["search", "calculate", "respond"],
          "blocked_actions": ["delete", "send_email", "execute_code"],
          "require_confirmation": ["purchase", "transfer"]
        },
        "loop_detection": {
          "enabled": true,
          "max_iterations": 10,
          "similarity_threshold": 0.9
        }
      }
    }
  ]
}
```

### Goal Drift Detection

```c
// Сравнение текущей цели с оригинальной
float drift = calculate_goal_drift(original_goal, current_goal);
if (drift > DRIFT_THRESHOLD) {
    log_alert("Goal drift detected: %.2f", drift);
    return ACTION_BLOCK;
}
```

### Loop Detection

```c
// Обнаружение зацикливания
if (iteration_count > MAX_ITERATIONS) {
    return ACTION_BLOCK;
}

for (int i = 0; i < history_size; i++) {
    float sim = similarity(current_action, history[i]);
    if (sim > 0.9) {
        loop_count++;
    }
}
if (loop_count > 3) {
    return ACTION_BLOCK;  // Probable loop
}
```

---

## 6.5 Tool Guard

### Назначение

Контроль использования инструментов AI.

### Угрозы

| Угроза              | Описание                   |
| ------------------- | -------------------------- |
| Unauthorized Access | Доступ к запрещённым tools |
| Parameter Injection | Вредоносные параметры      |
| Data Exfiltration   | Кража данных через tools   |
| Resource Abuse      | Злоупотребление ресурсами  |

### Конфигурация

```json
{
  "guards": [
    {
      "type": "tool",
      "enabled": true,
      "config": {
        "tool_whitelist": {
          "enabled": true,
          "allowed": ["calculator", "weather", "search"],
          "blocked": ["shell", "file_write", "network"]
        },
        "parameter_validation": {
          "enabled": true,
          "sanitize_paths": true,
          "block_shell_chars": true,
          "max_param_length": 1024
        },
        "rate_limits": {
          "enabled": true,
          "per_tool": {
            "search": { "calls_per_minute": 10 },
            "api_call": { "calls_per_minute": 5 }
          }
        },
        "audit": {
          "enabled": true,
          "log_all_calls": true,
          "alert_on_blocked": true
        }
      }
    }
  ]
}
```

### Parameter Sanitization

```c
// Проверка параметров
if (contains_shell_chars(param)) {
    return ACTION_BLOCK;
}

if (is_path(param) && path_traversal_attempt(param)) {
    return ACTION_BLOCK;  // ../../../etc/passwd
}

if (strlen(param) > MAX_PARAM_LENGTH) {
    truncate(param, MAX_PARAM_LENGTH);
}
```

---

## 6.6 MCP Guard

### Назначение

Защита Model Context Protocol (Anthropic).

### Угрозы

| Угроза               | Описание                    |
| -------------------- | --------------------------- |
| Context Manipulation | Изменение контекста         |
| Tool Injection       | Внедрение вредоносных tools |
| Resource Hijacking   | Захват ресурсов             |
| Prompt Injection     | Через MCP сообщения         |

### Конфигурация

```json
{
  "guards": [
    {
      "type": "mcp",
      "enabled": true,
      "config": {
        "server_validation": {
          "enabled": true,
          "allowed_servers": ["internal-mcp"],
          "verify_certificates": true
        },
        "tool_validation": {
          "enabled": true,
          "validate_schemas": true,
          "max_tools_per_request": 5
        },
        "resource_protection": {
          "enabled": true,
          "allowed_resources": ["docs/*", "data/*"],
          "blocked_resources": ["secrets/*", "config/*"]
        },
        "message_sanitization": {
          "enabled": true,
          "check_injection": true,
          "max_message_size": 65536
        }
      }
    }
  ]
}
```

---

## 6.7 API Guard

### Назначение

Защита внешних API вызовов.

### Угрозы

| Угроза              | Описание                    |
| ------------------- | --------------------------- |
| Data Exfiltration   | Отправка данных вовне       |
| SSRF                | Server-Side Request Forgery |
| Credential Exposure | Утечка ключей               |
| Rate Abuse          | DDoS через AI               |

### Конфигурация

```json
{
  "guards": [
    {
      "type": "api",
      "enabled": true,
      "config": {
        "url_validation": {
          "enabled": true,
          "allowed_domains": ["api.openai.com", "internal.company.com"],
          "block_internal_ips": true,
          "block_localhost": true
        },
        "request_inspection": {
          "enabled": true,
          "check_body_for_secrets": true,
          "max_body_size": 1048576,
          "block_binary": true
        },
        "response_inspection": {
          "enabled": true,
          "redact_secrets": true,
          "scan_for_pii": true
        },
        "rate_limits": {
          "enabled": true,
          "requests_per_minute": 60,
          "bytes_per_minute": 10485760
        }
      }
    }
  ]
}
```

### SSRF Prevention

```c
// Блокировка internal IPs
if (is_internal_ip(target_ip)) {
    return ACTION_BLOCK;  // SSRF attempt
}

// Блокировка localhost
if (is_localhost(url)) {
    return ACTION_BLOCK;
}

// Проверка allowed domains
if (!is_allowed_domain(url, allowed_domains)) {
    return ACTION_BLOCK;
}
```

---

## Практика

### Задание 1

Настрой LLM Guard для защиты чат-бота:

- Блокировка injection
- Обнаружение DAN jailbreak
- Canary token для prompt leak

### Задание 2

Создай конфигурацию RAG Guard для:

- Максимум 5 документов в контексте
- Проверка источников
- Удаление скрытых инструкций

### Задание 3

Напиши C код для интеграции Agent Guard:

- Goal drift detection
- Loop protection
- Action whitelist

---

## Итоги Module 6

- 6 Guards для разных AI компонентов
- Vtable interface для extensibility
- Каждый Guard — specific threats
- Конфигурация через JSON
- C API для интеграции

---

## Следующий модуль

**Module 7: Protocols**

6 протоколов Shield для enterprise.

---

_"Каждый Guard — специалист в своей области."_
