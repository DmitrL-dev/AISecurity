# OWASP LLM Top 10

> **Submodule 02.1: Industry Standard Risk Framework**

---

## Overview

The OWASP LLM Top 10 is the definitive framework for understanding and categorizing security risks in Large Language Model applications. This submodule provides deep dives into each category with practical attack examples and defense strategies.

---

## The Top 10 Vulnerabilities

| # | Vulnerability | Risk Level | Prevalence |
|---|---------------|------------|------------|
| LLM01 | Prompt Injection | Critical | Very High |
| LLM02 | Sensitive Information Disclosure | High | High |
| LLM03 | Training Data Poisoning | High | Medium |
| LLM04 | Denial of Service | Medium | Medium |
| LLM05 | Supply Chain Vulnerabilities | High | Medium |
| LLM06 | Permission & Access Issues | High | High |
| LLM07 | Data & Privacy Leakage | High | High |
| LLM08 | Excessive Agency | Critical | Medium |
| LLM09 | Overreliance | Medium | Very High |
| LLM10 | Model Theft | Medium | Low |

---

## Lessons

### [01. LLM01: Prompt Injection](01-LLM01-prompt-injection.md)
**Time:** 45 minutes | **Criticality:** Critical

The most prevalent and dangerous LLM vulnerability:
- Direct injection techniques
- Indirect injection via content
- Defense layers and best practices

### [02. LLM02: Sensitive Information Disclosure](02-LLM02-sensitive-disclosure.md)
**Time:** 35 minutes | **Criticality:** High

Preventing unintended data leakage:
- Training data extraction
- System prompt exposure
- PII in outputs

### 03. LLM03: Training Data Poisoning
**Time:** 40 minutes | **Criticality:** High

Supply chain attacks on training data:
- Backdoor insertion
- Behavior manipulation
- Data validation strategies

### 04. LLM04: Denial of Service
**Time:** 30 minutes | **Criticality:** Medium

Resource exhaustion attacks:
- Token flooding
- Recursive generation
- Rate limiting defenses

### 05-10. Additional Vulnerabilities
Supply chain, permissions, agency, overreliance, and model theft. *Advanced lessons available in Expert track.*

---

## Attack/Defense Matrix

| Vulnerability | Primary Attack | Primary Defense |
|--------------|----------------|-----------------|
| Prompt Injection | Embedded instructions | Input filtering + output checking |
| Disclosure | Extraction prompts | Output filtering + prompt protection |
| Poisoning | Malicious training data | Data validation + anomaly detection |
| DoS | Resource exhaustion | Rate limiting + input limits |
| Supply Chain | Compromised dependencies | Integrity verification |

---

## Practical Application

For each vulnerability, you'll learn:

1. **What it is** - Clear definition and scope
2. **How it works** - Attack mechanics and examples
3. **Real-world impact** - Documented incidents
4. **How to detect** - Signatures and patterns
5. **How to prevent** - Defense strategies

---

## Study Approach

### Recommended Order
Study vulnerabilities in order of prevalence and criticality:
1. LLM01 (Prompt Injection) - Most common
2. LLM02 (Disclosure) - High impact
3. LLM08 (Excessive Agency) - Growing threat
4. Remaining categories

### Hands-On Practice
Each lesson includes:
- Code examples of attacks
- Detection patterns
- SENTINEL integration

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Module Overview](../README.md) | **OWASP LLM Top 10** | [OWASP ASI Top 10](../02-owasp-asi-top10/) |

---

*AI Security Academy | Submodule 02.1*
