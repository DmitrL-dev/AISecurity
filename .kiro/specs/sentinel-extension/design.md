# SENTINEL Guard Extension — Design

> **Компонент:** saas/sentinel-extension/
> **Статус:** Implemented (MVP)
> **Дата:** 2026-02-12

---

## 1. Архитектура

```
┌───────────────────────────────────────────────────────────────┐
│                   SENTINEL Guard Extension                     │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐    │
│  │  Content.js   │    │ Background.js│    │  Popup.html  │    │
│  │  (per tab)    │───►│  (Service    │◄──►│  + popup.js  │    │
│  │              │    │   Worker)    │    │              │    │
│  └──────┬───────┘    └──────┬───────┘    └──────────────┘    │
│         │                   │                                  │
│  DOM injection        ┌─────┴──────┐                          │
│  Prompt intercept     │            │                          │
│                  ┌────┴───┐  ┌────┴────┐                     │
│                  │ Cache  │  │  Stats  │                     │
│                  │ (Map)  │  │ (local) │                     │
│                  └────────┘  └─────────┘                     │
│                       │                                        │
│                  POST /analyze                                 │
│                       │                                        │
│              ┌────────┴────────┐                              │
│              │ SENTINEL Shield │                              │
│              │     API         │                              │
│              └─────────────────┘                              │
└───────────────────────────────────────────────────────────────┘
```

---

## 2. Компоненты

### 2.1 Content Script (content.js)

**Ответственность:** DOM-инжекция на AI-платформах, перехват промптов.

```javascript
// Поддерживаемые селекторы (по платформам)
const PLATFORM_SELECTORS = {
  'chatgpt.com': 'textarea[data-id="root"]',
  'claude.ai': 'div[contenteditable="true"]',
  'gemini.google.com': 'rich-textarea',
  // ... остальные платформы
};

// Стратегия перехвата:
// 1. MutationObserver для обнаружения textarea
// 2. Event delegation для Submit (keydown Enter, button click)
// 3. Отправка SCAN_TEXT message в background
```

### 2.2 Background Service Worker (background.js)

**Ответственность:** API-коммуникация, кеширование, badge, статистика.

| Функция | Описание |
|---------|----------|
| `getConfig()` | Загрузка настроек из chrome.storage.sync |
| `scanText(text)` | Сканирование через POST /analyze (с кешем) |
| `updateBadge(result)` | Badge: ✅ safe (зелёный), ⚠ warn (жёлтый), ⛔ block (красный) |
| `incrementStats(result)` | Обновление счётчиков в chrome.storage.local |
| `hashText(text)` | Простой хеш для ключей кеша |

**Кеш:**
- In-memory `Map` (очищается при sleep Service Worker)
- TTL: 5 минут
- Ключ: hashText(prompt)

**Fail-open:**
- При ошибке API → `{ verdict: 'allow', error: error.message }`
- Никогда не блокирует пользователя при сбое

### 2.3 Popup UI (popup.html + popup.js)

**Ответственность:** Настройки пользователя, отображение статистики.

| Элемент | ID | Тип |
|---------|-----|-----|
| Protection toggle | `enableToggle` | checkbox |
| Auto-scan toggle | `autoScan` | checkbox |
| Sensitivity | `sensitivity` | select (low/medium/high) |
| API Key | `apiKey` | input text |
| Status card | `statusCard` | div |
| Total scans | `totalScans` | span |
| Total blocked | `totalBlocked` | span |
| Total warned | `totalWarned` | span |
| Total safe | `totalSafe` | span |
| Last scan result | `lastScanResult` | div |

---

## 3. Data Flow

```
User types prompt → Content Script intercepts
    → chrome.runtime.sendMessage({ type: 'SCAN_TEXT', text })
    → Background: scanText(text)
        → Check cache (hashText)
        → Cache miss → POST api.sentinel.dev/analyze
        → Response: { verdict, risk_score, threats }
        → Update cache
        → updateBadge(result)
        → incrementStats(result)
    → sendResponse(result)
    → Content Script: показывает inline indicator
```

---

## 4. API Contract

### POST /analyze

```json
// Request
{
  "text": "user prompt here",
  "zone": "browser"
}

// Response
{
  "verdict": "allow" | "warn" | "block",
  "risk_score": 0.0-1.0,
  "threats": [
    {
      "threat_type": "prompt_injection",
      "engine": "semantic_entropy",
      "confidence": 0.95
    }
  ]
}
```

Headers:
- `Content-Type: application/json`
- `User-Agent: sentinel-guard-extension/0.1.0`
- `X-API-Key: <optional>`

---

## 5. Storage Schema

### chrome.storage.sync (synced)
```json
{
  "enabled": true,
  "autoScan": true,
  "sensitivity": "medium",
  "apiKey": "",
  "apiUrl": "https://api.sentinel.dev"
}
```

### chrome.storage.local (local)
```json
{
  "totalScans": 0,
  "totalBlocked": 0,
  "totalWarned": 0,
  "totalSafe": 0,
  "threatTypes": { "prompt_injection": 5, "jailbreak": 2 },
  "lastScan": {
    "verdict": "block",
    "risk_score": 0.94,
    "timestamp": 1707753600000
  }
}
```

---

## 6. Permissions Audit

| Permission | Обоснование |
|------------|-------------|
| `storage` | Config (sync) + stats (local) |
| `activeTab` | Доступ к текущей вкладке для content script |
| `host_permissions` (11 AI сайтов) | Инжекция content script |
| `host_permissions` (api.sentinel.dev) | API вызовы |

---

## 7. Verification Plan

### Unit Tests
```bash
# Тестирование хеширования и кеша
node --test background.test.js
```

### Manual Testing
1. Загрузить как unpacked extension в chrome://extensions
2. Открыть chatgpt.com → ввести промпт
3. Проверить badge обновляется
4. Открыть popup → проверить статистику
5. Отключить → проверить что сканирование остановлено
