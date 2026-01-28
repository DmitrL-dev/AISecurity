# Требования: Academy 2026 Gaps Coverage

> **Spec:** academy-2026-gaps  
> **Версия:** 1.0  
> **Дата:** 28 января 2026  
> **Источник:** R&D отчёт `docs/rnd/2026-01-28-full-research.md`

---

## 1. Обзор

Покрытие критических gaps, выявленных в R&D раунде 28.01.2026. Фокус на новых техниках атак 2025-2026, которые отсутствуют в Academy.

---

## 2. Функциональные требования

### FR-01: Новые Jailbreak уроки

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-01.1 | Создать урок "Policy Puppetry Jailbreak" с описанием техники, примерами, защитой | HIGH |
| FR-01.2 | Создать урок "Constrained Decoding Attack (CDA)" — 96.2% success rate | HIGH |
| FR-01.3 | Создать урок "Time Bandit Jailbreak" — temporal confusion | HIGH |
| FR-01.4 | Создать урок "Fallacy Failure" — логические манипуляции | MEDIUM |
| FR-01.5 | Создать урок "Crescendo Multi-Turn Attack" | MEDIUM |

### FR-02: Invisible Prompts / Obfuscation

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-02.1 | Создать урок "Invisible Prompts" — font injection, hidden characters | HIGH |
| FR-02.2 | Создать урок "Character Obfuscation" — emoji, homoglyphs, leetspeak, zero-width | HIGH |
| FR-02.3 | Добавить lab "Invisible Prompt Detection" | MEDIUM |

### FR-03: MCP/A2A Security

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-03.1 | Создать урок "MCP Security Threats" — Shadow Escape, TPA, naming vulnerabilities | HIGH |
| FR-03.2 | Создать урок "Tool Poisoning Attacks (TPA)" | HIGH |
| FR-03.3 | Обновить Track 04.4 (Tool Security) с MCP-specific content | MEDIUM |

### FR-04: Multimodal RAG

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-04.1 | Создать урок "MM-PoisonRAG" — multimodal RAG poisoning (ICLR 2026) | HIGH |
| FR-04.2 | Обновить LLM08 (Vector Embeddings) с multimodal attacks | MEDIUM |

### FR-05: Новые защитные техники

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-05.1 | Создать урок "CaMeL Defense" — protective system layer | MEDIUM |
| FR-05.2 | Создать урок "SecAlign" — preference optimization, ~0% injection success | MEDIUM |
| FR-05.3 | Создать урок "ZEDD" — zero-shot embedding drift detection | MEDIUM |

---

## 3. Нефункциональные требования

### NFR-01: Структура уроков

- Каждый урок следует шаблону Academy (`_templates/lesson-template.md`)
- Билингвальность: EN + RU версии
- Включает: теорию, примеры кода, практические задания

### NFR-02: TDD

- Каждый урок имеет тест в `tests/academy/`
- Проверка: структура, обязательные секции, code examples

### NFR-03: Интеграция

- Уроки добавляются в CURRICULUM.md
- Обновляется README.md соответствующих треков

---

## 4. User Stories

### US-01: Security Researcher
> Как исследователь безопасности, я хочу изучить новейшие jailbreak техники (Policy Puppetry, CDA), чтобы понимать современные угрозы для LLM.

**Acceptance Criteria:**
- [ ] Урок содержит описание техники
- [ ] Урок содержит работающие примеры
- [ ] Урок содержит методы защиты
- [ ] Урок доступен на EN и RU

### US-02: Red Teamer
> Как red teamer, я хочу получить готовые payloads для MCP атак, чтобы тестировать agentic AI системы.

**Acceptance Criteria:**
- [ ] Урок MCP Security содержит примеры атак
- [ ] Lab включает практические задания
- [ ] Интеграция с STRIKE payloads

### US-03: Blue Teamer
> Как blue teamer, я хочу изучить новые защитные техники (CaMeL, SecAlign, ZEDD), чтобы внедрить их в production.

**Acceptance Criteria:**
- [ ] Уроки содержат implementation guides
- [ ] Примеры интеграции с SENTINEL BRAIN

---

## 5. Out of Scope

- Изменения в BRAIN detection engines (отдельная spec)
- Изменения в STRIKE payloads (отдельная spec)
- Видео-контент для уроков

---

## 6. Dependencies

| Dependency | Описание |
|------------|----------|
| Academy templates | `docs/academy/_templates/` |
| CURRICULUM.md | `docs/academy/CURRICULUM.md` |
| R&D Report | `docs/rnd/2026-01-28-full-research.md` |

---

## 7. Success Metrics

| Metric | Target |
|--------|--------|
| Новых уроков | 12+ |
| Новых labs | 3+ |
| OWASP 2025 coverage | 100% |
| Билингвальность | EN + RU |

---

*Requirements v1.0 — 28 января 2026*
