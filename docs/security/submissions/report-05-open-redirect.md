# Report 05: Open Redirect

---
**Поля формы:**

- **Название:** Open Redirect через endpoint /redirect — фишинг и кража OAuth-токенов
- **Уровень опасности:** Средний
- **CWE:** CWE-601 (URL Redirection to Untrusted Site)
- **CVE:** (не указывать)
- **Скоуп:** setka.ru

---

## Где обнаружено

`GET https://setka.ru/redirect?to=//evil.com`

## Описание уязвимости

Endpoint `GET /redirect` на setka.ru принимает параметр `to` и выполняет HTTP 302 redirect на указанный URL без валидации домена назначения. Protocol-relative URL (`//evil.com`) обходит проверки.

## Шаги воспроизведения

### 1. Базовый redirect

```bash
curl -s -D - -o /dev/null \
  -b "X_Bug_Bounty=security_standoff" \
  "https://setka.ru/redirect?to=//evil.com"
```
→ `302 Found`, `Location: //evil.com`

Браузер интерпретирует `//evil.com` как protocol-relative URL → перенаправляет на `https://evil.com`.

### 2. Цепочка атаки (Phishing)

Ссылка для жертвы:
```
https://setka.ru/redirect?to=//evil.com/setka-login
```
Жертва видит домен setka.ru, кликает, попадает на фишинговый сайт, вводит credentials.

## Влияние на безопасность

1. **Фишинг:** Атакующий создаёт поддельную страницу логина. Ссылка выглядит легитимной (начинается с setka.ru).
2. **OAuth Token Theft:** Redirect может быть использован для кражи authorization code.
3. **Reputation Damage:** Ссылки с домена setka.ru ведут на вредоносные ресурсы.

**Рекомендации:** Whitelist доменов (*.hh.ru, *.setka.ru), валидация host перед redirect, запрет protocol-relative URLs, промежуточная страница предупреждения.

## Дополнительные ссылки

- CWE-601: https://cwe.mitre.org/data/definitions/601.html
- OWASP Unvalidated Redirects: https://cheatsheetseries.owasp.org/cheatsheets/Unvalidated_Redirects_and_Forwards_Cheat_Sheet.html
