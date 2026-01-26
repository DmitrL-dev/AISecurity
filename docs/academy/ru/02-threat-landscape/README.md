# Threat Landscape

> **Модуль 02: Знай своего врага**

---

## Обзор

Эффективная защита требует понимания ландшафта угроз. Этот модуль предоставляет комплексную таксономию атак против AI систем, организованную как по индустриальным стандартам (OWASP), так и по методологии атак.

---

## Почему изучать угрозы первыми?

```
Знать атаки → Понимать риск → Проектировать защиты → Строить детекцию
```

Вы не можете защищаться от того, чего не понимаете. Этот модуль даёт вам перспективу атакующего, чтобы вы могли предвидеть и противодействовать их техникам.

---

## Таксономии атак

### Индустриальные стандарты

| Framework | Фокус | Покрытие |
|-----------|-------|----------|
| **OWASP LLM Top 10** | Language models | Prompt injection, data leakage и др. |
| **OWASP ASI Top 10** | Agentic systems | Privilege escalation, tool abuse |
| **MITRE ATLAS** | ML системы широко | От reconnaissance до impact |

### По Attack Surface

| Поверхность | Типы атак |
|-------------|-----------|
| **Input** | Prompt injection, jailbreaking |
| **Model** | Adversarial examples, extraction |
| **Output** | Data leakage, harmful content |
| **System** | Tool abuse, privilege escalation |

---

## Подмодули

### [01. OWASP LLM Top 10](01-owasp-llm-top10/)
Индустриальный стандарт для LLM security risks:

1. LLM01: Prompt Injection
2. LLM02: Sensitive Information Disclosure
3. LLM03: Training Data Poisoning
4. LLM04: Denial of Service
5. LLM05: Supply Chain Vulnerabilities
6. LLM06: Permission Issues
7. LLM07: Data Leakage
8. LLM08: Excessive Agency
9. LLM09: Overreliance
10. LLM10: Model Theft

### [02. OWASP ASI Top 10](02-owasp-asi-top10/)
Расширение покрытия на agentic AI системы:

1. ASI01: System Compromise
2. ASI02: Privilege Escalation
3. ASI03: Tool Misuse
4. ASI04: Data Exfiltration
5. ASI05: Goal Hijacking
... и другие

---

## Путь обучения

### Для Blue Team (Защитники)
1. Изучите каждую категорию уязвимостей
2. Поймите сигнатуры детекции
3. Практикуйте идентификацию атак
4. Стройте слои защиты

### Для Red Team (Атакующие)
1. Изучите техники атак глубоко
2. Поймите обходы и evasions
3. Практикуйте эксплуатацию безопасно
4. Документируйте новые открытия

---

## Ключевые insights

### Распространённость атак (2024-2025)

| Тип атаки | Частота | Сложность |
|-----------|---------|-----------|
| Prompt Injection | Очень высокая | Низкая |
| Jailbreaking | Высокая | Средняя |
| Data Extraction | Средняя | Средняя |
| Model Theft | Низкая | Высокая |

### Тренд: Agentic атаки

По мере того как AI системы получают больше capabilities (tools, actions), появляются новые векторы атак:
- Tool injection
- Multi-hop exploitation
- Cross-agent атаки
- Persistent compromise

---

## Навигация

| Предыдущий | Текущий | Следующий |
|------------|---------|-----------|
| [AI Fundamentals](../01-ai-fundamentals/) | **Threat Landscape** | [Attack Vectors](../03-attack-vectors/) |

---

*AI Security Academy | Модуль 02*
