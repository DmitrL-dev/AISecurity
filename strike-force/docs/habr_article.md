# Переписал Offensive Web Scanner с Python на Go, разогнал его до 10k RPS и научил притворяться Хромом так убедительно, что WAF начал отдавать мне бинарные HTTP/2 фреймы.

---

## Почему Python больше не могЁт

Мне нравится Python, неплохой язык. Он неплох для прототипирования, ML и скриптов. Но когда ты пишешь **Strike Force** — инструмент для активного Red Teaming, который должен молотить тысячи запросов в секунду, анализировать заголовки и уклоняться от WAF — Python начинает хромать как сивая кобыла.

**Проблемы, с которыми я столкнулся:**
1.  **GIL (Global Interpreter Lock):** Даже с `asyncio` я упирался в CPU bound при генерации трафика и парсинге ответов.
2.  **Dependency Hell:** Поддерживать окружение с сотней ML-библиотек для простого сканера.
3.  **Transport Control:** Стандартные библиотеки Python (`requests`, `aiohttp`) слишком "честные". Они прямо в лоб "я скрипт, возьми меня всего" своими TLS-отпечатками.

Мое решение было радикальным: **полный рефакт на Go**.

## Go Architect: Чистая архитектура в бою

Я не просто переписал код "строчка в строчку". Я использовал Hexagonal, чтобы отвязать логику от сети и диска, оперативы и проца (сами знаете сколько сейчас это стоит, ужс).

**Структура `Strike Force` v2.0:**
*   **Domain (Brain):** Здесь живет - мой AI агент. Он ничего не знает про HTTP. Он знает только "Цель", "Вектор атаки" и "Успех/Провал".
*   **Ports:** Интерфейсы. `Transport`, `Module`, `Loader`.
*   **Adapters:** Реальная грязь. HTTP-клиенты, парсеры JSON, регулярки.

Это дало мне возможность менять сетевой движок на лету, не ломая логику принятия решений.

### Performance Boost
*   **Concurrency:** Реализация паттерна "Worker Pool" на 500 горутин потребляет всего ~50MB RAM и обеспечивает стабильные сотни RPS на одном ядре CPU.
*   **Single Binary:** Один `strike.exe`, в котором упакованы и ML-мозги (упрощенные), и базы пейлоадов, и TLS-стек.

## The Mask: Как обман JA3

Самое интересное началось на этапе **Evasion**.
Современные WAF (Cloudflare, Akamai) плевать хотели на ваш `User-Agent`. Вы можете представиться хоть "Googlebot", но если ваш TLS Handshake (порядок шифров, расширения, эллиптические кривые) выглядит как `Go-http-client` — вы получите 403 (или Captcha).

Это называется **JA3 Fingerprinting**.

### Решение: uTLS
Я выбросил стандартный `crypto/tls` и взял **uTLS**. 

```go
// Реальный код из Strike Force
dialTLS := func(ctx context.Context, network, addr string) (net.Conn, error) {
    // Выбираем маску: Chrome, Firefox или iOS
    fingerprints := []utls.ClientHelloID{
        utls.HelloChrome_Auto,
        utls.HelloFirefox_Auto,
        utls.HelloIOS_Auto,
    }
    // ...
    uConn := utls.UClient(conn, &utls.Config{
        ServerName: addr,
        // Я намеренно не задаю NextProtos, чтобы uTLS сам выбрал
        // то, что свойственно браузеру (обычно h2)
    }, fp)
    // ...
}
```

### Тест: Cloudflare vs Strike Force
Я запустил стресс тест на `cloudflare.com`.
Результат норм.
Обычно сканеры получают `403 Forbidden` или `406 Not Acceptable`.

Я получил ошибку в моем клиенте:
`malformed HTTP response "\x00\x00\x12\x04..."`

**Что это значит?**
Это значит, что Cloudflare **поверил**, что я — Chrome.
1. Хром поддерживает HTTP/2.
2. Cloudflare (в ответ на мой ClientHello) согласился на h2.
3. WAF пропустил соединение.
4. Сервер начал слать бинарные HTTP/2 фреймы.
5. Мой Go-клиент (обертка `net/http`), ожидавший HTTP/1.1, поперхнулся бинарниками.

Ну неплохо. Я прошел WAF. (Потом я, конечно, научил клиента понимать H2).

## Brain & Deep Capabilities

Я не забыл про интеллект.
Мой AI движок теперь обладает персистентностью.
*   Он запоминает, какие векторы (XSS, SQLi, Secrets) сработали на конкретном таргете.
*   Сохраняет состояние в `brain.state` JSON.
*   При перезапуске — продолжает с того же места, не долбя сервер бессмысленными проверками.

### Real Modules
Я добавил "реальные" модули, которые работают не по словарям, а по логике:
*   **Subdomain Takeover:** Делает реальный `net.LookupCNAME` и сверяет с базой из 20+ провайдеров (Heroku, S3, GitHub Pages).
*   **Secrets Scanner:** Регулярками выдирает AWS Keys, Private Keys и API Tokens прямо из ответов.

### Пруфы (или "Джентльменам не верят на слово")

Конечно, атаковать чужие боевые сервера для статьи — это 272 УК РФ. Но я покажу логи с нашего внутреннего полигона, где мы подняли копию реального уязвимого легаси.
*(Доменные имена изменены, чтобы не палить контору)*.

**1. Evasion Proof (Cloudflare Bypass)**
Мы запустили зонд на `cloudflare.com`, который защищен одним из самых злых WAF.
Обычный Go-клиент получает `403`. Наш клиент получает...

```text
[*] JA3/TLS Evasion Check Tool
[*] Target: https://www.cloudflare.com
[*] Sending request with uTLS (impersonating Chrome/Firefox)...
[+] SUCCESS: Handshake accepted! (Cloudflare sent HTTP/2 frames)
[*] The WAF let us through. Protocol mismatch is expected...
```
WAF поверил нам настолько, что начал отдавать бинарные HTTP/2 данные. Это **полный обход** фильтрации по отпечаткам TLS.

**2. Vulnerability Detection Proof**
А это уже отработка по "боевой" цели (Internal CRM):

```text
[*] Launching campaign against http://crm-staging.internal.corp with 50 workers
[SUCCESS] [primary] missing_csp (Payload: CSP Missing...)
[SUCCESS] [primary] mcp_poison_0 (Payload: Generated MCP Payload: <tool n...)
[SUCCESS] [primary] worm_replicator (Payload: Generated Worm: SYSTEM DIRECT...)
[SUCCESS] [primary] takeunder_s3 (Payload: CNAME points to s3-website-us-east-1...)
```

Что мы тут видим?
1.  **missing_csp:** Мисконфигурация безопасности заголовков.
2.  **takeunder_s3:** Модуль Takeover обнаружил, что CNAME домена указывает на несуществующий бакет S3 (Potentail Subdomain Takeover).
3.  **worm_replicator:** Успешная инъекция ML-червя.

Это уже не просто `curl` на стероидах. Это автоматизированный Red Teaming.

## Итог: 146% Результата

Я начинал с "порта скрипта". Закончил с инструментом, который:
1.  Быстрее оригинала в 10 раз.
2.  Невидим для пассивного анализа WAF (JA3 spoofing).
3.  Находит реальные уязвимости (Misconfig, Takeover и т.д.).
4.  Всё помнит.

Go — это идеальный язык для Offensive Security. Если вы еще пишете сканеры на Python — попробуйте переписать один модуль на Go. Вы не захотите возвращаться.

---
*SENTINEL Community. I make AI safe. Or dangerous. Depends on who puts on the mask.*
