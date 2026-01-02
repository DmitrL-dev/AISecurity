# SENTINEL Academy

## Образование в AI Security. Серьёзно.

---

## Философия

> **"Лёгкая дорога не всегда правильная."**

SENTINEL Academy — это не курсы "за 3 дня станешь экспертом".

Это систематическое образование в области AI Security:

- Глубокое понимание угроз
- Практические навыки защиты
- Профессиональная сертификация

Как Cisco Academy для сетей. Только для AI.

---

## Структура Сертификации

![SENTINEL Academy Certifications](images/certifications.png)

```
                    ┌─────────────────┐
                    │   SSE Expert    │  8 недель
                    │   Архитектор    │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
       ┌──────▼──────┐              ┌───────▼──────┐
       │    SRTS     │              │     SBTS     │
       │  Red Team   │              │  Blue Team   │
       │ Specialist  │              │  Specialist  │
       └─────────────┘              └──────────────┘
                             │
                    ┌────────▼────────┐
                    │  SSP Professional│ 4 недели
                    │   Инженер       │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   SSA Associate │  2 недели
                    │   Фундамент     │
                    └─────────────────┘
```

---

## Уровень 1: SSA (SENTINEL Shield Associate)

### Для кого

Начинающие разработчики и инженеры, которые хотят понять AI Security с нуля.

### Продолжительность

2 недели (40 часов)

### Что ты узнаешь

**Модуль 1.1: Почему AI уязвим**

- Как работают LLM на высоком уровне
- Почему традиционная безопасность не работает для AI
- Модель угроз AI систем

**Модуль 1.2: Атаки на AI**

- Prompt Injection — анатомия атаки
- Jailbreak — обход ограничений
- Data Extraction — кража данных через AI
- Prompt Leakage — утечка системного промпта

**Модуль 1.3: SENTINEL Shield — Основы**

- Архитектура DMZ для AI
- Зоны доверия (trust zones)
- Правила и действия
- Guards — специализированные защитники

**Модуль 1.4: Установка и Конфигурация**

- Сборка из исходников (cmake, make)
- Структура конфигурации JSON
- Запуск и проверка
- Использование API

**Модуль 1.5: Первая Защита**

- Создание зон
- Написание правил
- Тестирование через curl
- Интеграция в код (C)

### Лабораторные работы

| Lab     | Название             | Время  |
| ------- | -------------------- | ------ |
| LAB-101 | Установка Shield     | 30 мин |
| LAB-102 | Базовая Конфигурация | 45 мин |
| LAB-103 | Блокировка Injection | 30 мин |
| LAB-104 | Docker Deployment    | 30 мин |

### Экзамен SSA-100

- 60 вопросов
- 90 минут
- 70% для прохождения
- Теория + практические сценарии

---

## Уровень 2: SSP (SENTINEL Shield Professional)

### Для кого

Инженеры с опытом, ответственные за защиту AI систем в production.

### Предварительные требования

- SSA сертификация
- Опыт работы с C/C++
- Понимание сетевых протоколов

### Продолжительность

4 недели (80 часов)

### Что ты узнаешь

**Модуль 2.1: Глубокая Архитектура**

- Внутреннее устройство Shield
- Pattern Engine — как работает сопоставление
- Semantic Detector — анализ намерений
- Encoding Detector — обнаружение обфускации

**Модуль 2.2: Многоуровневая Защита**

- Layered defense strategy
- Комбинирование правил, guards и semantic analysis
- Обработка false positives

**Модуль 2.3: Guards — Глубокое Погружение**

- LLM Guard — защита языковых моделей
- RAG Guard — защита retrieval-augmented generation
- Agent Guard — защита автономных агентов
- Tool Guard — контроль tool use
- MCP Guard — защита Model Context Protocol
- API Guard — защита внешних API

**Модуль 2.4: Контекстное Управление**

- Multi-turn conversation security
- Token budget management
- Context poisoning prevention
- Eviction policies

**Модуль 2.5: Rate Limiting и Sessions**

- Защита от brute force
- Session tracking и anomaly detection
- Blocklists и quarantine

**Модуль 2.6: Протоколы Shield**

- STP — Sentinel Transfer Protocol
- SBP — Shield-Brain Protocol
- ZDP — Zone Discovery Protocol
- SHSP — Shield Hot Standby Protocol
- SAF — Sentinel Analytics Flow
- SSRP — State Replication Protocol

**Модуль 2.7: Output Filtering**

- PII detection и redaction
- Secret detection (API keys, passwords)
- Custom redaction patterns

**Модуль 2.8: High Availability**

- Active-Standby clustering
- State replication
- Automatic failover
- Zero-downtime upgrades

**Модуль 2.9: Мониторинг**

- Prometheus metrics
- Grafana dashboards
- Alerting strategies
- Performance tuning

### Лабораторные работы

| Lab     | Название                | Время  |
| ------- | ----------------------- | ------ |
| LAB-201 | Multi-Zone Architecture | 60 мин |
| LAB-202 | HA Cluster Setup        | 90 мин |
| LAB-203 | Prometheus Integration  | 45 мин |
| LAB-204 | Output Filtering        | 45 мин |
| LAB-205 | Session Management      | 45 мин |

### Экзамен SSP-200

- 80 вопросов
- 120 минут
- 75% для прохождения
- Теория + конфигурационные сценарии

---

## Уровень 3: SSE (SENTINEL Shield Expert)

### Для кого

Архитекторы безопасности и senior инженеры, разрабатывающие решения enterprise-уровня.

### Предварительные требования

- SSP сертификация
- 6+ месяцев работы с Shield в production
- Глубокие знания C

### Продолжительность

8 недель (160 часов)

### Что ты узнаешь

**Модуль 3.1: Internals Shield**

- Структуры данных и алгоритмы
- Memory management и memory pools
- Thread pool и concurrent processing
- Lock-free structures

**Модуль 3.2: Разработка Custom Guards**

- Guard vtable architecture
- Implementing custom evaluate logic
- Testing и deployment
- Performance considerations

**Модуль 3.3: Plugin System**

- Plugin API
- Dynamic loading
- Hot-reload capabilities
- Versioning и compatibility

**Модуль 3.4: Protocol Development**

- Designing custom protocols
- Binary encodings
- Security considerations
- Testing и validation

**Модуль 3.5: Performance Engineering**

- Profiling с perf и Valgrind
- Micro-optimizations
- Cache-friendly data structures
- SIMD optimizations

**Модуль 3.6: Pattern Engineering**

- Advanced regex patterns
- Evasion-resistant patterns
- Multi-pattern rules
- Performance vs accuracy trade-offs

**Модуль 3.7: Integration Architecture**

- Enterprise integration patterns
- Kubernetes operators
- Service mesh integration
- Multi-region deployment

**Модуль 3.8: Capstone Project**

- Реальный проект
- Full lifecycle: design → implementation → testing → deployment
- Peer review
- Final presentation

### Лабораторные работы

| Lab     | Название                 | Время   |
| ------- | ------------------------ | ------- |
| LAB-301 | Custom Guard Development | 120 мин |
| LAB-302 | Performance Tuning       | 90 мин  |
| LAB-303 | Plugin Development       | 90 мин  |
| LAB-304 | Protocol Implementation  | 120 мин |

### Экзамен SSE-300

- 60 вопросов теории
- 4-часовой практический экзамен
- 80% для прохождения
- Hands-on scenario

---

## Специализации

### SRTS — Red Team Specialist

**Для кого:** Penetration testers и security researchers

**Модули:**

- R.1: Offensive AI Security
- R.2: Attack Methodology
- R.3: Evasion Techniques
- R.4: Payload Development
- R.5: Multi-turn Attack Chains
- R.6: Reporting и Remediation

**Labs:**
| Lab | Название | Время |
|-----|----------|-------|
| LAB-R01 | Attack Simulation | 60 мин |
| LAB-R02 | Evasion Testing | 60 мин |
| LAB-R03 | Payload Generation | 90 мин |

---

### SBTS — Blue Team Specialist

**Для кого:** SOC analysts и incident responders

**Модули:**

- B.1: Defensive AI Security
- B.2: Threat Detection
- B.3: Incident Response
- B.4: Forensics и Analysis
- B.5: Threat Hunting
- B.6: Hardening и Prevention

**Labs:**
| Lab | Название | Время |
|-----|----------|-------|
| LAB-B01 | Incident Response | 60 мин |
| LAB-B02 | Threat Hunting | 90 мин |
| LAB-B03 | Forensic Analysis | 90 мин |

---

## Формат Обучения

### Теория

- Структурированные модули
- Глубокие объяснения концепций
- Реальные примеры атак
- Документация и reference materials

### Практика

- Лабораторные работы на каждый модуль
- Реальная среда с Shield
- Пошаговые инструкции
- Самостоятельные challenge задания

### Оценка

- Quiz после каждого модуля
- Промежуточные assessments
- Финальный экзамен
- Практический hands-on для SSE

---

## Как Начать

### Шаг 0: Понять ЗАЧЕМ

**→ [Module 0: Почему AI Небезопасен](academy/MODULE_0_WHY.md)**

_Даже если ты здесь случайно — прочитай это первым. Поймёшь зачем тебе это нужно._

### Шаг 1: Установи Shield

```bash
git clone https://github.com/SENTINEL/shield.git
cd shield && mkdir build && cd build
cmake .. && make -j$(nproc)
```

### Шаг 2: Изучи основы

Начни с `docs/START_HERE.md`

### Шаг 3: Пройди LAB-101

Первая лабораторная — установка и проверка.

### Шаг 4: Изучай модули SSA

Читай, практикуй, повторяй.

### Шаг 5: Сдай SSA-100

Когда готов — пройди экзамен.

---

## Ресурсы

| Ресурс                                                         | Описание             |
| -------------------------------------------------------------- | -------------------- |
| **[Module 0: Почему AI Небезопасен](academy/MODULE_0_WHY.md)** | **Начни здесь!**     |
| [START_HERE.md](START_HERE.md)                                 | Практический старт   |
| [LABS.md](academy/LABS.md)                                     | Все лабораторные     |
| [EXAM_BANK.md](academy/EXAM_BANK.md)                           | Банк вопросов        |
| [STUDENT_HANDBOOK.md](academy/STUDENT_HANDBOOK.md)             | Руководство студента |
| [INSTRUCTOR_GUIDE.md](academy/INSTRUCTOR_GUIDE.md)             | Для преподавателей   |

---

## Принципы Academy

1. **Глубина важнее скорости** — Лучше понять хорошо, чем быстро и поверхностно
2. **Практика = Знание** — 70% времени на labs
3. **Чистый C** — Никаких компромиссов в технологиях
4. **Профессиональный уровень** — Как Cisco, как AWS, как Google

---

_SENTINEL Academy_
_"Лёгкая дорога не всегда правильная."_
