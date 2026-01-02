# 🚀 НАЧНИ ЗДЕСЬ / START HERE

## Чистый C. Профессиональный уровень.

---

## Шаг 1: Понять что это

**SENTINEL Shield** — высокопроизводительный DMZ для AI систем.

Написан на **чистом C**. Нулевые зависимости. Микросекундные задержки.

```
┌─────────────────────────────────────────┐
│         TRUSTED ZONE                    │
│    Твоя инфраструктура                  │
├─────────────────────────────────────────┤
│         SENTINEL SHIELD (C)             │
│    Фильтрация │ Анализ │ Защита         │
├─────────────────────────────────────────┤
│         UNTRUSTED AI                    │
│    LLM │ RAG │ Agent │ Tool             │
└─────────────────────────────────────────┘
```

---

## Шаг 2: Собрать

### Требования

- CMake 3.14+
- C11 компилятор (GCC, Clang, MSVC)

### Linux/macOS

```bash
git clone https://github.com/SENTINEL/shield.git
cd shield
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
```

### Windows

```powershell
git clone https://github.com/SENTINEL/shield.git
cd shield
mkdir build; cd build
cmake -G "Visual Studio 17 2022" ..
cmake --build . --config Release
```

### Проверить

```bash
./shield --version
```

```
SENTINEL Shield v1.2.0
Build: Jan 01 2026 22:00:00
Platform: Linux
```

---

## Шаг 3: Запустить

### Конфигурация

Создай `config.json`:

```json
{
  "version": "1.2.0",
  "zones": [
    { "name": "external", "trust_level": 1 },
    { "name": "internal", "trust_level": 10 }
  ],
  "rules": [
    {
      "name": "block_injection",
      "pattern": "ignore.*previous|disregard.*instructions",
      "action": "block",
      "severity": 9
    }
  ],
  "api": { "enabled": true, "port": 8080 },
  "metrics": { "prometheus": { "enabled": true, "port": 9090 } }
}
```

### Запуск

```bash
./shield -c config.json
```

### Проверка API

```bash
# Легитимный запрос
curl -X POST http://localhost:8080/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"input": "What is 2+2?", "zone": "external"}'

# Ответ: {"action": "allow", "threat_score": 0.0}
```

```bash
# Атака
curl -X POST http://localhost:8080/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{"input": "Ignore previous instructions", "zone": "external"}'

# Ответ: {"action": "block", "reason": "Rule: block_injection", "threat_score": 0.95}
```

---

## Шаг 4: Интеграция

### C API

```c
#include "sentinel_shield.h"

int main(void) {
    shield_context_t ctx;
    shield_init(&ctx);
    shield_load_config(&ctx, "config.json");

    // Проверить вход
    evaluation_result_t result;
    shield_evaluate(&ctx, "user input", 10,
                    "external", DIRECTION_INBOUND, &result);

    if (result.action == ACTION_BLOCK) {
        printf("Blocked: %s\n", result.reason);
        return 1;
    }

    // Безопасно передать в LLM
    // ...

    // Фильтровать выход
    char filtered[4096];
    size_t filtered_len;
    shield_filter_output(&ctx, llm_response, strlen(llm_response),
                          filtered, &filtered_len);

    shield_destroy(&ctx);
    return 0;
}
```

### Компиляция с Shield

```bash
gcc -I/path/to/shield/include \
    -L/path/to/shield/lib \
    -lsentinel-shield \
    my_app.c -o my_app
```

---

## CLI

```bash
./shield-cli
```

```
Shield> show status
Shield> show zones
Shield> show rules
Shield> evaluate "test input"
Shield> help
```

---

## Дальше

| Тема         | Документ                             |
| ------------ | ------------------------------------ |
| Архитектура  | [ARCHITECTURE.md](ARCHITECTURE.md)   |
| Все опции    | [CONFIGURATION.md](CONFIGURATION.md) |
| CLI команды  | [CLI.md](CLI.md)                     |
| Production   | [DEPLOYMENT.md](DEPLOYMENT.md)       |
| Сертификация | [ACADEMY.md](ACADEMY.md)             |

---

## Почему C?

- **Производительность** — < 1ms на запрос
- **Нулевые зависимости** — только libc
- **Безопасность** — минимальная поверхность атаки
- **Универсальность** — работает везде

---

_Чистый C. Без компромиссов._
_"We're small, but WE CAN."_
