# AI Security Academy — Дизайн

> **Spec ID:** ai-security-academy  
> **Фаза:** Design  
> **Дата:** 2026-01-25

---

## Архитектура контента

### Иерархия файлов

```
docs/academy/
├── README.md                      # Главная страница Academy
├── CURRICULUM.md                  # Полная учебная программа
├── ru/                            # 🇷🇺 Русская версия
│   ├── README.md                  # Навигация RU
│   ├── 00-introduction/
│   │   ├── 00-welcome.md
│   │   ├── 01-how-to-use.md
│   │   ├── 02-learning-paths.md
│   │   └── 03-prerequisites.md
│   ├── 01-ai-fundamentals/
│   │   ├── README.md
│   │   ├── 01-model-types/
│   │   │   ├── 01-transformers.md
│   │   │   ├── 02-encoder-only.md
│   │   │   ├── 03-decoder-only.md
│   │   │   ├── 04-encoder-decoder.md
│   │   │   ├── 05-vision-transformers.md
│   │   │   ├── 06-multimodal.md
│   │   │   ├── 07-mixture-of-experts.md
│   │   │   ├── 08-state-space.md
│   │   │   ├── 09-diffusion.md
│   │   │   └── 10-audio-models.md
│   │   ├── 02-architecture/
│   │   │   ├── 01-attention.md
│   │   │   ├── 02-positional-encoding.md
│   │   │   ├── 03-tokenization.md
│   │   │   ├── 04-embeddings.md
│   │   │   ├── 05-context-windows.md
│   │   │   ├── 06-kv-cache.md
│   │   │   ├── 07-quantization.md
│   │   │   └── 08-adapters.md
│   │   ├── 03-inference/
│   │   └── 04-training/
│   ├── 02-threat-landscape/
│   │   ├── README.md
│   │   ├── 01-owasp-llm-top10/
│   │   │   ├── 01-LLM01-prompt-injection.md
│   │   │   ├── 02-LLM02-sensitive-disclosure.md
│   │   │   └── ... (10 уроков)
│   │   ├── 02-owasp-asi-top10/
│   │   │   ├── 01-ASI01-agentic-injection.md
│   │   │   └── ... (10 уроков)
│   │   ├── 03-threat-actors/
│   │   ├── 04-attack-surfaces/
│   │   ├── 05-incidents/
│   │   └── 06-emerging-threats/
│   ├── 03-attack-vectors/
│   │   ├── README.md
│   │   ├── 01-prompt-injection/
│   │   │   ├── 01-direct-injection.md
│   │   │   ├── 02-indirect-injection.md
│   │   │   ├── 03-image-injection.md
│   │   │   └── ... (8+ техник)
│   │   ├── 02-jailbreaks/
│   │   │   ├── 01-dan-family.md
│   │   │   ├── 02-crescendo.md
│   │   │   ├── 03-many-shot.md
│   │   │   └── ... (17+ техник)
│   │   ├── 03-data-poisoning/
│   │   ├── 04-model-attacks/
│   │   ├── 05-infrastructure/
│   │   └── 06-agentic-attacks/
│   ├── 04-agentic-security/
│   │   ├── README.md
│   │   ├── 01-architectures/
│   │   ├── 02-protocols/
│   │   ├── 03-trust-authorization/
│   │   ├── 04-tool-security/
│   │   ├── 05-memory-security/
│   │   ├── 06-multi-agent/
│   │   └── 07-human-interaction/
│   ├── 05-defense-strategies/
│   │   ├── README.md
│   │   ├── 01-detection/           # 30+ стратегий
│   │   │   ├── 01-pattern-matching.md
│   │   │   ├── 02-semantic-analysis.md
│   │   │   └── ...
│   │   ├── 02-prevention/          # 30+ стратегий
│   │   ├── 03-response/            # 20+ стратегий
│   │   └── 04-recovery/            # 20+ стратегий
│   ├── 06-advanced-detection/
│   │   ├── README.md
│   │   ├── 01-tda/
│   │   ├── 02-geometric/
│   │   ├── 03-information-geometry/
│   │   ├── 04-dynamical-systems/
│   │   ├── 05-category-theory/
│   │   └── 06-novel-methods/
│   ├── 07-governance/
│   │   ├── README.md
│   │   ├── 01-sentinel-framework/
│   │   ├── 02-international/
│   │   ├── 03-regional/
│   │   ├── 04-industry/
│   │   ├── 05-organizational/
│   │   └── 06-technical-controls/
│   ├── 08-labs/
│   │   ├── README.md
│   │   ├── strike-red-team/        # 40+ лабораторных
│   │   │   ├── lab-001-basic-injection.md
│   │   │   ├── lab-002-indirect-injection.md
│   │   │   └── ...
│   │   ├── sentinel-blue-team/     # 40+ лабораторных
│   │   │   ├── lab-001-installation.md
│   │   │   ├── lab-002-configuration.md
│   │   │   └── ...
│   │   ├── purple-team/            # 20+ лабораторных
│   │   └── ctf/                    # 20+ челленджей
│   └── certification/
│       ├── README.md
│       ├── beginner-exam.md
│       ├── intermediate-exam.md
│       ├── advanced-exam.md
│       └── expert-exam.md
├── en/                             # 🇬🇧 English version
│   └── ... (identical structure)
└── assets/
    ├── images/
    │   ├── architecture/
    │   ├── attacks/
    │   ├── defense/
    │   └── diagrams/
    ├── code-samples/
    │   ├── python/
    │   ├── typescript/
    │   └── bash/
    └── notebooks/
        ├── attack-demos/
        └── defense-demos/
```

---

## Формат урока

### Шаблон урока (lesson-template.md)

```markdown
# [Название урока]

> **Уровень:** Beginner | Intermediate | Advanced | Expert
> **Время:** X минут
> **Предварительные требования:** [Список]

## Цели обучения

После этого урока вы сможете:
- [ ] Цель 1
- [ ] Цель 2
- [ ] Цель 3

## Теория

[Основной контент]

## Примеры

### Пример 1: [Название]
```python
# Реальный код из SENTINEL
```

### Пример 2: [Название]
[Описание]

## Практика

### Задание 1
[Описание задания]

<details>
<summary>Подсказка</summary>
[Подсказка]
</details>

<details>
<summary>Решение</summary>
[Решение]
</details>

## Проверочные вопросы

1. Вопрос 1?
   - [ ] A) Вариант
   - [ ] B) Вариант
   - [x] C) Правильный ответ
   - [ ] D) Вариант

2. Вопрос 2?
   ...

## Дополнительные материалы

- [Ссылка 1](url)
- [Ссылка 2](url)

## Следующий урок

→ [Название следующего урока](./next-lesson.md)
```

---

## Формат лабораторной

### Шаблон лабораторной (lab-template.md)

```markdown
# Lab XXX: [Название]

> **Тип:** Red Team | Blue Team | Purple Team | CTF
> **Уровень:** Beginner | Intermediate | Advanced | Expert
> **Время:** X минут
> **Инструменты:** STRIKE | SENTINEL | Both

## Цель

[Что студент должен сделать]

## Сценарий

[Описание сценария атаки/защиты]

## Подготовка

### Требования
- Python 3.11+
- SENTINEL установлен
- STRIKE payloads загружены

### Окружение
```bash
# Команды настройки
```

## Шаги

### Шаг 1: [Название]
[Инструкции]

```python
# Код
```

### Шаг 2: [Название]
...

## Проверка успеха

- [ ] Результат 1 достигнут
- [ ] Результат 2 достигнут
- [ ] Результат 3 достигнут

## Разбор

### Что произошло
[Объяснение]

### Почему это важно
[Связь с реальностью]

### Как защититься / атаковать
[Практические советы]

## Дополнительные задачи

1. **Easy:** [Задача]
2. **Medium:** [Задача]
3. **Hard:** [Задача]

## Связанные материалы

- Урок: [Название](link)
- Движок: [Название](link to engine)
- STRIKE payload: [Название](link)
```

---

## Билингвальная синхронизация

### Процесс

1. **Создание контента:**
   - Пишем на русском (primary)
   - Переводим на английский (secondary)
   - Сохраняем идентичную структуру

2. **Файловая конвенция:**
   ```
   ru/01-ai-fundamentals/01-model-types/01-transformers.md
   en/01-ai-fundamentals/01-model-types/01-transformers.md
   ```

3. **Синхронизация:**
   - При обновлении RU → обновляем EN
   - Версия указывается в frontmatter
   - CI проверяет соответствие структуры

### Frontmatter

```yaml
---
title: "Трансформеры"
title_en: "Transformers"
version: 1.0.0
last_updated: 2026-01-25
author: SENTINEL Team
level: beginner
duration_minutes: 30
track: 01-ai-fundamentals
module: 01-model-types
lesson: 01
prerequisites:
  - 00-introduction/02-learning-paths
tags:
  - transformers
  - architecture
  - fundamentals
---
```

---

## Learning Paths

### Path 1: Security Beginner (2 месяца)
```
Week 1-2:  00-introduction + 01-ai-fundamentals (basics)
Week 3-4:  02-threat-landscape (OWASP LLM Top 10)
Week 5-6:  03-attack-vectors (injection basics)
Week 7-8:  05-defense-strategies (detection basics)
Labs:      5 Red Team + 5 Blue Team basics
Exam:      Beginner Certification
```

### Path 2: Security Practitioner (3 месяца)
```
Week 1-4:   All remaining 01-03 content
Week 5-8:   04-agentic-security
Week 9-12:  05-defense (full)
Labs:       20 Red + 20 Blue + 5 Purple
Exam:       Intermediate Certification
```

### Path 3: Security Expert (4 месяца)
```
Week 1-4:   06-advanced-detection
Week 5-8:   07-governance
Week 9-12:  Advanced labs + CTF
Week 13-16: Capstone project
Labs:       Full set (100+)
Exam:       Advanced/Expert Certification
```

---

## Интеграция с SENTINEL

### Ссылки на движки

```markdown
## Связанные движки SENTINEL

| Движок | Файл | Описание |
|--------|------|----------|
| InjectionEngine | [injection.py](file:///...) | Базовая детекция инъекций |
| SemanticFirewall | [semantic_firewall.py](file:///...) | Семантический анализ |
```

### Примеры кода

Все примеры берутся из реального кода SENTINEL:

```python
# Из src/brain/engines/injection.py
from sentinel.brain.engines import InjectionEngine

engine = InjectionEngine()
result = engine.analyze(prompt)

if result.is_malicious:
    print(f"Detected: {result.attack_type}")
```

---

## Интеграция со STRIKE

### Payloads в лабораторных

```markdown
## STRIKE Payloads

Для этой лабораторной используются:

| Payload ID | Категория | Описание |
|------------|-----------|----------|
| STR-INJ-001 | Injection | Basic prompt injection |
| STR-INJ-002 | Injection | Indirect via document |
```

### Использование

```python
from strike import PayloadLoader

payloads = PayloadLoader.load_category("injection")
for payload in payloads:
    result = target.send(payload.content)
    # Analyze response
```

---

## CI/CD для Academy

### Проверки

```yaml
# .github/workflows/academy-check.yml
- name: Structure Sync
  run: |
    # Проверить что ru/ и en/ имеют идентичную структуру
    python scripts/check_academy_sync.py

- name: Link Validation
  run: |
    # Проверить все ссылки на движки/payloads
    python scripts/validate_links.py

- name: Markdown Lint
  run: markdownlint docs/academy/

- name: Spell Check
  run: |
    aspell -l ru docs/academy/ru/**/*.md
    aspell -l en docs/academy/en/**/*.md
```

---

## Roadmap реализации

### Phase 1: Foundation (P0) — 4 недели
- [ ] Структура папок
- [ ] Track 1: AI Fundamentals (25 уроков)
- [ ] Track 2: Threat Landscape (40 уроков)
- [ ] 20 базовых лабораторных
- [ ] README и навигация

### Phase 2: Core (P1) — 6 недель
- [ ] Track 3: Attack Vectors (60 техник)
- [ ] Track 4: Agentic Security (40 уроков)
- [ ] Track 5: Defense Strategies (100 стратегий)
- [ ] 40 лабораторных
- [ ] Beginner certification

### Phase 3: Advanced (P2) — 4 недели
- [ ] Track 6: Advanced Detection (40 техник)
- [ ] Track 7: Governance (30 frameworks)
- [ ] 40 лабораторных
- [ ] Intermediate certification

### Phase 4: Polish (P3) — 2 недели
- [ ] CTF challenges (20)
- [ ] Video placeholders
- [ ] Full review
- [ ] Launch

---

## Метрики качества

| Метрика | Target |
|---------|--------|
| Уроков на трек | 25-60 |
| Примеров кода на урок | 2-5 |
| Практических заданий на урок | 1-3 |
| Вопросов на урок | 3-5 |
| Лабораторных с STRIKE | 40+ |
| Лабораторных с SENTINEL | 40+ |
| Покрытие движков SENTINEL | 80%+ |

---

*Дизайн создан: 2026-01-25*
