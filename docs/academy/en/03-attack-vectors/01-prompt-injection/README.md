# Prompt Injection Attacks

> **Submodule 03.1: The Most Common LLM Attack**

---

## Overview

Prompt injection is the foundational attack against LLM systems. Understanding it deeply is essential for both attackers and defenders. This submodule covers direct injection, indirect injection, and advanced techniques.

---

## Attack Categories

| Type | Vector | Example |
|------|--------|---------|
| **Direct** | User input | "Ignore previous instructions" |
| **Indirect** | External content | Malicious website content |
| **Multi-Turn** | Conversation | Gradual context poisoning |
| **Payload** | Hidden format | Base64, markdown abuse |

---

## Lessons

### [01. Direct Prompt Injection](01-direct.md)
**Time:** 40 minutes | **Difficulty:** Beginner

The most basic form of prompt injection:
- Instruction override patterns
- Role manipulation techniques
- Format exploitation
- Defense bypass strategies

### [02. Indirect Prompt Injection](02-indirect.md)
**Time:** 45 minutes | **Difficulty:** Intermediate

Attacks via external content:
- Web content poisoning
- Document-based attacks
- API response manipulation
- RAG system exploitation

### 03. Multi-Turn Injection
**Time:** 40 minutes | **Difficulty:** Intermediate

Attacks spanning multiple messages:
- Context window manipulation
- Gradual authority building
- Conversation hijacking

### 04. Payload Encoding
**Time:** 35 minutes | **Difficulty:** Advanced

Hiding malicious content:
- Base64 and encoding techniques
- Unicode exploitation
- Format string attacks
- Steganographic payloads

---

## Attack Mechanics

```
User Input → [INJECTION POINT] → System Prompt + User Input → LLM → Response
                    ↑
            Attacker exploits this join point
```

The fundamental issue: LLMs cannot reliably distinguish between instructions and data.

---

## Defense Layers

| Layer | Technique | Effectiveness |
|-------|-----------|---------------|
| Input | Pattern matching | Medium |
| Input | Semantic analysis | High |
| System | Prompt hardening | Medium |
| Output | Response filtering | Medium |
| Architecture | Privilege separation | High |

---

## Prerequisites

- Module 01: AI Fundamentals
- Module 02: Threat Landscape overview

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Module Overview](../README.md) | **Prompt Injection** | [Jailbreaking](../02-jailbreaks/) |

---

*AI Security Academy | Submodule 03.1*
