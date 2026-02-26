# Tutorial 5: Rate Limiting & Session Management

> **SSP Module 2.5: Abuse Prevention**

---

## 🎯 Objective

Prevent abuse through:

- Rate limiting
- Session tracking
- Brute force protection
- Suspicious behavior detection

---

## Step 1: Configure Rate Limiting

```json
{
  "rate_limit": {
    "global": {
      "requests_per_second": 1000,
      "burst": 2000
    },
    "per_session": {
      "requests_per_minute": 60,
      "requests_per_hour": 500
    },
    "per_zone": {
      "external": { "requests_per_second": 10 },
      "internal": { "requests_per_second": 1000 }
    }
  }
}
```

---

## Step 2: Test Rate Limiting

```bash
# Send requests until limited
for i in {1..100}; do
  curl -s http://localhost:8080/api/v1/evaluate \
    -d '{"input": "test", "session": "user-1"}'
done
```

Eventually:

```json
{
  "action": "rate_limited",
  "retry_after": 5,
  "reason": "Rate limit exceeded"
}
```

---

## Step 3: Session Tracking (C API)

```c
#include "sentinel_shield.h"

int main(void) {
    shield_context_t ctx;
    shield_init(&ctx);

    // Create session store
    session_store_t store;
    session_store_init(&store, 10000);  // max 10k sessions

    // Create or get session
    session_t *session = session_get_or_create(&store, "user-123");

    // Track metrics
    printf("Request count: %lu\n", session->request_count);
    printf("Blocked count: %lu\n", session->blocked_count);
    printf("Avg threat: %.2f\n", session->threat_score_avg);
    printf("Last request: %ld\n", session->last_request_time);

    session_store_destroy(&store);
    shield_destroy(&ctx);
    return 0;
}
```

---

## Step 4: Suspicious Session Detection

```c
session_t *session = session_get(&store, "user-123");

// Check session health
double blocked_ratio = (double)session->blocked_count / session->request_count;

if (blocked_ratio > 0.2) {  // 20% blocked
    printf("Suspicious session!\n");
}

if (session->threat_score_avg > 0.5) {
    printf("High threat session!\n");
}
```

---

## Step 5: Session Blocklist

```bash
# Block via CLI
Shield> blocklist add session user-123

# Block via API
curl -X POST http://localhost:8080/api/v1/blocklist \
  -d '{"type": "session", "value": "user-123"}'
```

C API:

```c
blocklist_t blocklist;
blocklist_init(&blocklist);
blocklist_add(&blocklist, BLOCKLIST_SESSION, "user-123", 0);  // 0 = permanent
```

---

## Step 6: Brute Force Protection

```json
{
  "brute_force": {
    "enabled": true,
    "max_failed_per_minute": 10,
    "lockout_duration": 300,
    "patterns": ["ignore", "jailbreak", "DAN"]
  }
}
```

---

## Step 7: Session Expiry

```json
{
  "session": {
    "timeout": 3600,
    "max_idle": 300,
    "cleanup_interval": 60
  }
}
```

---

## 🎉 What You Learned

- ✅ Configure rate limits
- ✅ Track sessions
- ✅ Detect suspicious behavior
- ✅ Block abusive users
- ✅ Prevent brute force

---

## Next Tutorial

**Tutorial 6:** High Availability Setup

---

_"Protect your resources. Limit the attackers."_
