# Shield Auth Migration — Design

## Архитектура

```
┌─────────────────────────────────────────────────────────┐
│                     Shield HTTP Server                   │
│                    (http_server.c)                       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐ │
│  │ JWT Middle  │→→│ Rate Limit  │→→│ Request Handler │ │
│  │   ware      │  │  Middleware │  │                 │ │
│  └──────┬──────┘  └──────┬──────┘  └─────────────────┘ │
│         │                │                              │
│         ▼                ▼                              │
│  ┌─────────────┐  ┌─────────────┐                      │
│  │ JWT Verify  │  │ Token Bucket│                      │
│  │ (szaa_jwt.c)│  │ (rate_lim.c)│                      │
│  └──────┬──────┘  └─────────────┘                      │
│         │                                               │
│         ▼                                               │
│  ┌─────────────┐                                       │
│  │ Vault Client│                                       │
│  │ (vault.c)   │                                       │
│  └─────────────┘                                       │
└─────────────────────────────────────────────────────────┘
```

---

## Компоненты

### 1. JWT Middleware (`szaa_jwt.c`)

```c
typedef struct {
    char *secret;           // HS256 secret
    char *public_key;       // RS256 public key
    char *issuer;           // Expected issuer
    char *audience;         // Expected audience
    int clock_skew_seconds; // Allowed clock skew
} jwt_config_t;

typedef struct {
    char *sub;              // Subject (user ID)
    char *iss;              // Issuer
    char *aud;              // Audience
    time_t exp;             // Expiration
    time_t iat;             // Issued at
    cJSON *custom_claims;   // Custom claims
} jwt_claims_t;

// API
int jwt_init(jwt_config_t *config);
int jwt_verify(const char *token, jwt_claims_t *claims);
void jwt_cleanup(jwt_claims_t *claims);
```

### 2. Rate Limiter (`rate_limiter.c`)

```c
typedef struct {
    int requests_per_minute;
    int burst_size;
    bool per_ip;
    bool per_user;
} rate_limit_config_t;

typedef struct {
    int remaining;
    int limit;
    time_t reset_at;
} rate_limit_result_t;

// API
int rate_limiter_init(rate_limit_config_t *config);
int rate_limiter_check(const char *key, rate_limit_result_t *result);
void rate_limiter_cleanup(void);
```

### 3. Vault Client (`vault_client.c`)

```c
typedef struct {
    char *address;          // Vault address
    char *token;            // Vault token
    char *secret_path;      // Path to secrets
    int cache_ttl_seconds;  // Cache TTL
} vault_config_t;

// API
int vault_init(vault_config_t *config);
int vault_get_secret(const char *key, char **value);
void vault_cleanup(void);
```

---

## Потоки данных

### JWT Verification Flow

```
Request → Extract Authorization header
       → Parse "Bearer <token>"
       → Split header.payload.signature
       → Verify signature (HS256 or RS256)
       → Decode payload (base64)
       → Parse JSON claims
       → Check exp > now
       → Check iss == expected
       → Check aud == expected
       → Return claims or 401
```

### Rate Limiting Flow

```
Request → Extract IP / User ID
       → Hash key
       → Lookup bucket in hashtable
       → Check tokens available
       → If yes: decrement, pass
       → If no: return 429
       → Refill tokens based on time
```

---

## Интеграция с HTTP Server

### Модификации `http_server.c`

```c
// Before
void handle_request(http_request_t *req) {
    route_handler(req);
}

// After
void handle_request(http_request_t *req) {
    // Whitelist check
    if (!is_whitelisted(req->path)) {
        // JWT middleware
        jwt_claims_t claims;
        if (jwt_verify(req->auth_header, &claims) != 0) {
            send_401(req);
            return;
        }
        req->user_id = claims.sub;
        
        // Rate limiting
        rate_limit_result_t rl;
        if (rate_limiter_check(req->remote_ip, &rl) != 0) {
            send_429(req, &rl);
            return;
        }
        add_rate_limit_headers(req, &rl);
    }
    
    route_handler(req);
}
```

---

## Конфигурация

### Новые переменные окружения

```bash
# JWT
SHIELD_JWT_SECRET=<base64-encoded-secret>
SHIELD_JWT_ALGORITHM=HS256  # or RS256
SHIELD_JWT_ISSUER=sentinel
SHIELD_JWT_AUDIENCE=shield-api
SHIELD_JWT_CLOCK_SKEW=30

# Rate Limiting
SHIELD_RATE_LIMIT_RPM=100
SHIELD_RATE_LIMIT_BURST=20
SHIELD_RATE_LIMIT_PER_IP=true
SHIELD_RATE_LIMIT_PER_USER=true

# Vault
SHIELD_VAULT_ADDR=http://vault:8200
SHIELD_VAULT_TOKEN=<token>
SHIELD_VAULT_SECRET_PATH=secret/data/sentinel
SHIELD_VAULT_CACHE_TTL=300
```

---

## Тестирование

| Тест | Описание |
|------|----------|
| test_jwt_hs256 | Валидация HS256 токенов |
| test_jwt_rs256 | Валидация RS256 токенов |
| test_jwt_expired | Отклонение истёкших |
| test_jwt_invalid_sig | Отклонение неверной подписи |
| test_rate_limit_pass | Запрос в пределах лимита |
| test_rate_limit_block | Блокировка при превышении |
| test_rate_limit_refill | Пополнение bucket |
| test_vault_fetch | Получение секрета из Vault |
| test_vault_cache | Кэширование секретов |

---

**Created:** 2026-01-09
