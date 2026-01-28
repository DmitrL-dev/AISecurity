# OWASP Agentic Security Initiative (ASI) Top 10

> **Подмодуль 02.2: Защита автономных AI систем**

---

## Обзор

По мере того как AI системы эволюционируют от простых чатботов к автономным агентам с инструментами и возможностями, появляются новые риски безопасности. OWASP ASI Top 10 адресует эти агент-специфичные уязвимости, которые выходят за рамки традиционной безопасности LLM.

---

## Чем отличаются агентные системы?

| Аспект | Традиционный LLM | Агентная система |
|--------|------------------|------------------|
| **Scope** | Q&A, генерация | Действия, решения |
| **Persistence** | Stateless | Multi-turn state |
| **Capabilities** | Только текст | Tools, APIs, файлы |
| **Autonomy** | Human loop | Полу-автономный |
| **Attack Surface** | Input/output | Вся цепочка инструментов |

---

## ASI Top 10

| # | Уязвимость | Риск | Описание |
|---|------------|------|----------|
| ASI01 | System Compromise | Критический | Полный захват агента |
| ASI02 | Privilege Escalation | Критический | Несанкционированное повышение доступа |
| ASI03 | Tool Misuse | Высокий | Вредоносное использование инструментов |
| ASI04 | Data Exfiltration | Высокий | Кража данных через агента |
| ASI05 | Goal Hijacking | Высокий | Перенаправление целей агента |
| ASI06 | Memory Poisoning | Средний | Повреждение persistent памяти |
| ASI07 | Cross-Agent Attacks | Средний | Эксплуатация агент-агент |
| ASI08 | Trust Boundary Violations | Высокий | Нарушение изоляции |
| ASI09 | Cascading Failures | Средний | Усиленные ошибки |
| ASI10 | Audit Trail Manipulation | Средний | Сокрытие следов атаки |

---

## Уроки

### 01. ASI01: System Compromise
**Время:** 45 минут | **Критичность:** Критическая

Полный захват агента через:
- Multi-vector атаки
- Persistent compromise
- Defense-in-depth стратегии

### 02. ASI02: Privilege Escalation
**Время:** 40 минут | **Критичность:** Критическая

Получение несанкционированного доступа:
- Вертикальная escalation
- Горизонтальное перемещение
- Capability-based access control

### 03-10. Дополнительные уязвимости
Злоупотребление инструментами, exfiltration, манипуляция целями и другое в последующих уроках.

---

## Ключевые паттерны атак

### Multi-Hop Exploitation
```
User Input → Agent 1 → Tool A → External Data → Agent 2 → Compromise
```

Атакующие связывают несколько шагов для достижения чувствительных ресурсов.

### Persistent Memory Attacks
```
Session 1: Внедрение вредоносного контекста
Session 2-N: Эксплуатация отравленной памяти
```

Атаки, которые сохраняются между сессиями агента.

### Trust Delegation Abuse
```
Trusted Agent → Делегирует к → Untrusted Tool → Вредоносное действие
```

Эксплуатация унаследованного доверия от агента.

---

## Сравнение с LLM Top 10

| LLM Issue | ASI Extension |
|-----------|---------------|
| Prompt Injection | + Tool injection, goal hijacking |
| Excessive Agency | + Multi-agent exploitation |
| Data Leakage | + Exfiltration через инструменты |
| DoS | + Cascading failures |

---

## Приоритеты защиты

1. **Trust Boundaries** - Строгая изоляция между компонентами
2. **Capability Limits** - Минимально необходимые permissions
3. **Audit Logging** - Полные traces действий
4. **Human Oversight** - Approval для чувствительных действий
5. **Memory Protection** - Валидация persistent state

---

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [OWASP LLM Top 10](../01-owasp-llm-top10/) | **OWASP ASI Top 10** | [Attack Vectors](../../03-attack-vectors/) |

---

*AI Security Academy | Подмодуль 02.2*
