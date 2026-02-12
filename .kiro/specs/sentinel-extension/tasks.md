# SENTINEL Guard Extension — Tasks

> **Компонент:** saas/sentinel-extension/
> **Статус:** MVP implemented, roadmap below
> **Дата:** 2026-02-12

---

## Реализованные задачи (MVP)

- [x] T-1: Manifest V3 конфигурация (manifest.json)
- [x] T-2: Background Service Worker (background.js)
  - [x] T-2.1: Shield API интеграция (scanText)
  - [x] T-2.2: In-memory кеш с TTL 5 мин
  - [x] T-2.3: Badge updates (✅/⚠/⛔)
  - [x] T-2.4: Stats tracking (incrementStats)
  - [x] T-2.5: Message handlers (SCAN_TEXT, GET_STATS, GET_CONFIG)
  - [x] T-2.6: Install handler (defaults)
- [x] T-3: Content Script (content.js)
  - [x] T-3.1: DOM injection на AI-платформах
  - [x] T-3.2: Prompt interception
  - [x] T-3.3: CSS indicators (content.css)
- [x] T-4: Popup UI
  - [x] T-4.1: HTML layout (popup.html)
  - [x] T-4.2: Settings persistence (popup.js)
  - [x] T-4.3: Stats display
  - [x] T-4.4: Last scan result
- [x] T-5: Иконки (16/32/48/128 px)

---

## Следующие задачи (Roadmap)

- [ ] T-6: Chrome Web Store подготовка
  - [ ] T-6.1: Скриншоты для листинга
  - [ ] T-6.2: Privacy policy
  - [ ] T-6.3: Описание и категория
  - [ ] T-6.4: Submit на review
- [ ] T-7: Edge Add-ons публикация
- [ ] T-8: Firefox Add-ons адаптация (MV2/MV3)
- [ ] T-9: Персистентный кеш (storage.local)
- [ ] T-10: UI improvements
  - [ ] T-10.1: Dark mode popup
  - [ ] T-10.2: Threat details в popup
  - [ ] T-10.3: Notification при block
- [ ] T-11: Добавить поддержку новых AI-сайтов
  - [ ] T-11.1: Grok (x.com/grok)
  - [ ] T-11.2: Pi.ai
  - [ ] T-11.3: Ollama Web UI
