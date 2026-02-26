# Audit

> **Module 07.2: Audit Trail for AI Systems**

---

## Обзор

Audit модуль для AI-систем обеспечивает отслеживание событий, обнаружение аномалий и соответствие нормативным требованиям.

---

## Уроки

### [01. Audit Trail](01-audit-trail.md)
- Audit requirements (regulatory, security, operational)
- Audit event model with hash integrity
- Audit chain with tamper detection
- Audit logger with async support
- Audit analyzer: security summary, anomaly detection
- SENTINEL integration

---

## Audit Event Types

| Category | Events |
|----------|--------|
| **Request/Response** | request_received, response_generated |
| **Security** | security_violation, attack_detected, access_denied |
| **System** | tool_invoked, data_accessed, config_changed |
| **Agent** | agent_created, agent_terminated |
| **Approval** | approval_requested, granted, denied |

---

## Key Features

```
AuditEvent → AuditChain → Backend → Analyzer
    ↓            ↓           ↓          ↓
  Hash     Integrity    Storage   Anomalies
```

---

*AI Security Academy | Module 07.2*
