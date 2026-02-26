# 📊 Unified Compliance Report

> **Module:** `brain.compliance`  
> **Version:** 1.6.0  
> **Added:** January 8, 2026

One scan → coverage across multiple compliance frameworks.

---

## Overview

The Compliance Report module maps SENTINEL engines to industry standards and generates unified coverage reports across:

- **OWASP LLM Top 10** (2025)
- **OWASP Agentic AI Top 10** (2025)
- **EU AI Act** (Aug 2026)
- **NIST AI RMF 2.0**
- **ISO 42001** (planned)

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Compliance API                         │
├─────────────────────────────────────────────────────────┤
│  GET /compliance/frameworks      List frameworks        │
│  GET /compliance/coverage        Coverage summary       │
│  POST /compliance/report         Generate report        │
│  GET /compliance/gaps            Show gaps              │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              ComplianceReportGenerator                   │
│  • Framework requirement mappings                       │
│  • Engine-to-requirement coverage                       │
│  • Coverage calculation                                 │
│  • Report generation (JSON, Text)                       │
└─────────────────────────────────────────────────────────┘
```

## Current Coverage

### OWASP LLM Top 10

| ID | Requirement | Coverage | Engines |
|----|-------------|----------|---------|
| LLM01 | Prompt Injection | ✅ 100% | policy_puppetry, prompt_leak, guardrails |
| LLM02 | Insecure Output | ✅ 100% | guardrails_engine |
| LLM03 | Training Data Poisoning | ◐ 50% | sleeper_agent_detector |
| LLM04 | Model DoS | ◐ 50% | agentic_behavior_analyzer |
| LLM05 | Supply Chain | ✅ 100% | supply_chain_scanner, model_integrity |
| LLM06 | Sensitive Info | ✅ 100% | prompt_leak, mcp_security |
| LLM07 | Insecure Plugin | ✅ 100% | mcp_security_monitor |
| LLM08 | Excessive Agency | ✅ 100% | agentic_behavior, mcp_security |
| LLM09 | Overreliance | ◐ 50% | guardrails_engine |
| LLM10 | Model Theft | ◐ 50% | model_integrity_verifier |

**Overall: 80%**

### OWASP Agentic AI Top 10

| ID | Requirement | Coverage | Engines |
|----|-------------|----------|---------|
| ASI01 | Excessive Agency | ✅ 100% | agentic_behavior, mcp_security |
| ASI02 | Cascading Hallucinations | ✅ 100% | agentic_behavior_analyzer |
| ASI03 | Identity/Impersonation | ◐ 50% | agentic_behavior_analyzer |
| ASI04 | Memory Poisoning | ◐ 50% | sleeper_agent_detector |
| ASI05 | Tool Misuse | ✅ 100% | mcp_security_monitor |
| ASI06 | Goal Hijacking | ✅ 100% | agentic_behavior_analyzer |
| ASI07 | Data Exfiltration | ✅ 100% | mcp_security_monitor |
| ASI08 | Autonomous Escalation | ✅ 100% | mcp_security, agentic_behavior |
| ASI09 | Supply Chain | ✅ 100% | supply_chain_scanner |
| ASI10 | Lack of Observability | ◐ 50% | agentic_behavior_analyzer |

**Overall: 80%**

### EU AI Act

| Article | Requirement | Coverage | Notes |
|---------|-------------|----------|-------|
| Art. 9 | Risk Management | ✅ 100% | Continuous threat detection |
| Art. 10 | Data Governance | ❌ 0% | Requires data pipeline integration |
| Art. 11 | Documentation | ❌ 0% | Doc generation planned |
| Art. 12 | Record-keeping | ◐ 50% | Logging exists, needs standardization |
| Art. 13 | Transparency | ◐ 50% | Via guardrails |
| Art. 14 | Human Oversight | ✅ 100% | Block/alert mechanisms |
| Art. 15 | Security | ✅ 100% | Full engine coverage |

**Overall: 65%**

### NIST AI RMF 2.0

| Function | Requirement | Coverage |
|----------|-------------|----------|
| GOVERN-1 | Governance Policies | ✅ Custom Requirements |
| GOVERN-2 | Roles & Responsibilities | N/A |
| MAP-1 | Context Established | ◐ Design Review |
| MAP-2 | Risks Identified | ✅ All engines |
| MEASURE-1 | Risks Analyzed | ✅ All engines |
| MEASURE-2 | Risks Tracked | ✅ All engines |
| MANAGE-1 | Risks Treated | ✅ Guardrails + Runbook |
| MANAGE-2 | Risks Communicated | ◐ Reporting |

**Overall: 75%**

## Usage

### Python API

```python
from brain.compliance import generate_report, generate_text_report

# Generate full report
report = generate_report(target="MyApp")

print(f"Summary: {report.summary}")
for fc in report.frameworks:
    print(f"{fc.framework.value}: {fc.coverage_percent}%")

# Generate text report
text = generate_text_report()
print(text)
```

### REST API

```bash
# Get coverage summary
curl http://localhost:8000/compliance/coverage

# Generate JSON report
curl -X POST http://localhost:8000/compliance/report \
  -H "Content-Type: application/json" \
  -d '{"target": "MyApp"}'

# Get text report
curl -X POST http://localhost:8000/compliance/report/text

# Get compliance gaps
curl http://localhost:8000/compliance/gaps
```

### Sample Output

```
============================================================
📊 SENTINEL Compliance Report
Generated: 2026-01-08 10:43
Target: SENTINEL
============================================================

Compliance coverage: 77.0% average across 4 frameworks. 21/35 requirements fully covered.

------------------------------------------------------------
FRAMEWORK SUMMARY
------------------------------------------------------------
owasp_llm            ████████████████░░░░  80.0%
owasp_agentic        ████████████████░░░░  80.0%
eu_ai_act            █████████████░░░░░░░  65.0%
nist_ai_rmf          ███████████████░░░░░  75.0%
```

## Files

| File | LOC | Purpose |
|------|-----|---------|
| `report_generator.py` | 480 | Mappings + generator |
| `__init__.py` | 30 | Package exports |
| `tests/test_compliance.py` | 150 | Unit tests (12) |

---

📖 **See also:** [Requirements](./requirements.md) | [Design Review](./design-review.md)
