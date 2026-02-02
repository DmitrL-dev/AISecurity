# Authentication & RBAC Guide

## Overview

SENTINEL Dashboard uses Keycloak for authentication with OIDC and NextAuth.js for session management.

## Roles

| Role | Description | Access |
|------|-------------|--------|
| `admin` | Full access | All pages, settings, API |
| `analyst` | Security analyst | Dashboard, Analyze, Audit, Engines |
| `viewer` | Read-only | Dashboard, Metrics |
| `api-only` | API access | API endpoints only (no UI) |

## Quick Start

### 1. Start Keycloak

```bash
cd dashboard/keycloak
docker-compose up -d
```

Access admin console: http://localhost:8081/admin
- Username: `admin`
- Password: `sentinel-admin-dev`

### 2. Configure Environment

Copy `.env.example` to `.env.local`:

```bash
KEYCLOAK_ISSUER=http://localhost:8081/realms/sentinel
KEYCLOAK_CLIENT_ID=sentinel-dashboard
KEYCLOAK_CLIENT_SECRET=CHANGE_ME_IN_PRODUCTION
AUTH_SECRET=$(openssl rand -base64 32)
AUTH_URL=http://localhost:3000
DATABASE_URL=postgresql://sentinel:sentinel@localhost:5432/sentinel
```

### 3. Test Users

| User | Password | Role | 2FA |
|------|----------|------|-----|
| admin@sentinel.local | Admin123! | admin | Required |
| analyst@sentinel.local | Analyst123! | analyst | Optional |
| viewer@sentinel.local | Viewer123! | viewer | Optional |

## Usage

### Protecting Pages

```tsx
// Use middleware (automatic) - see middleware.ts
// Or use RoleGuard component:
import { RoleGuard } from '@/components/auth';

<RoleGuard roles={["admin"]}>
  <AdminPanel />
</RoleGuard>
```

### Protecting API Routes

```typescript
import { withAuth, withAdmin } from '@/lib/api-auth';

// Any authenticated user
export const GET = withAuth(async (req) => {
  return Response.json({ data: "protected" });
});

// Admin only
export const POST = withAdmin(async (req) => {
  return Response.json({ data: "admin only" });
});
```

### Checking Roles in Components

```tsx
import { useSession } from 'next-auth/react';

function MyComponent() {
  const { data: session } = useSession();
  const roles = (session as any)?.roles || [];
  
  if (roles.includes('admin')) {
    return <AdminView />;
  }
  return <UserView />;
}
```

## Files Structure

```
src/
├── lib/
│   ├── auth.ts         # NextAuth config
│   ├── rbac.ts         # Role permissions
│   ├── api-auth.ts     # API protection
│   └── audit.ts        # Audit logging
├── components/auth/
│   ├── LoginButton.tsx
│   ├── RoleGuard.tsx
│   └── UserMenu.tsx
├── middleware.ts       # Route protection
└── db/
    └── schema/auth.ts  # User/API key schema
```

## Production Checklist

- [ ] Change Keycloak admin password
- [ ] Set proper `KEYCLOAK_CLIENT_SECRET`
- [ ] Generate strong `AUTH_SECRET`
- [ ] Enable HTTPS for all services
- [ ] Configure proper redirect URIs in Keycloak
- [ ] Enable brute-force protection
- [ ] Set up database for audit logging
