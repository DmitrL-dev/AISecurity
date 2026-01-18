# Дизайн: Закрытие Documentation Gaps

## Обзор

Планомерное закрытие 5 документационных гапов, выявленных после реструктуризации README.

---

## DS-1: Mid-Level Lesson 08 — Monitoring

### Содержание урока

```
08-monitoring.md
├── Введение в observability
├── Metrics (Prometheus)
├── Logging
├── Tracing (OpenTelemetry)
├── Dashboards (Grafana)
└── Alerting
```

### Структура

| Секция | EN | RU |
|--------|----|----|
| Title | Monitoring & Observability | Мониторинг и Observability |
| Time | 35 min | 35 мин |
| Module | Mid-Level 2.4 | Mid-Level 2.4 |

---

## DS-2: CONTRIBUTING.md

### Структура документа

```markdown
1. Introduction
2. Code of Conduct
3. Getting Started
   - Fork & Clone
   - Development Setup
4. Making Changes
   - Branch Naming
   - Commit Messages
   - Code Style
5. Pull Request Process
6. Review Guidelines
7. Community
```

---

## DS-3: RU READMEs

Копирование структуры EN README с русским контентом.

---

## DS-4: CHANGELOG.md

### Формат

```markdown
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

## [4.1.0] - 2026-01-18

### Added
- Bilingual Academy (48 EN + 48 RU lessons)
- SECURITY.md
- ARCHITECTURE.md

### Changed
- README restructuring
- Collapsible sections
```

---

## DS-5: Benchmarks

### Таблица для README

```markdown
| Engine | Precision | Recall | F1 | P50 | P99 |
|--------|-----------|--------|----|----|-----|
| injection_detector | 97% | 94% | 95% | 3ms | 12ms |
| jailbreak_detector | 95% | 91% | 93% | 8ms | 25ms |
| tda_analyzer | 89% | 96% | 92% | 45ms | 120ms |
```

---

## Порядок реализации

1. **FR-1** → Mid-Level 08 (EN + RU)
2. **FR-2** → CONTRIBUTING.md
3. **FR-3** → RU READMEs
4. **FR-4** → CHANGELOG.md
5. **FR-5** → Benchmarks (опционально)
