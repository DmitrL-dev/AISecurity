# Требования: Закрытие Documentation Gaps

## Контекст

После реструктуризации README и создания билингвальной Academy (48 EN + 48 RU уроков) остались следующие гапы:

---

## FR-1: Missing Mid-Level Lesson 08

**Приоритет:** High

**Описание:** В Mid-Level EN path пропущен урок 08 (между 07-compliance-reporting.md и 09-custom-engines.md).

**Acceptance Criteria:**
- [ ] Создан `docs/academy/mid-level/en/08-monitoring.md`
- [ ] Создан `docs/academy/mid-level/ru/08-monitoring.md` (если отсутствует)
- [ ] Урок о мониторинге и observability AI систем
- [ ] Ссылки в README работают

---

## FR-2: CONTRIBUTING.md

**Приоритет:** High

**Описание:** README ссылается на `./docs/CONTRIBUTING.md`, но файл отсутствует.

**Acceptance Criteria:**
- [ ] Создан `docs/CONTRIBUTING.md`
- [ ] Code of Conduct секция
- [ ] Инструкции по PR
- [ ] Стиль кода (black, ruff)
- [ ] Процесс review

---

## FR-3: Academy RU READMEs

**Приоритет:** Medium

**Описание:** В /ru/ директориях нужны README.md файлы.

**Acceptance Criteria:**
- [ ] `docs/academy/beginners/ru/README.md` существует и актуален
- [ ] `docs/academy/mid-level/ru/README.md` существует и актуален  
- [ ] `docs/academy/expert/ru/README.md` существует и актуален

---

## FR-4: CHANGELOG.md

**Приоритет:** Medium

**Описание:** README ссылается на `docs/CHANGELOG.md`, нужен актуальный changelog.

**Acceptance Criteria:**
- [ ] Создан `docs/CHANGELOG.md`
- [ ] Keep-a-Changelog формат
- [ ] Записи за январь 2026
- [ ] Ссылки на PR/issues

---

## FR-5: Benchmarks Table

**Приоритет:** Low

**Описание:** Эксперты хотят видеть accuracy/latency данные.

**Acceptance Criteria:**
- [ ] Добавить в BRAIN секцию README таблицу benchmarks
- [ ] Precision/Recall/F1 метрики
- [ ] P50/P95/P99 latency

---

## NFR-1: Consistency

- Все документы должны следовать единому стилю форматирования
- EN и RU версии должны быть синхронизированы по структуре

---

## Приоритеты

| ID | Gap | Priority | Effort |
|----|-----|----------|--------|
| FR-1 | Mid-Level 08 | High | 20 мин |
| FR-2 | CONTRIBUTING.md | High | 30 мин |
| FR-3 | RU READMEs | Medium | 15 мин |
| FR-4 | CHANGELOG.md | Medium | 30 мин |
| FR-5 | Benchmarks | Low | 45 мин |

**Total estimated effort:** ~2.5 часа
