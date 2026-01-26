# Техники защиты

> **Модуль: Основные методы защиты**

---

## Обзор

Техники защиты формируют фундамент безопасности AI. Этот модуль охватывает как превентивные, так и детективные контроли для защиты AI систем от атак, с практическими рекомендациями по реализации.

---

## Категории защиты

| Категория | Назначение | Примеры |
|-----------|------------|---------|
| **Превентивные** | Остановка атак до нанесения вреда | Input filtering, guardrails |
| **Детективные** | Идентификация атак в процессе | Мониторинг, anomaly detection |
| **Корректирующие** | Реагирование на инциденты | Incident response, rollback |
| **Сдерживающие** | Отпугивание атакующих | Audit logging, rate limiting |

---

## Слои защиты

```
┌─────────────────────────────────────────────────────────────┐
│                    DEFENSE IN DEPTH                          │
├─────────────────────────────────────────────────────────────┤
│  Слой 1: ЗАЩИТА ВХОДА                                        │
│  ├── Pattern matching (regex, keywords)                     │
│  ├── Семантический анализ (embeddings, classification)      │
│  └── Rate limiting и anomaly detection                      │
├─────────────────────────────────────────────────────────────┤
│  Слой 2: ЗАЩИТА СИСТЕМЫ                                      │
│  ├── Prompt engineering (hardening, structure)              │
│  ├── Разделение привилегий (least access)                   │
│  └── Лимиты ресурсов (tokens, time, memory)                 │
├─────────────────────────────────────────────────────────────┤
│  Слой 3: ЗАЩИТА ВЫХОДА                                       │
│  ├── Фильтрация контента (harmful, PII)                     │
│  ├── Policy enforcement (compliance)                        │
│  └── Response validation (format, length)                   │
├─────────────────────────────────────────────────────────────┤
│  Слой 4: МОНИТОРИНГ                                          │
│  ├── Real-time detection (streaming)                        │
│  ├── Audit logging (forensics)                              │
│  └── Alerting and response (automation)                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Темы

### Защита входа
- Pattern matching с regex и keywords
- Семантический анализ с embeddings
- Rate limiting и quotas
- Input normalization и sanitization

### Защита выхода
- Фильтрация контента для вредоносного материала
- Редактирование PII и credentials
- Policy enforcement и compliance
- Response validation и modification

### Защита системы
- Принципы hardening архитектуры
- Паттерны разделения привилегий
- Enforcement trust boundary
- Реализация лимитов ресурсов

### Мониторинг
- Real-time threat detection
- Комплексное audit logging
- Конфигурация и tuning alerts
- Автоматизация incident response

---

## Ключевые принципы

1. **Defense in depth** — Множество слоёв; нет единой точки отказа
2. **Minimal privilege** — Предоставляй только необходимый доступ
3. **Fail secure** — По умолчанию блокируй при неопределённости
4. **Continuous monitoring** — Детектируй аномалии в реальном времени
5. **Rapid response** — Быстрое containment и remediation

---

## Путь реализации

```
Input Filtering → System Hardening → Output Filtering → Monitoring
       ↓                ↓                   ↓              ↓
  Блокируй плохой    Ограничь ущерб      Лови утечки   Детектируй атаки
    input           если bypassed        в output       в процессе
```

---

## Интеграция SENTINEL

```python
from sentinel import configure, scan, Guard

# Конфигурация слоёв защиты
configure(
    input_engines=["injection", "jailbreak"],
    output_engines=["pii", "harmful"],
    monitoring=True
)

# Применение защиты
guard = Guard(mode="strict")

@guard.protect
def process_message(msg):
    return llm.generate(msg)
```

---

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [Attack Vectors](../03-attack-vectors/) | **Техники защиты** | [Agentic Security](../04-agentic-security/) |

---

*AI Security Academy | Техники защиты*
