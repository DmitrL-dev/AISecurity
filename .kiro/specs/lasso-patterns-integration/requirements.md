# Requirements: Lasso Patterns Integration

## Обзор

Интеграция паттернов детекции prompt injection из open-source проекта [claude-hooks](https://github.com/lasso-security/claude-hooks) от Lasso Security в SENTINEL IMMUNE engine.

## Источник

- **Репозиторий:** https://github.com/lasso-security/claude-hooks
- **Документация:** https://www.lasso.security/blog/the-hidden-backdoor-in-claude-coding-assistant
- **Лицензия:** Проверить совместимость

---

## Функциональные требования

### REQ-LP-001: Импорт категорий паттернов
**EARS:** WHEN система обрабатывает входящий текст, THEN она ДОЛЖНА проверять его на соответствие 5 категориям паттернов Lasso.

Категории:
1. Instruction Override (HIGH)
2. Role-Playing/DAN (HIGH)
3. Encoding/Obfuscation (MEDIUM)
4. Context Manipulation (HIGH)
5. Instruction Smuggling (HIGH)

### REQ-LP-002: Формат паттернов
**EARS:** WHEN добавляются новые паттерны, THEN они ДОЛЖНЫ соответствовать существующему формату `jailbreaks.yaml`.

Маппинг:
- Lasso `high` → SENTINEL `critical`
- Lasso `medium` → SENTINEL `high`
- Lasso `low` → SENTINEL `medium`

### REQ-LP-003: Дедупликация
**EARS:** WHEN паттерн уже существует в `jailbreaks.yaml`, THEN система НЕ ДОЛЖНА добавлять дубликат.

### REQ-LP-004: Attribution
**EARS:** WHEN паттерн добавлен из Lasso, THEN он ДОЛЖЕН содержать комментарий с источником.

Формат: `# Source: lasso-security/claude-hooks`

### REQ-LP-005: Тестирование паттернов
**EARS:** WHEN паттерн добавлен, THEN он ДОЛЖЕН быть покрыт тестом в `tests/patterns/`.

---

## Нефункциональные требования

### REQ-LP-NFR-001: Производительность
Добавление паттернов НЕ ДОЛЖНО увеличивать время обработки запроса более чем на 5%.

### REQ-LP-NFR-002: Совместимость
Паттерны ДОЛЖНЫ работать с Python regex engine (re module).

---

## Критерии приёмки

- [ ] 50+ паттернов добавлены в `jailbreaks.yaml`
- [ ] Все паттерны сгруппированы по категориям
- [ ] Attribution комментарии добавлены
- [ ] Тесты проходят для каждой категории
- [ ] Документация обновлена

---

## Ссылки

1. [Lasso Claude-Hooks README](https://github.com/lasso-security/claude-hooks)
2. [SENTINEL R&D Analysis](../../../docs/rnd/rnd_lasso_claude_hooks.md)
3. [AI Security Digest Week 1](../../../docs/rnd/2026-01-08_digest_week1.md)
