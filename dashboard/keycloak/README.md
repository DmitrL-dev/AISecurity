# Keycloak Authentication Server

SENTINEL Dashboard authentication infrastructure using Keycloak.

## Quick Start

```bash
# Start Keycloak
docker-compose up -d

# Wait for Keycloak to be ready
curl -f http://localhost:8081/health/ready

# Access Admin Console
open http://localhost:8081/admin
# Login: admin / sentinel-admin-dev
```

## Configuration

### Environment Variables

Create `.env` file:

```bash
# Keycloak Admin
KC_ADMIN_PASSWORD=sentinel-admin-dev

# PostgreSQL
POSTGRES_PASSWORD=keycloak-db-dev
```

### Realm Setup

The realm is auto-imported on first start from `realm-sentinel.json`.

**Realm:** `sentinel`
**Client:** `sentinel-dashboard`

### Test Users

| Username | Password | Role | 2FA |
|----------|----------|------|-----|
| admin@sentinel.local | Admin123! | admin | Required |
| analyst@sentinel.local | Analyst123! | analyst | Optional |
| viewer@sentinel.local | Viewer123! | viewer | Optional |

## Production Notes

1. **Change default passwords**
2. **Enable HTTPS** (`KC_HOSTNAME_STRICT_HTTPS=true`)
3. **Use external PostgreSQL** with proper credentials
4. **Configure HA** with multiple instances

## Files

```
keycloak/
├── docker-compose.yml      # Keycloak + PostgreSQL
├── realm-sentinel.json     # Realm configuration
├── .env.example            # Environment template
└── README.md               # This file
```
