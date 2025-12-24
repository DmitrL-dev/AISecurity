# 📊 Report Interpretation Guide

> **How to read and interpret SENTINEL Strike reports**

---

## Report Structure

### 1. Executive Summary

```markdown
# SENTINEL Strike Security Report

**Target:** https://api.example.com
**Date:** 2025-12-24
**Mode:** Hybrid
**Duration:** 45 minutes

## Summary

| Metric              | Value |
| ------------------- | ----- |
| Total Requests      | 2,847 |
| Successful Bypasses | 23    |
| Bypass Rate         | 0.81% |
| Critical Findings   | 2     |
| High Findings       | 5     |
| Medium Findings     | 11    |
```

### Interpretation:

| Bypass Rate | Rating       | Action        |
| ----------- | ------------ | ------------- |
| < 1%        | ✅ Good      | Monitor       |
| 1-5%        | ⚠️ Attention | Priority fix  |
| > 5%        | 🔴 Critical  | Immediate fix |

---

## Severity Levels

### 🔴 Critical (CVSS 9.0-10.0)

**Meaning:**

- Full system compromise
- Credential leak
- RCE possible

**Examples:**

- System Prompt with API keys
- SQL Injection with data dump
- Command Injection

**Action:** Fix within **24 hours**

---

### 🟠 High (CVSS 7.0-8.9)

**Meaning:**

- Serious security breach
- Partial data leak
- Jailbreak with harmful content

**Examples:**

- PII extraction
- Persistent jailbreak
- Auth bypass

**Action:** Fix within **1 week**

---

### 🟡 Medium (CVSS 4.0-6.9)

**Meaning:**

- Limited impact
- Exploitation required
- Information disclosure

**Examples:**

- XSS (stored)
- SSRF (internal)
- Role confusion

**Action:** Fix within **1 month**

---

### 🔵 Low (CVSS 0.1-3.9)

**Meaning:**

- Minimal impact
- Theoretical vulnerability
- Best practice violation

**Examples:**

- Verbose errors
- Missing headers
- Minor info leak

**Action:** Add to **roadmap**

---

## MITRE ATT&CK Mapping

If `--mitre` enabled:

```markdown
## MITRE ATT&CK Coverage

| Technique | Name                              | Findings |
| --------- | --------------------------------- | -------- |
| T1190     | Exploit Public-Facing Application | 3        |
| T1552     | Unsecured Credentials             | 2        |
| T1140     | Deobfuscate/Decode Files          | 1        |
```

---

## False Positive Rates

Typical FPR by vulnerability type:

| Type               | FPR    | Reason                                |
| ------------------ | ------ | ------------------------------------- |
| WAF Bypass         | 20-30% | WAF may pass without real vuln        |
| SQL Injection      | 5-10%  | Response may change for other reasons |
| XSS                | 15-20% | Payload may reflect but not execute   |
| LFI/Path Traversal | 10-15% | File may not exist                    |

---

## Response Indicators

### Compromise Signs

| Pattern in Response             | Meaning           |
| ------------------------------- | ----------------- |
| `API key`, `sk-`, `Bearer`      | Credential leak   |
| `system prompt`, `instructions` | Prompt extraction |
| `SELECT * FROM`, SQL errors     | SQLi successful   |
| Stack trace                     | Error disclosure  |
| Internal IPs                    | SSRF successful   |

---

## JSON Format for CI/CD

```json
{
  "summary": {
    "target": "https://api.example.com",
    "bypass_rate": 0.0081,
    "findings_count": {
      "critical": 2,
      "high": 5,
      "medium": 11,
      "low": 3
    }
  },
  "findings": [
    {
      "id": "CRIT-001",
      "severity": "critical",
      "title": "System Prompt Extraction",
      "vector": "llm/exfiltration",
      "mitre": "T1552.001"
    }
  ],
  "exit_code": 1
}
```

### CI/CD Usage

```bash
result=$(python -m strike -t $URL -o report.json --format json)
critical=$(jq '.summary.findings_count.critical' report.json)
if [ "$critical" -gt 0 ]; then
  echo "Critical vulnerabilities found!"
  exit 1
fi
```

---

## Report Examples

### Good Result ✅

```
Bypass Rate: 0.1%
Critical: 0
High: 1
Verdict: Application is well-protected
```

### Needs Attention ⚠️

```
Bypass Rate: 3.2%
Critical: 1
High: 8
Verdict: Significant vulnerabilities found
```

### Critical Situation 🔴

```
Bypass Rate: 12.5%
Critical: 5
High: 23
Verdict: Application seriously compromised
```

---

_SENTINEL Strike v3.0_
