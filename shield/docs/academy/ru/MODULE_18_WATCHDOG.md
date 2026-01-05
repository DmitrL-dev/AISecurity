# Модуль 18: Watchdog — Self-Healing System

## Обзор

Watchdog — это система мониторинга здоровья и автоматического восстановления в SENTINEL Shield. Она постоянно следит за состоянием всех компонентов системы и автоматически реагирует на проблемы.

---

## Архитектура Watchdog

```
┌─────────────────────────────────────────────────────────┐
│                      Watchdog                            │
├───────────────┬──────────────────┬──────────────────────┤
│   Monitoring  │   Health Check   │   Auto-Recovery      │
├───────────────┼──────────────────┼──────────────────────┤
│ • Guards (6)  │  • CPU Usage     │  • Restart           │
│ • Memory      │  • Memory        │  • Reinitialize      │
│ • Connections │  • Latency       │  • Failover          │
│ • State       │  • Error Rate    │  • Alert             │
└───────────────┴──────────────────┴──────────────────────┘
```

---

## Компоненты мониторинга

### 1. Guard Monitoring

Watchdog следит за всеми 6 Guards:

| Guard | Метрики | Threshold |
|-------|---------|-----------|
| LLM Guard | checks/s, errors | >5% error rate |
| RAG Guard | latency, blocks | >100ms latency |
| Agent Guard | sessions, alerts | >10 alerts/min |
| Tool Guard | calls, denials | >20% denial rate |
| MCP Guard | connections | >80% capacity |
| API Guard | requests, 4xx/5xx | >10% error rate |

### 2. Memory Subsystem

- Heap usage tracking
- Memory pool utilization
- Leak detection
- Fragmentation monitoring

### 3. System Health

- Overall health score (0.0 - 1.0)
- Component-level health
- Trend analysis
- Predictive alerts

---

## Alert Escalation

Watchdog использует 4-уровневую систему эскалации:

```
┌────────────────────────────────────────────────────────┐
│  CRITICAL  │ Immediate action required, system at risk │
├────────────┼───────────────────────────────────────────┤
│   ERROR    │ Component failure, degraded service       │
├────────────┼───────────────────────────────────────────┤
│  WARNING   │ Approaching threshold, attention needed   │
├────────────┼───────────────────────────────────────────┤
│   INFO     │ Normal operation, status update           │
└────────────┴───────────────────────────────────────────┘
```

**Автоматические действия:**
- **INFO** → Log only
- **WARNING** → Log + Metric increment
- **ERROR** → Log + Alert + Auto-recovery attempt
- **CRITICAL** → Log + Alert + Escalate + Possible failover

---

## API Watchdog

### Инициализация

```c
#include "shield_watchdog.h"

// Инициализация
shield_err_t shield_watchdog_init(void);

// Освобождение ресурсов
void shield_watchdog_destroy(void);
```

### Настройка

```c
// Включить/отключить auto-recovery
void shield_watchdog_set_auto_recovery(bool enable);

// Установить интервал проверки (ms)
void shield_watchdog_set_interval(uint32_t ms);
```

### Проверка здоровья

```c
// Проверить все компоненты
shield_err_t shield_watchdog_check_all(void);

// Получить общий health score
float shield_watchdog_get_system_health(void);

// Получить статус компонента
component_health_t shield_watchdog_get_component(const char *name);
```

### Результат проверки

```c
typedef struct component_health {
    char            name[64];
    health_status_t status;      // HEALTHY, DEGRADED, UNHEALTHY
    float           score;       // 0.0 - 1.0
    uint64_t        last_check;
    char            message[128];
} component_health_t;
```

---

## CLI Команды Watchdog

```
sentinel# show watchdog
Watchdog Status
===============
State:         ENABLED
Auto-Recovery: yes
Check Interval: 5000 ms
System Health: 95%

Statistics:
  Checks Total:    12456
  Alerts Raised:   23
  Recoveries:      5

sentinel(config)# watchdog enable
Watchdog enabled

sentinel(config)# watchdog auto-recovery enable
Watchdog auto-recovery enabled

sentinel# watchdog check
Running health check...
Health Check Complete
=====================
System Health: 95%
Status: HEALTHY
```

---

## Интеграция с shield_state_t

```c
typedef struct watchdog_state {
    module_state_t state;              // ENABLED/DISABLED
    bool           auto_recovery;
    uint32_t       check_interval_ms;
    float          system_health;      // 0.0 - 1.0
    time_t         last_check;
    uint64_t       checks_total;
    uint64_t       alerts_raised;
    uint64_t       recoveries_attempted;
} watchdog_state_t;
```

Конфигурация в `shield.conf`:
```ini
[watchdog]
enabled=true
auto_recovery=true
check_interval_ms=5000
```

---

## Auto-Recovery Strategies

### 1. Guard Recovery
```c
// При ошибке Guard:
1. Log error
2. Increment error counter
3. If error_rate > threshold:
   a. Disable guard temporarily
   b. Reinitialize guard
   c. Re-enable guard
   d. Monitor for 60 seconds
```

### 2. Memory Recovery
```c
// При высоком использовании памяти:
1. Log warning
2. Run garbage collection on pools
3. Evict old sessions
4. Clear caches
5. If still high: alert CRITICAL
```

### 3. Connection Recovery
```c
// При потере соединения с Brain:
1. Try reconnect (3 attempts)
2. If failed: switch to local-only mode
3. Alert operator
4. Continue monitoring
```

---

## Лабораторная работа LAB-180

### Цель
Настроить Watchdog для мониторинга и автоматического восстановления.

### Задание 1: Включение Watchdog
```bash
sentinel> enable
sentinel# configure terminal
sentinel(config)# watchdog enable
sentinel(config)# watchdog auto-recovery enable
sentinel(config)# end
sentinel# show watchdog
```

### Задание 2: Проверка здоровья
```bash
sentinel# watchdog check
```

**Ожидаемый результат:** System Health >= 80%

### Задание 3: Симуляция проблемы
```bash
# Отключить guard
sentinel(config)# no guard enable llm

# Проверить здоровье
sentinel# watchdog check
# Health должен упасть

# Включить обратно
sentinel(config)# guard enable llm
sentinel# watchdog check
# Health должен восстановиться
```

---

## Вопросы для самопроверки

1. Какие компоненты мониторит Watchdog?
2. Что происходит при CRITICAL alert?
3. Как Watchdog восстанавливает failed Guard?
4. Что означает System Health 0.75?
5. Зачем нужен check_interval_ms?

---

## Следующий модуль

→ [Модуль 19: Cognitive Signatures](MODULE_19_COGNITIVE.md)
