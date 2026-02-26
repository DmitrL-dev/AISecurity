# SENTINEL DevKit

> **Набор правил, навыков и паттернов для agent-first разработки в экосистеме SENTINEL**

## Архитектура Методологии

```
┌─────────────────────────────────────────────────────────────────┐
│                    SDD (SPEC-DRIVEN DEVELOPMENT)                │
│                        PRIMARY FRAMEWORK                        │
│                                                                 │
│   Phase 1: SPECIFICATION (ЧТО строить?)                        │
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐          │
│   │ Requirements│ → │   Design    │ → │    Tasks    │          │
│   │   (.md)     │   │   (.md)     │   │   (.md)     │          │
│   └─────────────┘   └─────────────┘   └─────────────┘          │
│         ↓                 ↓                 ↓                   │
│      Human Review     Human Review     Human Review             │
│                                                                 │
│   Phase 2: IMPLEMENTATION (КАК строить правильно?)             │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │                  TDD IRON LAW                           │  │
│   │        🔴 RED → 🟢 GREEN → 🔄 REFACTOR                  │  │
│   │        (Test First → Minimal Code → Improve)            │  │
│   └─────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│   ┌─────────────────────────────────────────────────────────┐  │
│   │              TWO-STAGE REVIEW                           │  │
│   │     Stage 1: Spec Compliance → Stage 2: Code Quality   │  │
│   └─────────────────────────────────────────────────────────┘  │
│                              ↓                                  │
│                         ✅ MERGE                                │
└─────────────────────────────────────────────────────────────────┘
```

## Иерархия

| Уровень | Компонент | Отвечает на вопрос | Источник |
|---------|-----------|-------------------|----------|
| **MACRO** | SDD (Kiro) | ЧТО строить? | Kiro Specs |
| **MICRO** | TDD Iron Law | КАК строить правильно? | Superpowers |
| **GATE** | Two-Stage Review | Готов ли код к merge? | Superpowers |
| **LOOP** | QA Fix Loop | Как исправить issues? | Auto-Claude |

## Структура

```
devkit/
├── README.md                          # Этот файл
├── rules/
│   └── rationalizations.md            # Таблица оправданий для TDD
├── skills/
│   ├── two-stage-review/SKILL.md      # Spec Compliance + Code Quality
│   ├── qa-fix-loop/SKILL.md           # Reviewer → Fixer цикл
│   └── tdd-enforcement/SKILL.md       # TDD Iron Law
├── prompts/
│   ├── README.md                      # Архитектура промптов
│   ├── reviewer.md                    # Reviewer Agent prompt
│   ├── fixer.md                       # Fixer Agent prompt
│   └── security-audit.md              # Security Auditor prompt
├── specs/
│   └── dot-templates.md               # DOT flowchart шаблоны
├── memory/
│   └── rlm-integration.md             # RLM Memory Bridge интеграция
└── hooks/
    ├── README.md                      # Инструкции установки
    ├── pre-commit.sh                  # Bash hook (Linux/macOS)
    └── pre-commit.ps1                 # PowerShell hook (Windows)
```

## Workflows

| Команда | Файл | Назначение |
|---------|------|------------|
| `/devkit:tdd-check` | `.agent/workflows/devkit-tdd-check.md` | Быстрая проверка TDD compliance |
| `/engine-verification` | `.agent/workflows/engine-verification.md` | Полная верификация engine (вкл. Two-Stage) |

## Ключевые компоненты

### 1. TDD Iron Law (Rule 21)
**NO PRODUCTION CODE WITHOUT A FAILING TEST FIRST**

Интегрировано в `agent_system_prompts/core_instructions.md`.

### 2. Two-Stage Review
Разделение code review на две фазы:
1. **Spec Compliance** — соответствует ли код спецификации?
2. **Code Quality** — качество, паттерны, maintainability

### 3. QA Fix Loop
Автономный цикл исправления: `Reviewer → Issue → Fixer → Re-review`

### 4. DOT Flowcharts
Использование DOT-диаграмм как исполняемых спецификаций в Kiro specs.

## Интеграция

DevKit работает через:
- `/devkit:*` workflows в `.agent/workflows/`
- SKILL.md файлы для Antigravity агента
- RLM Memory Bridge для хранения решений

## Лицензия

MIT (Superpowers-derived) + Apache 2.0 (SENTINEL core)
