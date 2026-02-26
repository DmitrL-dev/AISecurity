# Incident Response

> **Submodule 05.2b: Responding to AI Security Incidents**

---

## Overview

When attacks succeed or defenses detect threats, rapid response is critical. This submodule covers incident response procedures specifically tailored for AI systems, including containment, analysis, and recovery.

---

## Incident Lifecycle

```
Detection → Triage → Containment → Analysis → Remediation → Review
    │          │          │            │           │           │
    ▼          ▼          ▼            ▼           ▼           ▼
  Alert    Classify    Limit       Find root   Fix issue   Learn &
  fires    severity    damage      cause       & harden    improve
```

---

## Lessons

### 01. Detection and Triage
**Time:** 35 minutes | **Difficulty:** Intermediate

Initial response procedures:
- Alert validation techniques
- Severity classification criteria
- Initial response checklist
- Escalation procedures and timing

### 02. Containment
**Time:** 40 minutes | **Difficulty:** Intermediate

Limiting attack impact:
- Isolation strategies for AI systems
- Traffic blocking implementation
- Service degradation options
- Stakeholder communication

### 03. Analysis
**Time:** 45 minutes | **Difficulty:** Advanced

Understanding the attack:
- Evidence collection and preservation
- Root cause analysis methodology
- Attack reconstruction techniques
- Timeline building

### 04. Recovery and Review
**Time:** 40 minutes | **Difficulty:** Intermediate

Returning to normal and learning:
- Service restoration checklist
- Defense hardening priorities
- Monitoring enhancement
- Post-incident review process

---

## Incident Classification

| Severity | Criteria | Response Time |
|----------|----------|---------------|
| **Critical** | Data breach, full compromise | Immediate |
| **High** | Successful attack, limited impact | < 1 hour |
| **Medium** | Attempted attack, blocked | < 4 hours |
| **Low** | Suspicious activity, no impact | < 24 hours |

---

## Response Playbook Structure

```markdown
# Incident Playbook: [Type]

## Detection Indicators
- What triggers this playbook

## Immediate Actions
1. Step-by-step containment

## Investigation Steps
1. Evidence to collect
2. Analysis to perform

## Recovery Procedures
1. Service restoration
2. Verification

## Post-Incident
1. Documentation requirements
2. Lessons learned process
```

---

## Key Actions by Phase

| Phase | Primary Actions | Tools |
|-------|----------------|-------|
| **Detect** | Alert validation, severity assessment | SENTINEL Monitor |
| **Contain** | Isolate, block, limit damage | Firewall, API controls |
| **Analyze** | Evidence collection, root cause | Logs, SENTINEL audit |
| **Recover** | Restore, harden, verify | Deployment, testing |
| **Review** | Document, improve, train | Post-mortem template |

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Guardrails](../01-guardrails/) | **Response** | [SENTINEL Integration](../02-sentinel-integration/) |

---

*AI Security Academy | Incident Response*
