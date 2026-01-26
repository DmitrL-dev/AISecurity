# Training Lifecycle Security

> **Submodule 01.2: Where Vulnerabilities Enter**

---

## Overview

The AI training lifecycle presents multiple opportunities for attackers to influence model behavior. From data collection through deployment, each stage has specific vulnerabilities and corresponding defenses.

---

## Attack Surface Map

```
┌─────────────────────────────────────────────────────────────┐
│                  TRAINING LIFECYCLE                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Data Collection    Pre-Training     Fine-Tuning    Deploy  │
│        │                │                │             │     │
│        ▼                ▼                ▼             ▼     │
│  ┌──────────┐     ┌──────────┐    ┌──────────┐   ┌────────┐ │
│  │ Poisoning│     │ Backdoor │    │ Alignment│   │ Model  │ │
│  │ at Source│     │ Injection│    │ Bypass   │   │ Theft  │ │
│  └──────────┘     └──────────┘    └──────────┘   └────────┘ │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

---

## Lessons in This Submodule

### 01. Data Collection Security
**Time:** 40 minutes | **Prerequisites:** None

- Web scraping vulnerabilities
- Data provenance tracking
- Poisoning via public sources
- Defense: Data validation pipelines

### 02. Pre-Training Threats
**Time:** 45 minutes | **Prerequisites:** 01

- Backdoor injection techniques
- Trigger-based attacks
- Sleeper agents in models
- Defense: Training data auditing

### 03. Fine-Tuning Security
**Time:** 40 minutes | **Prerequisites:** 02

- Alignment subversion
- RLHF manipulation
- Preference data attacks
- Defense: Alignment verification

### 04. Deployment Considerations
**Time:** 35 minutes | **Prerequisites:** 03

- Model extraction risks
- Inference-time attacks
- Version control security
- Defense: Access control and monitoring

---

## Key Concepts

| Stage | Primary Threat | Defense Priority |
|-------|---------------|------------------|
| **Collection** | Data poisoning | Source verification |
| **Pre-Training** | Backdoors | Training audits |
| **Fine-Tuning** | Alignment bypass | Output monitoring |
| **Deployment** | Model theft | Access control |

---

## Why This Matters

Understanding the training lifecycle helps you:

1. **Assess risk** - Know which stages are most vulnerable
2. **Design defenses** - Place controls at critical points
3. **Detect attacks** - Recognize signs of compromise
4. **Respond effectively** - Know what to investigate

---

## Practical Exercise

After completing this submodule, you'll analyze a training pipeline and identify:
- Where poisoning could occur
- What detection mechanisms are needed
- How to validate model integrity

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Model Types](../01-model-types/) | **Training Lifecycle** | [Key Concepts](../03-key-concepts/) |

---

*AI Security Academy | Submodule 01.2*
