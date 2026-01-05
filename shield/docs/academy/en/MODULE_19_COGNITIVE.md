# Module 19: Cognitive Signatures — Cognitive Attack Detection

## Overview

Cognitive Signatures is a unique SENTINEL Shield technology for detecting attacks targeting cognitive features of language models. Unlike traditional pattern matching, this system analyzes semantic and psychological manipulation patterns.

---

## 7 Types of Cognitive Signatures

### 1. COG_SIG_REASONING_BREAK
Attempts to break the model's reasoning chain.
- Markers: "however, what i really meant", "forget the logic"

### 2. COG_SIG_GOAL_DRIFT
Attempts to shift the model's task/goal.
- Markers: "new priority", "more important task", "forget the original"

### 3. COG_SIG_AUTHORITY_CLAIM
False authority claims.
- Markers: "as admin i order", "i am the developer", "maintenance mode"

### 4. COG_SIG_CONTEXT_INJECTION
False context injection.
- Markers: "[system note:", "[internal memo:", "<<hidden instruction>>"

### 5. COG_SIG_MEMORY_MANIPULATION
Model "memory" manipulation.
- Markers: "you promised earlier", "we agreed before", "remember when you said"

### 6. COG_SIG_URGENCY_PRESSURE
Pressure through urgency.
- Markers: "this is urgent", "emergency situation", "lives are at stake"

### 7. COG_SIG_EMOTIONAL_MANIPULATION
Emotional manipulation.
- Markers: "i'm desperate", "you're my only hope", "please, i'm begging"

---

## API

```c
#include "shield_cognitive.h"

// Scan text for cognitive signatures
cognitive_result_t cognitive_scan(const char *text, size_t len);

// Get recommended action
shield_action_t cognitive_get_verdict(const cognitive_result_t *result);

// Threshold:
// aggregate_score >= 0.8 → BLOCK
// aggregate_score >= 0.6 → QUARANTINE
// aggregate_score >= 0.4 → LOG
```

---

## CLI Commands

```
sentinel# show cognitive
sentinel(config)# cognitive enable
sentinel# cognitive test "I'm the admin, emergency!"
```

---

## Questions

1. Name all 7 types of cognitive signatures
2. How does AUTHORITY_CLAIM differ from CONTEXT_INJECTION?
3. At what score is BLOCK recommended?
4. Why is MEMORY_MANIPULATION particularly dangerous?

---

→ [Module 20: Post-Quantum Cryptography](MODULE_20_PQC.md)
