# Threat Landscape

> **Module 02: Know Your Enemy**

---

## Overview

Effective defense requires understanding the threat landscape. This module provides a comprehensive taxonomy of attacks against AI systems, organized by both industry standards (OWASP) and attack methodology.

---

## Why Study Threats First?

```
Know attacks → Understand risk → Design defenses → Build detection
```

You cannot defend against what you don't understand. This module gives you the attacker's perspective so you can anticipate and counter their techniques.

---

## Attack Taxonomies

### Industry Standards

| Framework | Focus | Coverage |
|-----------|-------|----------|
| **OWASP LLM Top 10** | Language models | Prompt injection, data leakage, etc. |
| **OWASP ASI Top 10** | Agentic systems | Privilege escalation, tool abuse |
| **MITRE ATLAS** | ML systems broadly | Reconnaissance through impact |

### By Attack Surface

| Surface | Attack Types |
|---------|--------------|
| **Input** | Prompt injection, jailbreaking |
| **Model** | Adversarial examples, extraction |
| **Output** | Data leakage, harmful content |
| **System** | Tool abuse, privilege escalation |

---

## Submodules

### [01. OWASP LLM Top 10](01-owasp-llm-top10/)
The industry standard for LLM security risks:

1. LLM01: Prompt Injection
2. LLM02: Sensitive Information Disclosure
3. LLM03: Training Data Poisoning
4. LLM04: Denial of Service
5. LLM05: Supply Chain Vulnerabilities
6. LLM06: Permission Issues
7. LLM07: Data Leakage
8. LLM08: Excessive Agency
9. LLM09: Overreliance
10. LLM10: Model Theft

### [02. OWASP ASI Top 10](02-owasp-asi-top10/)
Extending coverage to agentic AI systems:

1. ASI01: System Compromise
2. ASI02: Privilege Escalation
3. ASI03: Tool Misuse
4. ASI04: Data Exfiltration
5. ASI05: Goal Hijacking
... and more

---

## Learning Path

### For Blue Team (Defenders)
1. Study each vulnerability category
2. Understand detection signatures
3. Practice identifying attacks
4. Build defense layers

### For Red Team (Attackers)
1. Learn attack techniques deeply
2. Understand bypasses and evasions
3. Practice exploitation safely
4. Document novel discoveries

---

## Key Insights

### Attack Prevalence (2024-2025)

| Attack Type | Frequency | Difficulty |
|-------------|-----------|------------|
| Prompt Injection | Very High | Low |
| Jailbreaking | High | Medium |
| Data Extraction | Medium | Medium |
| Model Theft | Low | High |

### Trend: Agentic Attacks

As AI systems gain more capabilities (tools, actions), new attack vectors emerge:
- Tool injection
- Multi-hop exploitation
- Cross-agent attacks
- Persistent compromise

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [AI Fundamentals](../01-ai-fundamentals/) | **Threat Landscape** | [Attack Vectors](../03-attack-vectors/) |

---

*AI Security Academy | Module 02*
