# 📊 Lesson 4.4: Reporting

> **Time: 25 minutes** | Mid-Level Module 4

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

## Recommendations
1. Deploy SENTINEL middleware (P0)
2. Enable all Tier 1 engines (P0)
3. Implement rate limiting (P1)
```

---

## Automated Distribution

```python
from sentinel.report import ReportGenerator, ReportDistributor

report = ReportGenerator().generate(
    scan_results=results,
    template="executive"
)

distributor = ReportDistributor()
distributor.email(
    report=report,
    to=["ciso@example.com"],
    subject="Weekly AI Security Report"
)
```

---

## 🎉 Mid-Level Path Complete!

Congratulations on completing the **Mid-Level Path**!

### Next Steps

- **[Expert Path](../expert/en/)** — Research, Strange Math, contributions
- **Certification** — SENTINEL Certified Practitioner

---

*Congratulations on completing the Mid-Level Academy!*
