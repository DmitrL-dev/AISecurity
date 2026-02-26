# 📋 Lesson 2.3: Compliance Reporting

> **Time: 30 minutes** | Mid-Level Module 2

---

## Supported Frameworks

| Framework | Coverage | Status |
|-----------|----------|--------|
| **OWASP LLM Top 10** | 100% | ✅ |
| **OWASP Agentic AI Top 10** | 100% | ✅ |
| **EU AI Act** | 65% | ⚠️ |
| **NIST AI RMF** | 75% | ⚠️ |

---

## Generate Report

```bash
# CLI
sentinel compliance report \
  --frameworks owasp-llm,eu-ai-act \
  --format pdf \
  --output compliance_report.pdf

# With date range
sentinel compliance report \
  --from 2026-01-01 \
  --to 2026-01-31 \
  --format html
```

---

## Python API

```python
from sentinel.compliance import ComplianceReport

report = ComplianceReport(
    frameworks=["owasp_llm", "eu_ai_act", "nist_ai_rmf"],
    date_range=("2026-01-01", "2026-01-31")
)

# Generate
report.generate()

# Get coverage
print(report.coverage)
# {'owasp_llm': {'covered': 10, 'total': 10, 'percent': 100}}

# Export
report.to_pdf("compliance.pdf")
report.to_html("compliance.html")
```

---

## OWASP Mapping

```python
from sentinel.compliance import get_owasp_mapping

mappings = get_owasp_mapping()

for item in mappings:
    print(f"{item.id}: {item.name}")
    print(f"  Engines: {item.engines}")
    print(f"  Status: {item.status}")
```

Output:
```
LLM01: Prompt Injection
  Engines: injection_detector, jailbreak_detector, ...
  Status: ✅ Covered

LLM02: Insecure Output Handling
  Engines: output_validator, xss_detector
  Status: ✅ Covered
```

---

## Audit Trail

```python
from sentinel.audit import get_audit_log

# Get all security events
events = get_audit_log(
    start="2026-01-01",
    end="2026-01-31",
    event_types=["threat_detected", "config_change"]
)

for event in events:
    print(f"{event.timestamp}: {event.type} - {event.details}")
```

---

## Next Lesson

→ [3.1: Custom Engines](./09-custom-engines.md)
