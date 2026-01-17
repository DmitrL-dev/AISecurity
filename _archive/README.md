# Gateway Archive

> **⚠️ LEGACY CODE - Archived 2026-01-09**

This directory contains the archived Go-based Gateway component.
As of SENTINEL Dragon v4.1, **Shield** (C library) has replaced Gateway.

## Why Archived?

The Gateway provided:
- JWT authentication
- OAuth integration  
- Rate limiting
- WebSocket hub
- HashiCorp Vault integration

These features have been **migrated to Shield**:
- `shield/src/protocols/szaa_jwt.c` - JWT verification
- `shield/src/core/rate_limiter.c` - Token bucket rate limiting
- `shield/src/utils/vault_client.c` - Vault secrets management
- `shield/src/http/http_middleware.c` - HTTP auth middleware

## Do Not Use

This code is preserved for **historical reference only**.
Do not build, deploy, or depend on this Gateway.

## Migration Guide

See `.kiro/specs/shield-auth-migration/` for the detailed SDD specification.

## Original Structure

```
gateway/
├── cmd/                  # Entry point
├── configs/              # Configuration files
├── dashboard/            # HTML dashboard (migrated to Shield HTTP)
├── internal/             # Business logic
│   ├── auth/            # → Shield szaa_jwt.c
│   ├── ratelimit/       # → Shield rate_limiter.c
│   ├── vault/           # → Shield vault_client.c
│   └── websocket/       # → Future: Shield WebSocket
└── pkg/                  # Shared packages
```

---

*Archived by SENTINEL SDD workflow*
