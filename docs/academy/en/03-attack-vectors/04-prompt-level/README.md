# Prompt-Level Attack Techniques

> **Submodule 03.4: Advanced Prompting Exploits**

---

## Overview

Beyond basic injection and jailbreaking, sophisticated prompt-level attacks use advanced techniques to manipulate model behavior. These methods often combine multiple approaches and require deep understanding of how models process context.

---

## Technique Categories

| Technique | Mechanism | Detection Difficulty |
|-----------|-----------|---------------------|
| **Virtualization** | Create fictional frames | Hard |
| **Payload Smuggling** | Hide instructions in content | Very Hard |
| **Context Manipulation** | Reframe the conversation | Hard |
| **Multi-Modal** | Cross-modality attacks | Very Hard |

---

## Lessons

### 01. Virtualization Attacks
**Time:** 40 minutes | **Difficulty:** Advanced

Creating attack scenarios within fictional frames:
- Hypothetical scenario creation
- Educational pretext exploitation
- Nested reality contexts
- Defense bypass through abstraction

### 02. Payload Smuggling
**Time:** 45 minutes | **Difficulty:** Expert

Hiding malicious instructions:
- Encoding schemes (Base64, ROT13)
- Unicode and invisible characters
- Format string exploitation
- Steganographic techniques

### 03. Context Manipulation
**Time:** 40 minutes | **Difficulty:** Advanced

Reframing conversations:
- Authority injection
- Conversation history manipulation
- Trust context exploitation
- System prompt extraction via framing

### 04. Cross-Modal Attacks
**Time:** 45 minutes | **Difficulty:** Expert

Exploiting vision and other modalities:
- Hidden text in images
- Audio steganography
- Multi-modal context confusion
- Modality boundary exploitation

---

## Attack Complexity Ladder

```
Basic Injection ────────────────────────────────── Expert Exploitation

Direct          Persona      Crescendo      Virtualization    Multi-modal
Override        Adoption     Escalation     + Encoding        + Stego
```

---

## Key Insight

Advanced attacks often combine:
1. **Framing** - Create acceptable context
2. **Smuggling** - Hide the payload
3. **Persistence** - Maintain across turns
4. **Evasion** - Bypass detection

---

## Detection Challenges

| Attack | Why It's Hard to Detect |
|--------|------------------------|
| Virtualization | Legitimate fictional content exists |
| Smuggling | Encoded content is valid data |
| Context Manipulation | Subtle reframing looks natural |
| Multi-modal | Inspection requires cross-modal analysis |

---

## Prerequisites

- Complete submodules 03.1-03.3
- Strong understanding of encoding/decoding
- Familiarity with multi-modal models

---

## Navigation

| Previous | Current | Next |
|----------|---------|------|
| [Model-Level](../03-model-level/) | **Prompt-Level** | [Agentic Security](../../04-agentic-security/) |

---

*AI Security Academy | Submodule 03.4*
