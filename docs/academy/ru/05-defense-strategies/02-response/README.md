# Incident Response

> **Подмодуль 05.2b: Реагирование на AI Security Incidents**

---

## Обзор

Когда атаки успешны или защиты детектируют угрозы, быстрое реагирование критично. Этот подмодуль покрывает процедуры incident response специально адаптированные для AI систем, включая containment, analysis и recovery.

---

## Жизненный цикл инцидента

```
Detection > Triage > Containment > Analysis > Remediation > Review
    ¦          ¦          ¦            ¦           ¦           ¦
    Ў          Ў          Ў            Ў           Ў           Ў
  Alert    Classify    Limit       Find root   Fix issue   Learn &
  fires    severity    damage      cause       & harden    improve
```

---

## Уроки

### 01. Detection and Triage
**Время:** 35 минут | **Сложность:** Средний

Процедуры начального реагирования:
- Техники валидации alerts
- Критерии классификации severity
- Initial response checklist
- Процедуры и тайминг escalation

### 02. Containment
**Время:** 40 минут | **Сложность:** Средний

Ограничение impact атаки:
- Стратегии изоляции для AI систем
- Реализация блокировки трафика
- Опции service degradation
- Коммуникация со стейкхолдерами

### 03. Analysis
**Время:** 45 минут | **Сложность:** Продвинутый

Понимание атаки:
- Сбор и сохранение evidence
- Методология root cause analysis
- Техники реконструкции атаки
- Timeline building

### 04. Recovery and Review
**Время:** 40 минут | **Сложность:** Средний

Возврат к нормальному состоянию и обучение:
- Checklist восстановления сервиса
- Приоритеты hardening защит
- Улучшение мониторинга
- Post-incident review process

---

## Классификация инцидентов

| Severity | Критерии | Время реагирования |
|----------|----------|-------------------|
| **Critical** | Data breach, полный compromise | Немедленно |
| **High** | Успешная атака, limited impact | < 1 часа |
| **Medium** | Attempted attack, заблокирована | < 4 часов |
| **Low** | Подозрительная активность, без impact | < 24 часов |

---

## Структура Response Playbook

```markdown
# Incident Playbook: [Type]

## Detection Indicators
- Что триггерит этот playbook

## Immediate Actions
1. Step-by-step containment

## Investigation Steps
1. Evidence для сбора
2. Analysis для выполнения

## Recovery Procedures
1. Service restoration
2. Verification

## Post-Incident
1. Требования к документации
2. Lessons learned process
```

---

## Ключевые действия по фазам

| Фаза | Primary Actions | Tools |
|------|-----------------|-------|
| **Detect** | Alert validation, severity assessment | SENTINEL Monitor |
| **Contain** | Isolate, block, limit damage | Firewall, API controls |
| **Analyze** | Evidence collection, root cause | Logs, SENTINEL audit |
| **Recover** | Restore, harden, verify | Deployment, testing |
| **Review** | Document, improve, train | Post-mortem template |

---

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [Guardrails](../01-guardrails/) | **Response** | [SENTINEL Integration](../02-sentinel-integration/) |

---

*AI Security Academy | Incident Response*
