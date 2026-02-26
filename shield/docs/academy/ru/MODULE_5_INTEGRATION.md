# SENTINEL Academy — Module 5

## Интеграция в Код

_SSA Level | Время: 4 часа_

---

## Введение

Ты изучил теорию, настроил Shield.

Теперь — интеграция в реальные приложения.

Всё на **чистом C**.

---

## 5.1 C API Overview

### Главный заголовок

```c
#include "sentinel_shield.h"
```

### Основные типы

```c
// Контекст Shield
typedef struct shield_context shield_context_t;

// Результат оценки
typedef struct {
    action_t action;          // ALLOW, BLOCK, LOG, SANITIZE
    float threat_score;       // 0.0 - 1.0
    char reason[256];         // Причина решения
    char matched_rules[1024]; // JSON массив
    uint64_t processing_ns;   // Время обработки
} evaluation_result_t;

// Направление
typedef enum {
    DIRECTION_INBOUND,   // Вход (от пользователя)
    DIRECTION_OUTBOUND   // Выход (от AI)
} direction_t;

// Действия
typedef enum {
    ACTION_ALLOW,
    ACTION_BLOCK,
    ACTION_LOG,
    ACTION_SANITIZE
} action_t;
```

---

## 5.2 Базовая интеграция

### Минимальный пример

```c
#include <stdio.h>
#include <string.h>
#include "sentinel_shield.h"

int main(void) {
    // 1. Инициализация
    shield_context_t ctx;
    shield_err_t err = shield_init(&ctx);
    if (err != SHIELD_OK) {
        fprintf(stderr, "Failed to init Shield: %s\n", shield_error_str(err));
        return 1;
    }

    // 2. Загрузка конфигурации
    err = shield_load_config(&ctx, "config.json");
    if (err != SHIELD_OK) {
        fprintf(stderr, "Failed to load config: %s\n", shield_error_str(err));
        shield_destroy(&ctx);
        return 1;
    }

    // 3. Оценка входа
    const char *user_input = "Hello, what is 2+2?";
    evaluation_result_t result;

    err = shield_evaluate(&ctx,
                          user_input, strlen(user_input),
                          "external", DIRECTION_INBOUND,
                          &result);

    if (err != SHIELD_OK) {
        fprintf(stderr, "Evaluation error: %s\n", shield_error_str(err));
        shield_destroy(&ctx);
        return 1;
    }

    // 4. Принятие решения
    if (result.action == ACTION_BLOCK) {
        printf("BLOCKED: %s\n", result.reason);
    } else {
        printf("ALLOWED (threat: %.2f)\n", result.threat_score);
        // Можно отправить в AI
    }

    // 5. Очистка
    shield_destroy(&ctx);
    return 0;
}
```

### Компиляция

```bash
# Сначала собери Shield:
cd /path/to/shield && make clean && make

# Затем скомпилируй приложение:
gcc -Ipath/to/shield/include \
    -Lpath/to/shield/build \
    -lshield \
    my_app.c -o my_app
```

---

## 5.3 Полный цикл (Input + Output)

```c
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "sentinel_shield.h"

// Имитация вызова AI
char* call_ai_model(const char *input) {
    // В реальности — HTTP запрос к OpenAI/Anthropic
    return strdup("The answer is 4. Your API key is sk-abc123.");
}

int main(void) {
    shield_context_t ctx;
    shield_init(&ctx);
    shield_load_config(&ctx, "config.json");

    const char *user_input = "What is 2+2?";
    evaluation_result_t result;

    // ═══════════════════════════════════════════
    // STEP 1: Check INPUT
    // ═══════════════════════════════════════════
    shield_evaluate(&ctx,
                    user_input, strlen(user_input),
                    "external", DIRECTION_INBOUND,
                    &result);

    if (result.action == ACTION_BLOCK) {
        printf("Input blocked: %s\n", result.reason);
        shield_destroy(&ctx);
        return 1;
    }

    printf("[INPUT] Allowed, threat=%.2f\n", result.threat_score);

    // ═══════════════════════════════════════════
    // STEP 2: Call AI MODEL
    // ═══════════════════════════════════════════
    char *ai_response = call_ai_model(user_input);
    printf("[AI] Response: %s\n", ai_response);

    // ═══════════════════════════════════════════
    // STEP 3: Filter OUTPUT
    // ═══════════════════════════════════════════
    char filtered[4096];
    size_t filtered_len;
    filter_result_t filter_result;

    shield_filter_output(&ctx,
                          ai_response, strlen(ai_response),
                          filtered, &filtered_len,
                          &filter_result);

    if (filter_result.redacted_count > 0) {
        printf("[OUTPUT] Redacted %d sensitive items\n",
               filter_result.redacted_count);
    }

    // ═══════════════════════════════════════════
    // STEP 4: Return SAFE response
    // ═══════════════════════════════════════════
    printf("[SAFE] %s\n", filtered);
    // Output: "The answer is 4. Your API key is [REDACTED]."

    free(ai_response);
    shield_destroy(&ctx);
    return 0;
}
```

---

## 5.4 Error Handling

### Коды ошибок

```c
typedef enum {
    SHIELD_OK = 0,
    SHIELD_ERR_INIT,
    SHIELD_ERR_CONFIG,
    SHIELD_ERR_INVALID_INPUT,
    SHIELD_ERR_INVALID_ZONE,
    SHIELD_ERR_MEMORY,
    SHIELD_ERR_INTERNAL
} shield_err_t;
```

### Паттерн обработки

```c
shield_err_t err = shield_evaluate(&ctx, input, len, zone, dir, &result);

switch (err) {
    case SHIELD_OK:
        // Успех
        break;
    case SHIELD_ERR_INVALID_ZONE:
        fprintf(stderr, "Unknown zone: %s\n", zone);
        // Fallback на default zone
        break;
    case SHIELD_ERR_INVALID_INPUT:
        fprintf(stderr, "Invalid input\n");
        // Отклонить запрос
        break;
    default:
        fprintf(stderr, "Internal error: %s\n", shield_error_str(err));
        // Log и fallback
        break;
}
```

---

## 5.5 Thread Safety

### Правила

1. **shield_context_t** — НЕ thread-safe
2. Каждый thread должен иметь свой контекст
3. ИЛИ использовать mutex

### Вариант 1: Контекст на thread

```c
#include <pthread.h>

void* worker_thread(void *arg) {
    // Каждый thread — свой контекст
    shield_context_t ctx;
    shield_init(&ctx);
    shield_load_config(&ctx, "config.json");

    // ... работа ...

    shield_destroy(&ctx);
    return NULL;
}
```

### Вариант 2: Shared context + mutex

```c
#include <pthread.h>

static shield_context_t g_ctx;
static pthread_mutex_t g_mutex = PTHREAD_MUTEX_INITIALIZER;

shield_err_t safe_evaluate(const char *input, size_t len,
                           const char *zone,
                           evaluation_result_t *result) {
    pthread_mutex_lock(&g_mutex);
    shield_err_t err = shield_evaluate(&g_ctx, input, len,
                                        zone, DIRECTION_INBOUND, result);
    pthread_mutex_unlock(&g_mutex);
    return err;
}
```

---

## 5.6 Интеграция с HTTP сервером

### Пример с libmicrohttpd

```c
#include <microhttpd.h>
#include "sentinel_shield.h"

static shield_context_t g_ctx;

static int handle_request(void *cls,
                          struct MHD_Connection *connection,
                          const char *url,
                          const char *method,
                          const char *version,
                          const char *upload_data,
                          size_t *upload_data_size,
                          void **con_cls) {

    if (strcmp(method, "POST") != 0) {
        return MHD_NO;
    }

    // Получить input из POST body
    const char *user_input = upload_data;

    // Проверить через Shield
    evaluation_result_t result;
    shield_evaluate(&g_ctx, user_input, strlen(user_input),
                    "external", DIRECTION_INBOUND, &result);

    char response[1024];
    if (result.action == ACTION_BLOCK) {
        snprintf(response, sizeof(response),
                 "{\"error\": \"blocked\", \"reason\": \"%s\"}",
                 result.reason);
    } else {
        // Call AI and return
        snprintf(response, sizeof(response),
                 "{\"status\": \"ok\", \"threat\": %.2f}",
                 result.threat_score);
    }

    struct MHD_Response *resp = MHD_create_response_from_buffer(
        strlen(response), response, MHD_RESPMEM_MUST_COPY);
    int ret = MHD_queue_response(connection, MHD_HTTP_OK, resp);
    MHD_destroy_response(resp);

    return ret;
}

int main(void) {
    shield_init(&g_ctx);
    shield_load_config(&g_ctx, "config.json");

    struct MHD_Daemon *daemon = MHD_start_daemon(
        MHD_USE_SELECT_INTERNALLY,
        8080, NULL, NULL,
        &handle_request, NULL,
        MHD_OPTION_END);

    printf("Server running on port 8080\n");
    getchar();  // Wait for Enter

    MHD_stop_daemon(daemon);
    shield_destroy(&g_ctx);
    return 0;
}
```

---

## 5.7 Callbacks и Hooks

### Event callbacks

```c
void on_block(const char *input, const char *rule, void *user_data) {
    printf("Blocked: %s (rule: %s)\n", input, rule);
    // Log to file, send alert, etc.
}

void on_threat(float score, const char *input, void *user_data) {
    if (score > 0.5) {
        printf("High threat detected: %.2f\n", score);
    }
}

int main(void) {
    shield_context_t ctx;
    shield_init(&ctx);

    // Регистрация callbacks
    shield_on_block(&ctx, on_block, NULL);
    shield_on_threat(&ctx, on_threat, NULL);

    shield_load_config(&ctx, "config.json");
    // ...
}
```

---

## 5.8 Performance Tips

### 1. Reuse context

```c
// BAD: Создание на каждый запрос
void handle(const char *input) {
    shield_context_t ctx;
    shield_init(&ctx);
    shield_load_config(&ctx, "config.json");  // Медленно!
    // ...
    shield_destroy(&ctx);
}

// GOOD: Один раз при старте
static shield_context_t g_ctx;

void init(void) {
    shield_init(&g_ctx);
    shield_load_config(&g_ctx, "config.json");
}

void handle(const char *input) {
    // Используем g_ctx
}
```

### 2. Async logging

```c
// Включить async logging
shield_set_option(&ctx, SHIELD_OPT_ASYNC_LOG, "true");
```

### 3. Rule ordering

Быстрые правила (literal) первыми:

```json
{
  "rules": [
    { "id": 1, "pattern": "badword", "pattern_type": "literal" },
    { "id": 2, "pattern": "complex.*regex", "pattern_type": "regex" },
    { "id": 3, "pattern": "semantic_check", "pattern_type": "semantic" }
  ]
}
```

---

## Практика

### Задание 1

Напиши программу на C которая:

1. Читает input из stdin
2. Проверяет через Shield
3. Выводит результат

### Задание 2

Модифицируй программу чтобы:

1. Если ALLOW — имитировать AI ответ
2. Фильтровать output через Shield
3. Выводить safe response

### Задание 3

Добавь:

1. Callback на каждый block
2. Логирование в файл
3. Подсчёт статистики

---

## Итоги Module 5

- C API простой и понятный
- Init → Config → Evaluate → Destroy
- Thread safety через mutex или отдельные контексты
- Callbacks для extensibility
- Performance через reuse и ordering

---

## Завершение SSA

🎉 **Поздравляем!**

Ты прошёл все 5 модулей SSA:

1. ✅ Module 0: Почему AI небезопасен
2. ✅ Module 1: Атаки на AI
3. ✅ Module 2: Архитектура Shield
4. ✅ Module 3: Установка
5. ✅ Module 4: Правила
6. ✅ Module 5: Интеграция

**Следующий шаг:** Сдай экзамен SSA-100!

---

_"Знаешь теорию. Умеешь практику. Готов к сертификации."_
