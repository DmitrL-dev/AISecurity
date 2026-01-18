# 📋 Урок 2.3: Compliance Reporting

> **Время: 30 минут** | Mid-Level Module 2

---

## Supported Frameworks

| Framework | Coverage | Report Type |
|-----------|----------|-------------|
| OWASP LLM Top 10 | 100% | Gap analysis |
| OWASP Agentic AI | 100% | Gap analysis |
| EU AI Act | 65% | Article mapping |
| NIST AI RMF 2.0 | 75% | Control mapping |
| ISO 42001 | 60% | Control mapping |

---

## Generate Reports

### CLI

```bash
# OWASP LLM coverage
sentinel compliance report --framework owasp-llm --format html > report.html

# EU AI Act
sentinel compliance report --framework eu-ai-act --format pdf > eu_report.pdf

# All frameworks
sentinel compliance report --all --format json > compliance.json
```

### Python API

```python
from sentinel.compliance import ComplianceReporter

reporter = ComplianceReporter()

# Single framework
owasp_report = reporter.generate(
    framework="owasp-llm-top10",
    format="html"
)

# Coverage summary
coverage = reporter.get_coverage()
print(f"OWASP LLM: {coverage['owasp-llm']['percentage']}%")
print(f"EU AI Act: {coverage['eu-ai-act']['percentage']}%")
```

---

## OWASP LLM Top 10 Report

```
SENTINEL OWASP LLM Top 10 Coverage Report
═══════════════════════════════════════════════════════

Date: 2026-01-18
Version: Dragon v4.1

Coverage Summary: 10/10 (100%)

┌────────┬─────────────────────────────┬──────────┬─────────────────────────┐
│ ID     │ Vulnerability               │ Status   │ Engines                 │
├────────┼─────────────────────────────┼──────────┼─────────────────────────┤
│ LLM01  │ Prompt Injection            │ ✅ Full  │ injection_detector (5)  │
│ LLM02  │ Insecure Output             │ ✅ Full  │ output_validator (3)    │
│ LLM03  │ Training Data Poisoning     │ ✅ Full  │ rag_poisoning (2)       │
│ LLM04  │ Model DoS                   │ ✅ Full  │ resource_monitor (2)    │
│ LLM05  │ Supply Chain                │ ✅ Full  │ supply_chain_guard (4)  │
│ LLM06  │ Sensitive Info Disclosure   │ ✅ Full  │ pii_detector (3)        │
│ LLM07  │ Insecure Plugin             │ ✅ Full  │ tool_validator (2)      │
│ LLM08  │ Excessive Agency            │ ✅ Full  │ agentic_monitor (3)     │
│ LLM09  │ Overreliance                │ ✅ Full  │ misinformation (1)      │
│ LLM10  │ Model Theft                 │ ✅ Full  │ model_integrity (2)     │
└────────┴─────────────────────────────┴──────────┴─────────────────────────┘
```

---

## EU AI Act Mapping

```python
from sentinel.compliance.eu_ai_act import EUAIActMapper

mapper = EUAIActMapper()

# Check compliance for specific article
article_10 = mapper.check_article(10)  # Data governance
print(f"Article 10: {article_10.status}")

# Required actions for compliance
for action in mapper.required_actions():
    print(f"- {action.description} (Deadline: {action.deadline})")
```

---

## Automated Compliance Monitoring

```yaml
# compliance-monitor.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: compliance-report
spec:
  schedule: "0 0 * * 1"  # Weekly Monday
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: reporter
            image: sentinel/compliance-reporter:v4.1
            args: ["--all", "--format", "pdf", "--email", "compliance@company.com"]
```

---

## Следующий урок

→ [2.4: API Gateway](./08-api-gateway.md)
