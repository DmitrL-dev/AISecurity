# Модуль 21: Shield State — Global State Manager

## Обзор

`shield_state_t` — это глобальный менеджер состояния SENTINEL Shield. Он обеспечивает единый источник правды для всей конфигурации и runtime-состояния системы, а также персистентность между перезагрузками.

---

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                      shield_state_t                          │
│                       (singleton)                            │
├─────────────────┬─────────────────┬─────────────────────────┤
│   Module States │    Config       │    Statistics           │
├─────────────────┼─────────────────┼─────────────────────────┤
│ threat_hunter   │  system_config  │  requests_total         │
│ watchdog        │  debug_state    │  blocked_total          │
│ cognitive       │  ha_config      │  allowed_total          │
│ pqc             │  api_state      │  uptime_seconds         │
│ guards (6)      │                 │                         │
│ rate_limit      │                 │                         │
│ blocklist       │                 │                         │
│ siem            │                 │                         │
│ brain           │                 │                         │
└─────────────────┴─────────────────┴─────────────────────────┘
```

---

## Ключевые структуры

### shield_state_t

```c
typedef struct shield_state {
    // Module states
    threat_hunter_state_t  threat_hunter;
    watchdog_state_t       watchdog;
    cognitive_state_t      cognitive;
    pqc_state_t           pqc;
    guards_state_t         guards;
    
    // Network/Enterprise
    rate_limit_state_t     rate_limit;
    blocklist_state_t      blocklist;
    siem_state_t          siem;
    brain_state_t         brain;
    
    // Configuration
    system_config_t        system;
    debug_state_t         debug;
    ha_config_t           ha;
    api_state_t           api;
    
    // Metadata
    time_t                last_modified;
    bool                  dirty;
    char                  config_path[256];
} shield_state_t;
```

### module_state_t (универсальный)

```c
typedef enum module_state {
    MODULE_DISABLED = 0,
    MODULE_ENABLED  = 1,
    MODULE_ERROR    = 2,
    MODULE_INIT     = 3
} module_state_t;
```

---

## API Shield State

### Доступ (Singleton)

```c
#include "shield_state.h"

// Получить глобальное состояние
shield_state_t* shield_state_get(void);
```

### Жизненный цикл

```c
// Инициализация с умолчаниями
shield_err_t shield_state_init(void);

// Сброс к умолчаниям
void shield_state_reset(void);
```

### Персистентность

```c
// Сохранить в файл (INI формат)
shield_err_t shield_state_save(const char *filepath);

// Загрузить из файла
shield_err_t shield_state_load(const char *filepath);

// Отметить как изменённое
void shield_state_mark_dirty(void);

// Проверить, есть ли несохранённые изменения
bool shield_state_is_dirty(void);
```

### Статистика

```c
// Инкремент счётчиков
void shield_state_inc_requests(void);
void shield_state_inc_blocked(void);
void shield_state_inc_allowed(void);

// Форматированный вывод
void shield_state_format_summary(char *buf, size_t buflen);
```

---

## Формат конфигурации (INI)

```ini
# shield.conf

[system]
log_level=info
max_connections=1000
timezone=UTC

[threat_hunter]
enabled=true
sensitivity=0.70
hunt_ioc=true
hunt_behavioral=true
hunt_anomaly=true

[watchdog]
enabled=true
auto_recovery=true
check_interval_ms=5000

[cognitive]
enabled=true

[pqc]
enabled=true

[guards]
llm=enabled
rag=enabled
agent=enabled
tool=enabled
mcp=enabled
api=enabled

[rate_limit]
enabled=true
max_requests=1000
window_seconds=60

[blocklist]
enabled=true
auto_block_threshold=5

[siem]
enabled=false
endpoint=

[brain]
enabled=true
url=http://localhost:8000
timeout_ms=5000

[ha]
enabled=false
mode=standalone
peer_url=

[api]
enabled=true
port=8080
auth_required=true
```

---

## CLI Интеграция

Все CLI команды используют `shield_state_t`:

```c
// Пример: cmd_threat_hunter_enable
int cmd_threat_hunter_enable(cli_context_t *ctx, int argc, char **argv) {
    shield_state_t *state = shield_state_get();
    
    state->threat_hunter.state = MODULE_ENABLED;
    shield_state_mark_dirty();  // Отметить для сохранения
    
    cli_out(ctx, "ThreatHunter enabled\n");
    return 0;
}
```

```
sentinel# configure terminal
sentinel(config)# threat-hunter enable
ThreatHunter enabled

sentinel(config)# end
sentinel# write memory
Building configuration...
Configuration saved to shield.conf
[OK]
```

---

## Dual Sync Pattern (Guards)

Guards имеют двойную синхронизацию:

```c
// cmd_guard_enable
int cmd_guard_enable(cli_context_t *ctx, int argc, char **argv) {
    shield_state_t *state = shield_state_get();
    
    // 1. Обновить ctx (для немедленного эффекта)
    ctx->guards.llm = true;
    
    // 2. Обновить shield_state (для персистентности)
    state->guards.llm.state = MODULE_ENABLED;
    
    shield_state_mark_dirty();
    return 0;
}
```

---

## Лабораторная работа LAB-210

### Цель
Понять работу Global State Manager.

### Задание 1: Изменение состояния
```bash
sentinel# configure terminal
sentinel(config)# threat-hunter enable
sentinel(config)# watchdog enable
sentinel(config)# pqc enable
sentinel(config)# end
```

### Задание 2: Просмотр состояния
```bash
sentinel# show running-config
```

### Задание 3: Сохранение
```bash
sentinel# write memory
# или
sentinel# copy running-config startup-config
```

### Задание 4: Перезагрузка и проверка
```bash
sentinel# reload
# После перезагрузки:
sentinel# show threat-hunter
# ThreatHunter должен быть enabled
```

---

## Вопросы для самопроверки

1. Что такое singleton pattern в shield_state_t?
2. Зачем нужен флаг `dirty`?
3. Когда вызывается shield_state_save()?
4. Что такое Dual Sync Pattern?
5. В каком формате хранится конфигурация?

---

## Следующий модуль

→ [Модуль 22: Advanced CLI — 199 команд](MODULE_22_CLI_ADVANCED.md)
