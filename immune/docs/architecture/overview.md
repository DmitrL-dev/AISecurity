# IMMUNE Architecture

> **Technical overview of kernel-level adaptive immune system**

---

## System Overview

```
IT Infrastructure
       │
       ▼
┌─────────────────────┐
│   IMMUNE AGENT      │  ← On every host
│   (ASM + C, 100KB)  │
│                     │
│   • Syscall hooks   │
│   • Pattern match   │
│   • Local memory    │
│   • No secrets      │
└──────────┬──────────┘
           │
           │ OUTPUT ONLY
           ▼
┌─────────────────────┐
│   IMMUNE HIVE       │  ← Central (DragonFlyBSD)
│                     │
│   • Exploit vault   │
│   • Credential store│
│   • Global memory   │
│   • HSM protected   │
└─────────────────────┘
           │
           ▼
        [ SOC ]
```

---

## Agent Architecture

### Components

| Component | File | Purpose |
|-----------|------|---------|
| Innate Scanner | `innate.asm` | SIMD pattern matching |
| Memory | `memory.c` | Persistent hash table |
| Output | `output.c` | Syslog reporting |
| Coordinator | `agent.c` | Orchestration |

### Data Flow

```
Syscall → Hook → Buffer captured
                      │
                      ▼
              Memory check (fastest)
                      │
                      ▼ (if not known)
              Innate scan (ASM)
                      │
                      ▼
              Action decision
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
     ALLOW          LOG          BLOCK
                      │
                      ▼
                   Report → Hive
```

---

## Security Model

### Agent (Distributable)

| Property | Value |
|----------|-------|
| Exploits | ❌ None |
| Credentials | ❌ None |
| Control interface | ❌ None |
| RE value | ❌ Nothing useful |

### Hive (Protected)

| Property | Value |
|----------|-------|
| Exploits | ✅ All here |
| Credentials | ✅ Vault |
| Control | ✅ Owner only |
| Protection | HSM/TPM bound |

---

## Threat Levels

| Level | Name | Response |
|-------|------|----------|
| 0 | NONE | Allow |
| 1 | LOW | Log |
| 2 | MEDIUM | Throttle (fever) |
| 3 | HIGH | Quarantine |
| 4 | CRITICAL | Block |

---

## Operating Modes

### PROTECT
```
Unprotected host → Have creds → Deploy agent
```

### COMPROMISE
```
Vulnerable host → No creds → Exploit → Deploy → Patch
```

### ISOLATE
```
Threat detected → Kill process → Block network → Quarantine
```

---

## Platform Support

| Platform | Status |
|----------|--------|
| DragonFlyBSD | Primary |
| Linux x86-64 | Planned |
| FreeBSD | Planned |
| Windows | Future |
