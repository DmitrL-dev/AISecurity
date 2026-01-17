# Shield Auth Migration — Tasks

## Phase 1: JWT Implementation

- [x] **Task 1.1**: Создать `shield/src/protocols/szaa_jwt.h`
  - Определить структуры jwt_config_t, jwt_claims_t
  - Определить API функции

- [x] **Task 1.2**: Создать `shield/src/protocols/szaa_jwt.c`
  - Base64 URL decode для header/payload
  - JSON parsing для claims
  - HS256 HMAC verification (wolfSSL)
  - RS256 RSA verification (wolfSSL)

- [x] **Task 1.3**: Создать unit tests для JWT
  - test_jwt_hs256_valid
  - test_jwt_hs256_expired
  - test_jwt_hs256_invalid_sig
  - test_jwt_rs256_valid

---

## Phase 2: Rate Limiting

- [x] **Task 2.1**: Создать `shield/src/core/rate_limiter.h`
  - Определить структуры rate_limit_config_t, rate_limit_result_t
  - Определить API функции

- [x] **Task 2.2**: Создать `shield/src/core/rate_limiter.c`
  - Token bucket алгоритм
  - Hashtable для buckets (per IP/user)
  - Thread-safe доступ (mutex)
  - Автоматический refill

- [x] **Task 2.3**: Создать unit tests для rate limiter
  - test_rate_limit_pass
  - test_rate_limit_block
  - test_rate_limit_refill
  - test_rate_limit_concurrent

---

## Phase 3: Vault Integration

- [x] **Task 3.1**: Создать `shield/src/utils/vault_client.h`
  - Определить структуры vault_config_t
  - Определить API функции

- [x] **Task 3.2**: Создать `shield/src/utils/vault_client.c`
  - HTTP client (libcurl)
  - JSON response parsing
  - Local cache с TTL
  - Auto-renewal

- [x] **Task 3.3**: Создать unit tests для Vault client
  - test_vault_fetch (mock server)
  - test_vault_cache
  - test_vault_fallback

---

## Phase 4: HTTP Integration

- [x] **Task 4.1**: Создать HTTP middleware модуль
  - Создать `include/http/http_middleware.h`
  - Создать `src/http/http_middleware.c`
  - JWT middleware hook
  - Rate limiting hook
  - Whitelist конфигурация

- [x] **Task 4.2**: Модифицировать `shield/src/http/http_server.c`
  - Добавить include http_middleware.h
  - Интегрировать middleware в handle_connection
  - Добавить rate limit headers

- [x] **Task 4.3**: Проверить сборку
  - Сборка libshield.a успешна
  - http_middleware.o включён в библиотеку

---

## Phase 5: Documentation & Cleanup

- [x] **Task 5.1**: Архивация Gateway
  - Move src/gateway/ → _archive/gateway/
  - Создан _archive/README.md

- [x] **Task 5.2**: Проверить docker-compose
  - docker-compose.full.yml не содержит gateway
  - Обновление не требуется

---

## Acceptance Criteria

| Критерий | Метрика |
|----------|---------|
| JWT verification | < 1ms латентность |
| Rate limiting | < 0.1ms латентность |
| Test coverage | > 80% для новых файлов |
| Zero breaking changes | Существующие JWT работают |

---

**Created:** 2026-01-09
