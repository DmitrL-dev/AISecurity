# Report 08: Admin Panel + Sentry DSN на dev.hh.ru

---
**Поля формы:**

- **Название:** Обход контроля доступа к Admin Panel + эксплуатируемый Sentry DSN на dev.hh.ru
- **Уровень опасности:** Средний
- **CWE:** CWE-284 (Improper Access Control)
- **CVE:** (не указывать)
- **Скоуп:** dev.hh.ru

---

## Где обнаружено

`GET https://dev.hh.ru/admin`

## Описание уязвимости

Dev-окружение `dev.hh.ru` (в scope) содержит **две эксплуатируемые уязвимости**:

**1. Обход контроля доступа к Admin Panel**
`/admin` на dev.hh.ru → `200 OK` (141KB), на prod `hh.ru/admin` → `301 redirect`. Это разница в контроле доступа, позволяющая: изучить структуру admin-интерфейса, обнаружить admin-only endpoints, извлечь debug-версии JavaScript.

**2. Эксплуатируемый Sentry DSN**
В JS-коде admin page раскрыт полный Sentry DSN:
```javascript
window.globalServiceVars.devHhFront.sentryDSN = 'https://7dac71be294dd57aea0...'
window.globalServiceVars.devHhFront.pageName = 'Admin'
```

Sentry DSN — это **credentials** для API. Атакующий может: inject fake errors (загрязнение мониторинга), получить source maps, DoS на Sentry quota.

## Шаги воспроизведения

### 1. Доступ к admin panel

```bash
curl -s -o /dev/null -w "%{http_code}:%{size_download}" \
  -b "X_Bug_Bounty=security_standoff" \
  -A "Mozilla/5.0" \
  "https://dev.hh.ru/admin"
```
→ `200:141565` (141KB admin page)

Сравнение с prod:
```bash
curl -s -o /dev/null -w "%{http_code}:%{size_download}" \
  -A "Mozilla/5.0" "https://hh.ru/admin"
```
→ `301:162` (redirect)

### 2. Sentry DSN в HTML

В HTML-коде:
```javascript
window.globalServiceVars.devHhFront.pageName = 'Admin';
window.globalServiceVars.devHhFront.sentryDSN = 'https://7dac71be294dd57aea0...';
window.globalServiceVars.devHhFront.requestId = '17713165228139745a3d8c9b64afd023';
```

### 3. Dev vs Prod

| Endpoint | dev.hh.ru | hh.ru (prod) |
|----------|-----------|-------------|
| `/admin` | **200 (141KB)** | 301 (162B) |
| `/account/login` | 000 (timeout) | 200 (252KB) |

## Влияние на безопасность

1. **Admin Panel Exposure:** Раскрытие структуры admin-интерфейса, JS-файлов с debug info.
2. **Sentry DSN Abuse:** Fake error injection → загрязнение мониторинга, маскировка реальных инцидентов.
3. **Source Maps:** Через Sentry DSN возможен доступ к source maps → раскрытие серверного кода.

**Рекомендации:** Закрыть dev.hh.ru через VPN/IP whitelist, удалить Sentry DSN из frontend, добавить 301/403 для `/admin` на dev.

## Дополнительные ссылки

- CWE-284: https://cwe.mitre.org/data/definitions/284.html
- CWE-215: https://cwe.mitre.org/data/definitions/215.html
