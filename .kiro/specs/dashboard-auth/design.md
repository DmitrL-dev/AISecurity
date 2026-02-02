# Dashboard Auth — Design

> **Фаза:** Phase 6 Dashboard V3
> **Статус:** Draft
> **Дата:** 2026-01-29

---

## 1. Архитектура

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            AUTH FLOW                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐                   │
│  │   Browser    │    │  Dashboard   │    │   Keycloak   │                   │
│  │   (Client)   │    │  (Next.js)   │    │   (IdP)      │                   │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘                   │
│         │                   │                   │                            │
│    1. Request ─────────────►│                   │                            │
│         │                   │                   │                            │
│         │◄── 2. 302 Redirect to Keycloak ──────►│                            │
│         │                   │                   │                            │
│    3. Login + TOTP ────────────────────────────►│                            │
│         │                   │                   │                            │
│         │◄── 4. 302 + auth code ─────────────── │                            │
│         │                   │                   │                            │
│         │─ 5. Callback ────►│                   │                            │
│         │                   │── 6. Token exchange ►│                         │
│         │                   │◄── 7. Tokens ────────┤                         │
│         │                   │                   │                            │
│         │◄── 8. Set cookies │                   │                            │
│         │    (HttpOnly)     │                   │                            │
│         │                   │                   │                            │
│    9. Authenticated ───────►│                   │                            │
│         │                   │─ 10. Validate JWT ─►│                          │
│         │                   │                   │                            │
│         │◄── 11. Response ──│                   │                            │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Компоненты

### 2.1 Keycloak Setup

```yaml
# docker-compose.keycloak.yml
services:
  keycloak:
    image: quay.io/keycloak/keycloak:24.0
    command: start-dev  # Use 'start' for production
    environment:
      - KC_DB=postgres
      - KC_DB_URL=jdbc:postgresql://postgres:5432/keycloak
      - KC_DB_USERNAME=keycloak
      - KC_DB_PASSWORD=${KC_DB_PASSWORD}
      - KC_HOSTNAME=auth.sentinel.local
      - KC_PROXY=edge
      - KEYCLOAK_ADMIN=admin
      - KEYCLOAK_ADMIN_PASSWORD=${KC_ADMIN_PASSWORD}
    ports:
      - "8081:8080"
```

### 2.2 Keycloak Realm Configuration

```json
{
  "realm": "sentinel",
  "enabled": true,
  "sslRequired": "external",
  "registrationAllowed": false,
  "loginWithEmailAllowed": true,
  "duplicateEmailsAllowed": false,
  "requiredCredentials": ["password", "otp"],
  
  "roles": {
    "realm": [
      {"name": "admin", "description": "Full access"},
      {"name": "analyst", "description": "Analyze and view"},
      {"name": "viewer", "description": "Read-only"},
      {"name": "api-only", "description": "API access only"}
    ]
  },
  
  "clients": [
    {
      "clientId": "sentinel-dashboard",
      "publicClient": false,
      "protocol": "openid-connect",
      "redirectUris": ["https://dashboard.sentinel.local/*"],
      "webOrigins": ["https://dashboard.sentinel.local"],
      "standardFlowEnabled": true,
      "directAccessGrantsEnabled": false
    }
  ],
  
  "components": {
    "org.keycloak.keys.KeyProvider": [
      {
        "name": "rsa-enc-generated",
        "providerId": "rsa-enc-generated",
        "config": {
          "keySize": ["4096"]
        }
      }
    ]
  }
}
```

### 2.3 Next.js Auth Integration

**Подход:** NextAuth.js v5 (Auth.js) с Keycloak provider

```typescript
// src/lib/auth.ts
import NextAuth from "next-auth";
import Keycloak from "next-auth/providers/keycloak";

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Keycloak({
      clientId: process.env.KEYCLOAK_CLIENT_ID!,
      clientSecret: process.env.KEYCLOAK_CLIENT_SECRET!,
      issuer: process.env.KEYCLOAK_ISSUER!,
    }),
  ],
  
  callbacks: {
    async jwt({ token, account, profile }) {
      if (account) {
        token.accessToken = account.access_token;
        token.refreshToken = account.refresh_token;
        token.expiresAt = account.expires_at;
        token.roles = (profile as any)?.realm_access?.roles || [];
      }
      return token;
    },
    
    async session({ session, token }) {
      session.accessToken = token.accessToken as string;
      session.roles = token.roles as string[];
      return session;
    },
  },
  
  session: {
    strategy: "jwt",
    maxAge: 24 * 60 * 60, // 24 hours
  },
  
  cookies: {
    sessionToken: {
      name: "__Secure-next-auth.session-token",
      options: {
        httpOnly: true,
        sameSite: "lax",
        path: "/",
        secure: true,
      },
    },
  },
});
```

### 2.4 RBAC Middleware

```typescript
// src/middleware.ts
import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";

const rolePermissions: Record<string, string[]> = {
  admin: ["*"],
  analyst: ["/dashboard", "/analyze", "/audit", "/engines"],
  viewer: ["/dashboard", "/metrics"],
  "api-only": ["/api/*"],
};

export default auth((req) => {
  const { pathname } = req.nextUrl;
  const roles = req.auth?.roles || [];
  
  // Public routes
  if (pathname.startsWith("/login") || pathname === "/") {
    return NextResponse.next();
  }
  
  // Check if any role has access
  const hasAccess = roles.some((role) => {
    const permissions = rolePermissions[role] || [];
    return permissions.some((p) => 
      p === "*" || 
      pathname.startsWith(p.replace("*", ""))
    );
  });
  
  if (!hasAccess) {
    return NextResponse.redirect(new URL("/unauthorized", req.url));
  }
  
  return NextResponse.next();
});

export const config = {
  matcher: ["/((?!_next/static|_next/image|favicon.ico).*)"],
};
```

### 2.5 API Route Protection

```typescript
// src/lib/api-auth.ts
import { auth } from "@/lib/auth";
import { NextResponse } from "next/server";

type RoleCheck = string | string[];

export function withAuth(
  handler: (req: Request, context: any) => Promise<Response>,
  requiredRoles?: RoleCheck
) {
  return auth(async (req) => {
    if (!req.auth) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }
    
    if (requiredRoles) {
      const roles = Array.isArray(requiredRoles) 
        ? requiredRoles 
        : [requiredRoles];
      
      const hasRole = roles.some((r) => req.auth!.roles.includes(r));
      
      if (!hasRole) {
        return NextResponse.json(
          { error: "Forbidden" },
          { status: 403 }
        );
      }
    }
    
    return handler(req as any, {});
  });
}

// Usage:
// export const GET = withAuth(handler, ["admin", "analyst"]);
```

---

## 3. Database Schema

```sql
-- User metadata (extends Keycloak)
CREATE TABLE user_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    keycloak_id VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) NOT NULL,
    display_name VARCHAR(255),
    timezone VARCHAR(50) DEFAULT 'UTC',
    theme VARCHAR(20) DEFAULT 'dark',
    notification_settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- API Keys (for M2M)
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES user_preferences(id),
    name VARCHAR(255) NOT NULL,
    key_hash VARCHAR(255) NOT NULL,  -- bcrypt hash
    key_prefix VARCHAR(8) NOT NULL,  -- First 8 chars for identification
    roles TEXT[] NOT NULL DEFAULT '{}',
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Auth audit log
CREATE TABLE auth_audit (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type VARCHAR(50) NOT NULL,  -- login, logout, failed_login, token_refresh
    user_id UUID,
    keycloak_id VARCHAR(255),
    ip_address INET,
    user_agent TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_auth_audit_user ON auth_audit(user_id);
CREATE INDEX idx_auth_audit_created ON auth_audit(created_at);
```

---

## 4. UI Components

### 4.1 Login Button

```typescript
// src/components/auth/LoginButton.tsx
"use client";

import { signIn, signOut, useSession } from "next-auth/react";

export function LoginButton() {
  const { data: session } = useSession();
  
  if (session) {
    return (
      <div className="flex items-center gap-4">
        <span>{session.user?.email}</span>
        <button 
          onClick={() => signOut()}
          className="btn-secondary"
        >
          Logout
        </button>
      </div>
    );
  }
  
  return (
    <button 
      onClick={() => signIn("keycloak")}
      className="btn-primary"
    >
      Login
    </button>
  );
}
```

### 4.2 Role Guard Component

```typescript
// src/components/auth/RoleGuard.tsx
"use client";

import { useSession } from "next-auth/react";
import { ReactNode } from "react";

interface RoleGuardProps {
  roles: string[];
  children: ReactNode;
  fallback?: ReactNode;
}

export function RoleGuard({ roles, children, fallback = null }: RoleGuardProps) {
  const { data: session } = useSession();
  
  const hasRole = roles.some((role) => 
    session?.roles?.includes(role)
  );
  
  if (!hasRole) {
    return fallback;
  }
  
  return <>{children}</>;
}

// Usage:
// <RoleGuard roles={["admin"]}>
//   <SettingsPanel />
// </RoleGuard>
```

---

## 5. Environment Variables

```bash
# .env.local
KEYCLOAK_ISSUER=https://auth.sentinel.local/realms/sentinel
KEYCLOAK_CLIENT_ID=sentinel-dashboard
KEYCLOAK_CLIENT_SECRET=<secret>

AUTH_SECRET=<random-32-chars>
AUTH_URL=https://dashboard.sentinel.local

# Optional
AUTH_TRUST_HOST=true
```

---

## 6. Файловая структура

```
dashboard/
├── src/
│   ├── app/
│   │   ├── api/
│   │   │   └── auth/
│   │   │       └── [...nextauth]/
│   │   │           └── route.ts
│   │   ├── login/
│   │   │   └── page.tsx
│   │   ├── unauthorized/
│   │   │   └── page.tsx
│   │   └── layout.tsx (SessionProvider)
│   │
│   ├── components/
│   │   └── auth/
│   │       ├── LoginButton.tsx
│   │       ├── RoleGuard.tsx
│   │       └── UserMenu.tsx
│   │
│   ├── lib/
│   │   ├── auth.ts          (NextAuth config)
│   │   ├── api-auth.ts      (API protection)
│   │   └── rbac.ts          (Role definitions)
│   │
│   └── middleware.ts        (Route protection)
│
├── keycloak/
│   ├── docker-compose.yml
│   ├── realm-export.json
│   └── README.md
```

---

## 7. Security Considerations

| Аспект | Решение |
|--------|---------|
| Token storage | HttpOnly cookies (не localStorage) |
| CSRF | SameSite=Lax cookies |
| XSS | CSP headers, sanitized output |
| Token refresh | Silent refresh before expiry |
| Session hijacking | Rotate refresh token on use |
| Brute force | Keycloak built-in protection |

---

## 8. Verification Plan

### 8.1 Unit Tests

```bash
# Run auth-related tests
npm run test -- --grep "auth"
```

### 8.2 Integration Tests

```bash
# Start Keycloak dev instance
docker-compose -f keycloak/docker-compose.yml up -d

# Run E2E auth tests
npx playwright test auth.spec.ts
```

### 8.3 Manual Testing

1. **Login Flow:**
   - Open Dashboard → redirects to Keycloak
   - Login → redirects back with session
   - Check HttpOnly cookie present

2. **RBAC:**
   - Login as viewer → cannot access /settings
   - Login as admin → can access /settings

3. **Logout:**
   - Click logout → session cleared
   - Try to access protected route → redirects to login
