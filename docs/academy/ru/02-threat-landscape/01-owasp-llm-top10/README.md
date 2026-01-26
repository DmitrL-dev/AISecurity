# OWASP LLM Top 10

> **Подмодуль 02.1: Индустриальный стандарт рисков**

---

## Обзор

OWASP LLM Top 10 — определяющий фреймворк для понимания и категоризации рисков безопасности в приложениях на базе больших языковых моделей. Этот подмодуль предоставляет глубокое погружение в каждую категорию с практическими примерами атак и стратегиями защиты.

---

## Top 10 уязвимостей

| # | Уязвимость | Уровень риска | Распространённость |
|---|------------|---------------|-------------------|
| LLM01 | Prompt Injection | Critical | Очень высокая |
| LLM02 | Sensitive Information Disclosure | High | Высокая |
| LLM03 | Training Data Poisoning | High | Средняя |
| LLM04 | Denial of Service | Medium | Средняя |
| LLM05 | Supply Chain Vulnerabilities | High | Средняя |
| LLM06 | Permission & Access Issues | High | Высокая |
| LLM07 | Data & Privacy Leakage | High | Высокая |
| LLM08 | Excessive Agency | Critical | Средняя |
| LLM09 | Overreliance | Medium | Очень высокая |
| LLM10 | Model Theft | Medium | Низкая |

---

## Уроки

### [01. LLM01: Prompt Injection](01-LLM01-prompt-injection.md)
**Время:** 45 минут | **Критичность:** Critical

Самая распространённая и опасная LLM уязвимость:
- Техники direct injection
- Indirect injection через контент
- Слои защиты и лучшие практики

### [02. LLM02: Sensitive Information Disclosure](02-LLM02-sensitive-disclosure.md)
**Время:** 35 минут | **Критичность:** High

Предотвращение непреднамеренных утечек данных:
- Extraction training data
- Раскрытие system prompt
- PII в outputs

### 03. LLM03: Training Data Poisoning
**Время:** 40 минут | **Критичность:** High

Supply chain атаки на training data:
- Backdoor insertion
- Манипуляция поведением
- Стратегии валидации данных

### 04. LLM04: Denial of Service
**Время:** 30 минут | **Критичность:** Medium

Атаки истощения ресурсов:
- Token flooding
- Recursive generation
- Rate limiting защиты

### 05-10. Дополнительные уязвимости
Supply chain, permissions, agency, overreliance и model theft. *Продвинутые уроки доступны в Эксперт track.*

---

## Матрица Attack/Defense

| Уязвимость | Основная атака | Основная защита |
|------------|----------------|-----------------|
| Prompt Injection | Embedded instructions | Input filtering + output checking |
| Disclosure | Extraction prompts | Output filtering + prompt protection |
| Poisoning | Malicious training data | Data validation + anomaly detection |
| DoS | Resource exhaustion | Rate limiting + input limits |
| Supply Chain | Compromised dependencies | Integrity verification |

---

## Практическое применение

Для каждой уязвимости вы узнаете:

1. **Что это** — Чёткое определение и scope
2. **Как работает** — Механика атак и примеры
3. **Real-world impact** — Документированные инциденты
4. **Как детектировать** — Сигнатуры и паттерны
5. **Как предотвращать** — Стратегии защиты

---

## Подход к изучению

### Рекомендованный порядок
Изучайте уязвимости по порядку распространённости и критичности:
1. LLM01 (Prompt Injection) — Самая частая
2. LLM02 (Disclosure) — Высокий impact
3. LLM08 (Excessive Agency) — Растущая угроза
4. Остальные категории

### Hands-On Practice
Каждый урок включает:
- Примеры кода атак
- Паттерны детекции
- Интеграцию SENTINEL

---

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [Обзор модуля](../README.md) | **OWASP LLM Top 10** | [OWASP ASI Top 10](../02-owasp-asi-top10/) |

---

*AI Security Academy | Подмодуль 02.1*
