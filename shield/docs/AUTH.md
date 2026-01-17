# SENTINEL Shield Authentication

## Overview

Shield provides enterprise-grade authentication with JWT support, rate limiting, and HashiCorp Vault integration.

---

## JWT Authentication

### Supported Algorithms

| Algorithm | Type | Use Case |
|-----------|------|----------|
| **HS256** | HMAC-SHA256 | Shared secret (simple) |
| **RS256** | RSA-SHA256 | Public/private keys (enterprise) |

### Configuration

```c
#include "szaa_jwt.h"

// HS256 configuration
jwt_config_t config = {
    .algorithm = JWT_ALG_HS256,
    .secret = "your-256-bit-secret",
    .secret_len = 32,
    .issuer = "shield",
    .audience = "api",
    .clock_skew = 60  // seconds
};

// Verify token
jwt_claims_t claims;
jwt_err_t err = jwt_verify(token, &config, &claims);
if (err == JWT_OK) {
    printf("User: %s\n", claims.sub);
}
```

### Claims Structure

```c
typedef struct {
    char iss[64];      // Issuer
    char sub[128];     // Subject (user ID)
    char aud[64];      // Audience
    uint64_t exp;      // Expiration time
    uint64_t iat;      // Issued at
    uint64_t nbf;      // Not before
    char jti[64];      // JWT ID
} jwt_claims_t;
```

---

## Rate Limiting

### Token Bucket Algorithm

Shield implements token bucket rate limiting per IP or per user.

```c
#include "rate_limiter.h"

// Configuration
rate_limit_config_t config = {
    .bucket_size = 100,      // Max tokens
    .refill_rate = 10,       // Tokens per second
    .key_type = RATE_KEY_IP, // Per IP address
};

// Initialize
rate_limiter_t *limiter = rate_limiter_create(&config);

// Check request
rate_limit_result_t result;
if (rate_limiter_check(limiter, client_ip, &result)) {
    // Request allowed
    handle_request();
} else {
    // Rate limited
    send_429(result.retry_after);
}
```

### Response Headers

| Header | Description |
|--------|-------------|
| `X-RateLimit-Limit` | Bucket size |
| `X-RateLimit-Remaining` | Tokens left |
| `X-RateLimit-Reset` | Next refill time |
| `Retry-After` | Seconds until retry (on 429) |

---

## Vault Integration

### Secret Management

Shield can fetch secrets from HashiCorp Vault.

```c
#include "vault_client.h"

// Configuration
vault_config_t config = {
    .addr = "https://vault.example.com:8200",
    .token = getenv("VAULT_TOKEN"),
    .mount_path = "secret",
    .cache_ttl = 300,  // seconds
};

// Initialize client
vault_client_t *client = vault_client_create(&config);

// Fetch secret
char *jwt_secret = vault_get(client, "shield/jwt-secret");

// Client handles caching and auto-renewal
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `VAULT_ADDR` | Vault server address |
| `VAULT_TOKEN` | Authentication token |
| `VAULT_CACERT` | CA certificate path |

---

## HTTP Middleware

### Middleware Chain

```
Request → JWT Middleware → Rate Limit Middleware → Handler
```

### Configuration

```c
#include "http_middleware.h"

// Whitelist paths (no auth required)
const char *whitelist[] = {
    "/health",
    "/metrics",
    "/v1/public/*",
    NULL
};

// Apply middleware
http_middleware_config_t mw_config = {
    .jwt_enabled = true,
    .jwt_config = &jwt_config,
    .rate_limit_enabled = true,
    .rate_limit_config = &rate_config,
    .whitelist = whitelist,
};

http_server_set_middleware(server, &mw_config);
```

---

## Security Best Practices

1. **JWT Secret** — Use 256+ bit secrets, rotate regularly
2. **Rate Limits** — Set per-endpoint limits for sensitive operations
3. **Vault** — Never hardcode secrets, use Vault or env vars
4. **HTTPS** — Always use TLS in production

---

## See Also

- [Architecture](ARCHITECTURE.md)
- [API Reference](API.md)
- [Configuration](CONFIGURATION.md)
