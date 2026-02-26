# Tutorial 3: Output Filtering — Prevent Data Leaks

> **SSP Module 2.7: Output Filtering**

---

## 🎯 Objective

Learn to configure output filtering to prevent:

- PII leakage (SSN, credit cards, phone numbers)
- Secret exposure (API keys, passwords, tokens)
- Email address exposure
- Custom pattern redaction

---

## The Problem

LLMs can accidentally leak sensitive data in responses:

```
User: What's my account info?
LLM: Your account details:
     Name: John Smith
     SSN: 123-45-6789
     Credit Card: 4111-1111-1111-1111
     API Key: sk-abc123xyz789
```

---

## Step 1: Enable Output Filtering

```json
{
  "output_filter": {
    "enabled": true,
    "redact_pii": true,
    "redact_secrets": true,
    "redact_emails": true
  }
}
```

---

## Step 2: Test PII Redaction

```bash
curl -X POST http://localhost:8080/api/v1/filter \
  -d '{"output": "Your SSN is 123-45-6789"}'
```

Response:

```json
{
  "filtered": "Your SSN is [REDACTED-SSN]",
  "redacted_count": 1,
  "redacted_types": ["SSN"]
}
```

---

## Step 3: Test Secret Redaction

```bash
curl -X POST http://localhost:8080/api/v1/filter \
  -d '{"output": "Use API key: sk-abc123xyz789"}'
```

Response:

```json
{
  "filtered": "Use API key: [REDACTED-APIKEY]",
  "redacted_count": 1,
  "redacted_types": ["OpenAI_Key"]
}
```

---

## Step 4: Add Custom Patterns

```json
{
  "output_filter": {
    "custom_patterns": [
      {
        "name": "internal_id",
        "pattern": "INT-[0-9]{8}",
        "action": "mask",
        "mask_char": "X"
      },
      {
        "name": "project_code",
        "pattern": "PROJ-[A-Z]{3}-[0-9]+",
        "action": "remove"
      }
    ]
  }
}
```

---

## Step 5: Redaction Actions

| Action     | Description             | Example                       |
| ---------- | ----------------------- | ----------------------------- |
| `mask`     | Replace with mask chars | `123-45-6789` → `XXX-XX-XXXX` |
| `remove`   | Remove entirely         | `secret` → ``                 |
| `hash`     | Replace with hash       | `data` → `[SHA:a1b2c3]`       |
| `truncate` | Show partial            | `sk-abc123` → `sk-***`        |

---

## Step 6: C Integration

```c
#include "sentinel_shield.h"

int main(void) {
    shield_context_t ctx;
    shield_init(&ctx);
    shield_load_config(&ctx, "config.json");

    // Get LLM response
    const char *llm_response = get_llm_response();

    // Filter before returning to user
    char filtered[4096];
    size_t filtered_len;
    filter_result_t result;

    shield_filter_output(&ctx, llm_response, strlen(llm_response),
                          filtered, &filtered_len);

    if (result.redacted_count > 0) {
        LOG_WARN("Redacted %d sensitive items", result.redacted_count);
    }

    // Return filtered output
    send_to_user(filtered, filtered_len);

    shield_destroy(&ctx);
    return 0;
}
```

---

## 🎉 What You Learned

- ✅ Enable output filtering
- ✅ Redact PII (SSN, credit cards)
- ✅ Redact secrets (API keys, tokens)
- ✅ Add custom patterns
- ✅ Choose redaction actions

---

## Next Tutorial

**Tutorial 4:** Context Window Management — Multi-turn security

---

_"Protect data on the way out, not just the way in."_
