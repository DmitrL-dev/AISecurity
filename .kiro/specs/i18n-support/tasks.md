# i18n Support — Tasks

## Phase 1: Core Infrastructure

- [x] **Task 1.1**: Создать `src/brain/i18n/__init__.py`
  - I18n class
  - Language detection from Accept-Language
  - Translation loader with fallback

- [x] **Task 1.2**: Создать translation files
  - locales/en.json (50 keys)
  - locales/ru.json (50 keys)
  - locales/zh.json (50 keys)

---

## Translation Categories

- [x] app — Name, description
- [x] verdicts — allow, warn, block
- [x] threats — injection, pii, jailbreak, etc.
- [x] errors — validation, rate_limit, unauthorized
- [x] messages — analyzing, complete, safe
- [x] engines — detection engine names
- [x] status — healthy, degraded, ready

---

## Acceptance Criteria

| Критерий | Метрика | Статус |
|----------|---------|--------|
| Languages | EN, RU, ZH | ✅ |
| Keys per language | ~50 | ✅ |
| Fallback | EN default | ✅ |

---

**Created:** 2026-01-09
**Completed:** 2026-01-09
