# Dashboard Auth — Requirements

> **Фаза:** Phase 6 Dashboard V3
> **Статус:** Draft
> **Дата:** 2026-01-29

---

## 1. Обзор

Реализация полноценной системы аутентификации и авторизации для SENTINEL Dashboard на базе Keycloak с поддержкой OIDC, RBAC и TOTP 2FA.

---

## 2. Функциональные требования

### FR-1: Интеграция с Keycloak

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-1.1 | Dashboard должен аутентифицировать пользователей через Keycloak OIDC | P0 |
| FR-1.2 | Поддержка SSO между Dashboard и другими SENTINEL компонентами | P1 |
| FR-1.3 | Автоматическое обновление access tokens через refresh tokens | P0 |
| FR-1.4 | Logout должен инвалидировать сессию на Keycloak (SLO) | P0 |

### FR-2: RBAC (Role-Based Access Control)

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-2.1 | Роль **admin** — полный доступ ко всем функциям | P0 |
| FR-2.2 | Роль **analyst** — анализ, просмотр audit logs, engine view | P0 |
| FR-2.3 | Роль **viewer** — только чтение (dashboard, metrics) | P0 |
| FR-2.4 | Роль **api-only** — только API доступ (без UI) | P1 |
| FR-2.5 | Кастомные роли с granular permissions (план развития) | P2 |

### FR-3: Двухфакторная аутентификация (2FA)

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-3.1 | Поддержка TOTP (Google Authenticator, Authy) | P0 |
| FR-3.2 | Принудительное включение 2FA для роли admin | P0 |
| FR-3.3 | Опциональное 2FA для остальных ролей | P1 |
| FR-3.4 | Backup codes для восстановления доступа | P1 |

### FR-4: UI Компоненты

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-4.1 | Страница логина с редиректом на Keycloak | P0 |
| FR-4.2 | Отображение текущего пользователя и роли в header | P0 |
| FR-4.3 | Страница профиля пользователя | P1 |
| FR-4.4 | Admin панель управления пользователями (через Keycloak) | P2 |

### FR-5: API Security

| ID | Требование | Приоритет |
|----|------------|-----------|
| FR-5.1 | Все API endpoints защищены JWT валидацией | P0 |
| FR-5.2 | RBAC проверка на уровне API route | P0 |
| FR-5.3 | API keys для machine-to-machine (M2M) доступа | P1 |
| FR-5.4 | Rate limiting per user/token | P1 |

---

## 3. Нефункциональные требования

### NFR-1: Безопасность

| ID | Требование |
|----|------------|
| NFR-1.1 | Tokens хранятся в HttpOnly cookies (не localStorage) |
| NFR-1.2 | CSRF protection через SameSite cookies |
| NFR-1.3 | Все auth endpoints через HTTPS |
| NFR-1.4 | Session timeout: 30 минут inactive, 24 часа absolute |
| NFR-1.5 | Brute-force protection (Keycloak built-in) |

### NFR-2: Compliance

| ID | Требование |
|----|------------|
| NFR-2.1 | Audit log всех auth событий (login, logout, failed attempts) |
| NFR-2.2 | ФЗ-152: согласие на обработку ПДн при регистрации |
| NFR-2.3 | GDPR: право на удаление аккаунта |

### NFR-3: Performance

| ID | Требование |
|----|------------|
| NFR-3.1 | Token validation <10ms |
| NFR-3.2 | Login flow <3 секунды (UX) |

---

## 4. User Stories

### US-1: Аутентификация

```gherkin
GIVEN я неаутентифицированный пользователь
WHEN я открываю Dashboard
THEN меня редиректит на Keycloak login page

GIVEN я ввёл верные credentials и TOTP код
WHEN я нажимаю Login
THEN меня редиректит обратно на Dashboard с активной сессией
```

### US-2: Авторизация

```gherkin
GIVEN я залогинен как analyst
WHEN я пытаюсь открыть Settings → Users
THEN я вижу сообщение "Access Denied" или страница скрыта

GIVEN я залогинен как admin
WHEN я пытаюсь открыть Settings → Users
THEN я вижу список пользователей и могу управлять ими
```

### US-3: Logout

```gherkin
GIVEN я залогинен
WHEN я нажимаю Logout
THEN моя сессия инвалидируется в Dashboard И в Keycloak
AND я редиректюсь на login page
```

---

## 5. Acceptance Criteria

- [ ] AC-1: Login через Keycloak работает
- [ ] AC-2: 2FA TOTP енфорсится для admin
- [ ] AC-3: Роли (admin/analyst/viewer) ограничивают доступ
- [ ] AC-4: Logout инвалидирует сессию
- [ ] AC-5: API endpoints защищены JWT
- [ ] AC-6: Audit log фиксирует auth события

---

## 6. Out of Scope (Phase 6)

- Social login (Google, GitHub) — Phase 7+
- SAML SSO — Phase 7+
- Custom roles UI — Phase 7+
- Password reset flow (handled by Keycloak)

---

## 7. Dependencies

- Keycloak instance (self-hosted или cloud)
- Dashboard V2 MVP (current)
- PostgreSQL для user metadata (optional)

---

## 8. Risks

| Риск | Митигация |
|------|-----------|
| Keycloak downtime → auth unavailable | HA Keycloak cluster |
| Token leakage | HttpOnly cookies, short expiry |
| Complexity | Использовать next-auth с Keycloak adapter |
