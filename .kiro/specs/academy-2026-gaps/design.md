# Design: Academy 2026 Gaps Coverage

> **Spec:** academy-2026-gaps  
> **Версия:** 1.0  
> **Дата:** 28 января 2026

---

## 1. Архитектура контента

### 1.1 Структура файлов

```
docs/academy/
├── en/
│   └── 03-attack-vectors/
│       ├── 02-jailbreaks/
│       │   ├── 18-policy-puppetry.md        # NEW
│       │   ├── 19-constrained-decoding.md   # NEW
│       │   ├── 20-time-bandit.md            # NEW
│       │   ├── 21-fallacy-failure.md        # NEW
│       │   └── 22-crescendo-multiturn.md    # NEW
│       ├── 01-prompt-injection/
│       │   ├── 04-invisible-prompts.md      # NEW
│       │   └── 05-character-obfuscation.md  # NEW
│       └── 06-agentic-attacks/
│           ├── 08-mcp-security-threats.md   # NEW
│           └── 09-tool-poisoning-attacks.md # NEW
│   └── 04-agentic-security/
│       └── 04-tool-security/
│           └── 08-mcp-specific.md           # NEW
│   └── 02-threat-landscape/
│       └── 01-owasp-llm-top10/
│           └── 08-LLM08-vector-embeddings.md # UPDATE
│   └── 05-defense-strategies/
│       └── 01-detection/
│           ├── 31-camel-defense.md          # NEW
│           ├── 32-secalign.md               # NEW
│           └── 33-zedd.md                   # NEW
├── ru/
│   └── [mirror structure]
└── labs/
    └── 09-invisible-prompts/                # NEW
        ├── README.md
        └── challenge.py
```

---

## 2. Lesson Template

Каждый урок следует единому шаблону:

```markdown
# [Lesson Title]

> **Track:** [Track Number]  
> **Урок:** [Lesson Number]  
> **Уровень:** [Beginner/Intermediate/Advanced/Expert]  
> **Время:** [XX минут]

---

## Обзор

[1-2 параграфа описания]

---

## Теория

### [Subsection 1]
[Content]

### [Subsection 2]
[Content]

---

## Технические детали

### Как это работает

[Technical explanation with diagrams if needed]

### Пример атаки/защиты

```python
# Code example
```

---

## Практика

### Задание 1
[Description]

### Задание 2
[Description]

---

## Защита / Митигация

[If attack lesson — how to defend]
[If defense lesson — implementation details]

---

## Ссылки

- [Link 1]
- [Link 2]

---

## Следующий урок

→ [Next Lesson Link]
```

---

## 3. Детальный дизайн уроков

### 3.1 Policy Puppetry Jailbreak

**Файл:** `03-attack-vectors/02-jailbreaks/18-policy-puppetry.md`

| Аспект | Содержание |
|--------|------------|
| **Описание** | Structured prompts disguised as override instructions |
| **Техника** | Fictional contexts, scripted dialogues, leetspeak |
| **Target** | Gemini, universal bypass |
| **Пример** | Prompt с "policy override" в XML/JSON structure |
| **Защита** | Input validation, structured output constraints |
| **Источник** | HackAIGC 2025 |

### 3.2 Constrained Decoding Attack (CDA)

**Файл:** `03-attack-vectors/02-jailbreaks/19-constrained-decoding.md`

| Аспект | Содержание |
|--------|------------|
| **Описание** | Weaponizes structured output constraints |
| **Техника** | Schema-level grammar rules (control-plane) |
| **Success Rate** | 96.2% (GPT-4o, Gemini-2.0-flash) |
| **PoC** | Chain Enum Attack |
| **Защита** | Schema validation, output sanitization |
| **Источник** | arXiv 2025 |

### 3.3 MCP Security Threats

**Файл:** `03-attack-vectors/06-agentic-attacks/08-mcp-security-threats.md`

| Аспект | Содержание |
|--------|------------|
| **Shadow Escape** | 2025 exploit, MCP agent takeover |
| **Tool Poisoning (TPA)** | Hidden instructions in tool descriptions |
| **Naming Vulnerabilities** | Similar tool/agent name confusion |
| **Mitigation** | Tool whitelisting, description scanning |
| **Источник** | DEF CON 33, Medium, Solo.io |

### 3.4 Invisible Prompts

**Файл:** `03-attack-vectors/01-prompt-injection/04-invisible-prompts.md`

| Аспект | Содержание |
|--------|------------|
| **Font Injection** | Malicious fonts in external resources |
| **Zero-Width Characters** | U+200B, U+FEFF hidden payloads |
| **Homoglyphs** | Cyrillic/Latin lookalikes |
| **Detection** | Unicode normalization, character filtering |
| **Источник** | arXiv 2025, Mindgard |

---

## 4. Lab Design

### 4.1 Invisible Prompts Lab

**Путь:** `docs/academy/labs/09-invisible-prompts/`

```
09-invisible-prompts/
├── README.md           # Instructions
├── challenge.py        # Test harness
├── payloads/
│   ├── zero_width.txt
│   ├── homoglyphs.txt
│   └── font_inject.html
└── solutions/
    └── detector.py
```

**Objectives:**
1. Обнаружить hidden characters в input
2. Построить detector для invisible prompts
3. Bypass существующих guardrails

---

## 5. TDD Strategy

### 5.1 Test Structure

```
tests/academy/
├── test_lesson_structure.py    # Validates lesson format
├── test_code_examples.py       # Runs code snippets
├── test_bilingual.py           # EN/RU parity check
└── test_curriculum.py          # CURRICULUM.md sync
```

### 5.2 Test Cases

| Test | Description |
|------|-------------|
| `test_lesson_has_overview` | Проверяет наличие секции "Обзор" |
| `test_lesson_has_practice` | Проверяет наличие секции "Практика" |
| `test_code_blocks_valid` | Проверяет синтаксис code blocks |
| `test_links_not_broken` | Проверяет что ссылки валидны |
| `test_en_ru_parity` | EN и RU версии синхронизированы |

### 5.3 Pre-commit Hook

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: academy-lint
      name: Academy Lesson Linter
      entry: python tests/academy/lint_lessons.py
      language: python
      files: ^docs/academy/.*\.md$
```

---

## 6. Implementation Order

| Phase | Tasks | Priority |
|-------|-------|----------|
| **Phase 1** | FR-01.1 (Policy Puppetry), FR-01.2 (CDA), FR-03.1 (MCP) | HIGH |
| **Phase 2** | FR-02.1 (Invisible Prompts), FR-02.2 (Obfuscation) | HIGH |
| **Phase 3** | FR-01.3-5 (Time Bandit, Fallacy, Crescendo) | MEDIUM |
| **Phase 4** | FR-05.1-3 (CaMeL, SecAlign, ZEDD) | MEDIUM |
| **Phase 5** | FR-04.1-2 (MM-PoisonRAG), Labs | MEDIUM |

---

## 7. Риски

| Risk | Mitigation |
|------|------------|
| Устаревание контента | Ссылки на первоисточники, версионирование |
| Неполное покрытие RU | Parallel creation EN+RU |
| Code examples не работают | TDD, automated testing |

---

*Design v1.0 — 28 января 2026*
