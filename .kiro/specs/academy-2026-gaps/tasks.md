# Tasks: Academy 2026 Gaps Coverage

> **Spec:** academy-2026-gaps  
> **Версия:** 1.0  
> **Дата:** 28 января 2026

---

## Phase 1: Critical Jailbreaks + MCP (HIGH Priority)

### Task 1.1: Policy Puppetry Jailbreak Lesson
- [x] Создать `en/03-attack-vectors/02-jailbreaks/18-policy-puppetry.md`
- [x] Написать теорию: structured prompts, fictional contexts
- [x] Добавить code examples с payload
- [x] Описать защитные меры
- [x] Создать RU версию `ru/03-attack-vectors/02-jailbreaks/18-policy-puppetry.md`
- [x] Написать тест `tests/academy/test_2026_gaps.py`

### Task 1.2: Constrained Decoding Attack (CDA) Lesson
- [x] Создать `en/03-attack-vectors/02-jailbreaks/19-constrained-decoding.md`
- [x] Написать теорию: schema-level grammar, Chain Enum Attack
- [x] Добавить code examples с 96.2% success rate demo
- [x] Описать защитные меры: schema validation
- [x] Создать RU версию
- [x] Написать тест

### Task 1.3: MCP Security Threats Lesson
- [x] Создать `en/03-attack-vectors/01-agentic-attacks/08-mcp-security-threats.md`
- [x] Описать Shadow Escape exploit
- [x] Описать Tool Poisoning Attacks (TPA)
- [x] Описать naming vulnerabilities
- [x] Добавить mitigation strategies
- [x] Создать RU версию
- [x] Написать тест

### Task 1.4: Tool Poisoning Attacks (TPA) Lesson
- [ ] Создать `en/03-attack-vectors/06-agentic-attacks/09-tool-poisoning-attacks.md`
- [ ] Детальное описание hidden instructions в tool descriptions
- [ ] Примеры malicious tool schemas
- [ ] Detection methods
- [ ] Создать RU версию
- [ ] Написать тест

---

## Phase 2: Invisible Prompts (HIGH Priority)

### Task 2.1: Invisible Prompts Lesson
- [x] Создать `en/03-attack-vectors/01-prompt-injection/04-invisible-prompts.md`
- [x] Описать font injection technique
- [x] Описать zero-width characters (U+200B, U+FEFF)
- [x] Добавить detection code
- [x] Создать RU версию
- [x] Написать тест

### Task 2.2: Character Obfuscation Lesson
- [ ] Создать `en/03-attack-vectors/01-prompt-injection/05-character-obfuscation.md`
- [ ] Описать homoglyphs (Cyrillic/Latin)
- [ ] Описать leetspeak evasion
- [ ] Описать emoji smuggling
- [ ] Добавить normalization code
- [ ] Создать RU версию
- [ ] Написать тест

### Task 2.3: Invisible Prompts Lab
- [x] Создать `labs/09-invisible-prompts/README.md`
- [x] Создать `labs/09-invisible-prompts/challenge.py`
- [x] Создать payloads directory с примерами
- [ ] Создать solutions с detector
- [ ] Написать тест для lab

---

## Phase 3: Additional Jailbreaks (MEDIUM Priority)

### Task 3.1: Time Bandit Jailbreak Lesson
- [x] Создать урок EN
- [x] Описать temporal confusion technique
- [x] Примеры "pretend it's 1995" prompts
- [ ] Создать RU версию
- [ ] Написать тест

### Task 3.2: Fallacy Failure Lesson
- [x] Создать урок EN
- [x] Описать логические манипуляции
- [x] Примеры invalid premise acceptance
- [ ] Создать RU версию
- [ ] Написать тест

### Task 3.3: Crescendo Multi-Turn Attack Lesson
- [x] Создать урок EN
- [x] Описать gradual erosion technique
- [x] Примеры multi-turn conversations
- [x] CrescendoAttacker tool reference
- [ ] Создать RU версию
- [ ] Написать тест

---

## Phase 4: Defense Techniques (MEDIUM Priority)

### Task 4.1: CaMeL Defense Lesson
- [x] Создать `en/05-defense-strategies/01-detection/31-camel-defense.md`
- [x] Описать protective system layer
- [x] Implementation guide
- [ ] Создать RU версию
- [ ] Написать тест

### Task 4.2: SecAlign Defense Lesson
- [x] Создать урок EN
- [x] Описать preference optimization
- [x] ~0% injection success results
- [ ] Создать RU версию
- [ ] Написать тест

### Task 4.3: ZEDD Defense Lesson
- [x] Создать урок EN
- [x] Описать Zero-Shot Embedding Drift Detection
- [x] Embedding space shift analysis
- [ ] Создать RU версию
- [ ] Написать тест

---

## Phase 5: Multimodal + Integration (MEDIUM Priority)

### Task 5.1: MM-PoisonRAG Lesson
- [x] Создать урок EN
- [x] Описать multimodal RAG poisoning (ICLR 2026)
- [x] Image + text combined attacks
- [ ] Создать RU версию
- [ ] Написать тест

### Task 5.2: Update LLM08 Vector Embeddings
- [ ] Обновить `en/02-threat-landscape/01-owasp-llm-top10/08-LLM08-vector-embeddings.md`
- [ ] Добавить multimodal attacks section
- [ ] Добавить MM-PoisonRAG reference
- [ ] Обновить RU версию

### Task 5.3: Update CURRICULUM.md
- [ ] Добавить все новые уроки в CURRICULUM.md
- [ ] Обновить счётчики уроков
- [ ] Проверить навигацию

---

## Phase 6: TDD Infrastructure

### Task 6.1: Create Test Framework
- [x] Создать `tests/academy/test_lesson_structure.py`
- [ ] Создать `tests/academy/test_code_examples.py`
- [x] Создать `tests/academy/test_bilingual.py`
- [ ] Создать `tests/academy/test_curriculum.py`

### Task 6.2: Create Lesson Linter
- [x] Создать `tests/academy/lint_lessons.py`
- [x] Validate required sections
- [x] Validate code block syntax
- [x] Validate links

### Task 6.3: Pre-commit Integration
- [ ] Добавить academy-lint hook в `.pre-commit-config.yaml`

---

## Summary

| Phase | Tasks | Estimated |
|-------|-------|-----------|
| Phase 1 | 4 lessons | 2 hours |
| Phase 2 | 2 lessons + 1 lab | 1.5 hours |
| Phase 3 | 3 lessons | 1 hour |
| Phase 4 | 3 lessons | 1 hour |
| Phase 5 | 2 lessons + 2 updates | 1 hour |
| Phase 6 | TDD infra | 1 hour |
| **Total** | **14 lessons + 1 lab + TDD** | **~7.5 hours** |

---

*Tasks v1.0 — 28 января 2026*
