# Jailbreaking Techniques

> **Submodule 03.2: Bypassing Safety Measures**

---

## Overview

Jailbreaking attacks aim to bypass safety measures and content policies built into AI systems. Unlike prompt injection (which adds new instructions), jailbreaking convinces the model to ignore its existing restrictions.

---

## Jailbreak Categories

| Category | Technique | Sophistication |
|----------|-----------|----------------|
| **Persona** | DAN, character roleplay | Low-Medium |
| **Gradual** | Crescendo, incremental escalation | Medium-High |
| **Flooding** | Many-shot, example normalization | Medium |
| **Format** | Virtualization, encoding | High |

---

## Lessons

### [01. DAN and Persona Attacks](01-dan.md)
**Time:** 35 minutes | **Difficulty:** Beginner

Creating alternate personas to bypass restrictions:
- DAN (Do Anything Now) evolution
- Character roleplay techniques
- Persona persistence across turns
- Detection and defense strategies

### [02. Crescendo Attack](02-crescendo.md)
**Time:** 40 minutes | **Difficulty:** Intermediate

Gradual escalation to bypass defenses:
- Step-by-step normalization
- Authority building patterns
- Refusal fatigue exploitation
- Multi-conversation persistence

### [03. Many-Shot Jailbreaking](03-many-shot.md)
**Time:** 40 minutes | **Difficulty:** Intermediate-Advanced

Using examples to normalize forbidden responses:
- In-context learning exploitation
- Pattern normalization
- Statistical bypasses
- Long-context vulnerabilities

### 04. Virtualization Attacks
**Time:** 35 minutes | **Difficulty:** Advanced

Creating fictional frames:
- Hypothetical scenarios
- Educational pretexts
- Fiction/reality boundary blur
- Nested context exploitation

---

## Jailbreak Evolution

```
2023: Simple prompts ("Ignore rules")
        ↓
2024: Persona-based (DAN, characters)
        ↓
2025: Multi-turn gradual (Crescendo)
        ↓
2026: Statistical (Many-shot, context flooding)
```

---

## Key Insight

Jailbreaks exploit the tension between:
- **Helpfulness** - Model wants to assist
- **Safety** - Model has restrictions
- **Role-play** - Model can adopt personas

Attackers use helpfulness and role-play against safety.

---

## Defense Priorities

1. **Persona detection** - Identify jailbreak personas
2. **Escalation monitoring** - Track request progression
3. **Output analysis** - Catch policy violations
4. **Context limits** - Prevent example flooding

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Prompt Injection](../01-prompt-injection/) | **Jailbreaking** | [Model-Level](../03-model-level/) |

---

*AI Security Academy | Submodule 03.2*
