# Red Teaming

> **Подмодуль 06.1: Продвинутые offensive техники**

---

## Обзор

Red teaming выходит за рамки базового выполнения атак. Этот подмодуль покрывает автоматизированную генерацию атак, планирование кампаний, исследование evasion и операционные аспекты профессиональных red team engagements.

---

## Темы

| Тема | Описание |
|------|----------|
| **Automation** | Программная генерация атак |
| **Campaigns** | Multi-stage планирование атак |
| **Evasion** | Обход известных защит |
| **Operations** | Процесс профессионального engagement |

---

## Уроки

### 01. Automated Attack Generation
**Время:** 45 минут | **Сложность:** Продвинутый

Построение генераторов атак:
- Payload mutation strategies
- Grammar-based fuzzing
- LLM-assisted attack creation
- Coverage-guided generation

### 02. Campaign Planning
**Время:** 40 минут | **Сложность:** Продвинутый

Стратегические attack campaigns:
- Objective definition
- Attack tree construction
- Resource allocation
- Progress tracking

### 03. Defense Evasion
**Время:** 50 минут | **Сложность:** Эксперт

Обход security controls:
- Detection signature analysis
- Payload obfuscation
- Timing attacks
- Novel technique development

### 04. Operational Security
**Время:** 35 минут | **Сложность:** Продвинутый

Практики профессионального engagement:
- Scope definition
- Rules of engagement
- Documentation requirements
- Responsible disclosure

---

## Этические guidelines

**Red team активности требуют:**
- Письменной авторизации от владельцев систем
- Defined scope и boundaries
- Документации всех активностей
- Responsible disclosure находок

**Никогда:**
- Тестировать без разрешения
- Превышать authorized scope
- Причинять unnecessary harm
- Скрывать critical vulnerabilities

---

## Интеграция STRIKE

```python
from strike import Campaign, Generator

campaign = Campaign(
    name="Q1 Assessment",
    targets=["chatbot-prod", "api-gateway"],
    techniques=["injection", "jailbreak"],
    duration_days=14
)

generator = Generator(
    base_payloads=strike.payloads.INJECTION,
    mutation_rate=0.3,
    coverage_target=0.95
)
```

---

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [Обзор модуля](../README.md) | **Red Teaming** | [TDA Detection](../02-detection-tda/) |

---

*AI Security Academy | Подмодуль 06.1*
