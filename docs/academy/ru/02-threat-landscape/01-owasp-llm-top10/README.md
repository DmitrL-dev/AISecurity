# OWASP LLM Top 10

> **Подмодуль 02.1: Отраслевой стандарт фреймворка рисков**

---

## Обзор

OWASP LLM Top 10 — это определяющий фреймворк для понимания и категоризации рисков безопасности в приложениях на основе Large Language Models. Этот подмодуль предоставляет глубокие разборы каждой категории с практическими примерами атак и стратегиями защиты.

---

## Top 10 Уязвимостей

| # | Уязвимость | Уровень риска | Распространённость |
|---|------------|---------------|-------------------|
| LLM01 | Prompt Injection | Критический | Очень высокая |
| LLM02 | Sensitive Information Disclosure | Высокий | Высокая |
| LLM03 | Supply Chain | Высокий | Средняя |
| LLM04 | Data and Model Poisoning | Высокий | Средняя |
| LLM05 | Improper Output Handling | Высокий | Высокая |
| LLM06 | Excessive Agency | Критический | Средняя |
| LLM07 | System Prompt Leakage | Высокий | Высокая |
| LLM08 | Vector and Embedding Weaknesses | Средний | Средняя |
| LLM09 | Misinformation | Средний | Очень высокая |
| LLM10 | Unbounded Consumption | Средний | Высокая |

---

## Уроки

### [01. LLM01: Prompt Injection](01-LLM01-prompt-injection.md)
**Время:** 45 минут | **Критичность:** Критическая

Самая распространённая и опасная уязвимость LLM:
- Техники прямой инъекции
- Непрямая инъекция через контент
- Слои защиты и лучшие практики

### [02. LLM02: Sensitive Information Disclosure](02-LLM02-sensitive-disclosure.md)
**Время:** 35 минут | **Критичность:** Высокая

Предотвращение непреднамеренной утечки данных:
- Извлечение обучающих данных
- Раскрытие system prompt
- PII в выводах

### [03. LLM03: Supply Chain](03-LLM03-supply-chain.md)
**Время:** 40 минут | **Критичность:** Высокая

Атаки на supply chain:
- Внедрение backdoors
- Манипуляция поведением
- Стратегии валидации данных

### [04. LLM04: Data and Model Poisoning](04-LLM04-data-model-poisoning.md)
**Время:** 40 минут | **Критичность:** Высокая

Атаки на данные и модель:
- Data poisoning
- Model poisoning
- Обнаружение и защита

### 05-10. Дополнительные уязвимости
Supply chain, permissions, agency, overreliance и model theft. *Продвинутые уроки доступны в Expert треке.*

---

## Матрица Атака/Защита

| Уязвимость | Основная атака | Основная защита |
|------------|----------------|-----------------|
| Prompt Injection | Встроенные инструкции | Input filtering + output checking |
| Disclosure | Extraction prompts | Output filtering + prompt protection |
| Poisoning | Вредоносные training данные | Data validation + anomaly detection |
| DoS | Resource exhaustion | Rate limiting + input limits |
| Supply Chain | Компрометированные зависимости | Integrity verification |

---

## Практическое применение

Для каждой уязвимости вы изучите:

1. **Что это** - Чёткое определение и scope
2. **Как работает** - Механика атаки и примеры
3. **Real-world impact** - Задокументированные инциденты
4. **Как обнаружить** - Сигнатуры и паттерны
5. **Как предотвратить** - Стратегии защиты

---

## Подход к изучению

### Рекомендуемый порядок
Изучайте уязвимости в порядке распространённости и критичности:
1. LLM01 (Prompt Injection) - Самая частая
2. LLM02 (Disclosure) - Высокое воздействие
3. LLM06 (Excessive Agency) - Растущая угроза
4. Остальные категории

### Практические упражнения
Каждый урок включает:
- Примеры кода атак
- Паттерны детекции
- Интеграция с SENTINEL

---

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [Обзор модуля](../README.md) | **OWASP LLM Top 10** | [OWASP ASI Top 10](../02-owasp-asi-top10/) |

---

*AI Security Academy | Подмодуль 02.1*
