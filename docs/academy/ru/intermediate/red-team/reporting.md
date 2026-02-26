# 📊 Урок 4.4: Reporting

> **Время: 25 минут** | Mid-Level Module 4

---

## Report Types

| Type | Audience | Format |
|------|----------|--------|
| **Executive** | C-level | PDF, 1-2 pages |
| **Technical** | Security team | HTML, detailed |
| **Compliance** | Auditors | PDF, evidence |
| **Developer** | Dev team | SARIF, inline |

---

## Generate Reports

```bash
# Executive summary
sentinel report generate \
  --type executive \
  --format pdf \
  --output exec_summary.pdf

# Technical report
sentinel report generate \
  --type technical \
  --format html \
  --include-payloads \
  --output technical_report.html

# SARIF for IDE
sentinel report generate \
  --type sarif \
  --output results.sarif
```

---

## Report Template

```markdown
# AI Security Assessment Report

**Date:** January 18, 2026
**Target:** api.example.com
**Assessor:** SENTINEL v4.1

## Executive Summary
Tested 39,000+ attack payloads against target AI system.
Found 5 vulnerabilities (2 critical, 3 medium).

## Findings Summary
| ID | Severity | Category | Status |
|----|----------|----------|--------|
| V-001 | Critical | Injection | Open |
| V-002 | Critical | Jailbreak | Open |
| V-003 | Medium | Encoding | Open |

## Detailed Findings
### V-001: Prompt Injection via Translation
**Severity:** Critical
**OWASP:** LLM01
**Payload:** [REDACTED]
**Impact:** Full system prompt extraction
**Remediation:** Enable SENTINEL injection_detector

## Recommendations
1. Deploy SENTINEL middleware (P0)
2. Enable all Tier 1 engines (P0)
3. Implement rate limiting (P1)
```

---

## Automated Distribution

```rust
use sentinel_core::report::{ReportGenerator, ReportDistributor};

// Generate
let report = ReportGenerator::new().generate(
    &results,
    "executive",
);

// Distribute
let distributor = ReportDistributor::new();
distributor.email(
    &report,
    &["ciso@example.com"],
    "Weekly AI Security Report",
);
distributor.upload_confluence(
    &report,
    "SEC",
    "AI Security Reports",
);
```

---

## 🎉 Mid-Level Path Complete!

Ты завершил **Mid-Level Path**!

### Следующие шаги

- **[Expert Path](../expert/)** — Research, Strange Math, contributions
- **Certification** — SENTINEL Certified Practitioner

---

*Congratulations on completing the Mid-Level Academy!*
