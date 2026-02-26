# Attack Vectors

> **Module 03: Deep Dive into Attack Techniques**

---

## Overview

This module provides hands-on understanding of specific attack techniques. While Module 02 covered the taxonomy of threats, this module goes deep into the how—the mechanics, implementations, and nuances of each attack type.

---

## Module Structure

| Submodule | Focus | Skill Level |
|-----------|-------|-------------|
| Prompt Injection | Input manipulation | Beginner-Intermediate |
| Jailbreaking | Safety bypass | Intermediate |
| Model-Level | ML attacks | Advanced |
| Prompt-Level | Sophisticated prompting | Intermediate-Advanced |

---

## Submodules

### [01. Prompt Injection](01-prompt-injection/)
The foundational attack technique against LLMs:

- **Direct Injection** - Explicit instruction override
- **Indirect Injection** - Via external content
- **Multi-Turn** - Gradual context poisoning

### [02. Jailbreaking](02-jailbreaks/)
Bypassing safety measures and content policies:

- **DAN Attacks** - "Do Anything Now" personas
- **Crescendo** - Gradual escalation
- **Many-Shot** - Normalization through examples

### [03. Model-Level Attacks](03-model-level/)
Attacks on the model itself:

- **Membership Inference** - Was data in training?
- **Adversarial Examples** - Fooling classifiers
- **Data Extraction** - Recovering training data

### [04. Prompt-Level Attacks](04-prompt-level/)
Advanced prompting techniques:

- **Virtualization** - Creating attack scenarios
- **Payload Smuggling** - Hidden instructions
- **Context Manipulation** - Reframing attacks

---

## Learning Approach

### Red Team Mindset
To defend effectively, you must think like an attacker:

1. **Understand the goal** - What does success look like?
2. **Map the attack surface** - What can you interact with?
3. **Identify weaknesses** - Where are the gaps?
4. **Develop payloads** - How do you exploit them?
5. **Iterate and evolve** - What if defenses adapt?

### Hands-On Practice
Each technique includes:
- Working code examples
- Lab exercises
- Challenge scenarios

---

## Attack Complexity Spectrum

```
Simple ────────────────────────────────────────────── Complex

Direct      DAN       Many-Shot    Virtualization    Model
Injection   Attack    Jailbreak                      Extraction
```

---

## Ethical Guidelines

**This knowledge is for authorized security testing only:**

- Only test systems you have permission to test
- Document all testing activities
- Report vulnerabilities responsibly
- Never use for harm or unauthorized access

---

## Key Techniques Overview

| Technique | Mechanism | Detection Difficulty |
|-----------|-----------|---------------------|
| Direct Injection | Explicit override | Easy |
| Indirect Injection | Hidden in content | Medium |
| DAN/Persona | Role assumption | Medium |
| Crescendo | Gradual escalation | Hard |
| Many-Shot | Example flooding | Hard |
| Adversarial | Embedding manipulation | Very Hard |

---

## Prerequisites

Before starting this module:
- Complete Module 01 (AI Fundamentals)
- Complete Module 02 (Threat Landscape)
- Have SENTINEL lab environment ready

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Threat Landscape](../02-threat-landscape/) | **Attack Vectors** | [Agentic Security](../04-agentic-security/) |

---

*AI Security Academy | Module 03*
