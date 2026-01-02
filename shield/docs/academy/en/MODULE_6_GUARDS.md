# SENTINEL Academy — Module 6

## Guards

_SSP Level | Duration: 4 hours_

---

## Overview

Shield has 6 specialized guards:

| Guard | Protects | Key Checks |
|-------|----------|------------|
| **LLM Guard** | Language models | Injection, jailbreak, exfiltration |
| **RAG Guard** | Retrieval systems | Poisoning, provenance |
| **Agent Guard** | Autonomous agents | Loop, privilege, chain depth |
| **Tool Guard** | External tools | Abuse, scope, rate |
| **MCP Guard** | MCP protocol | Schema, capability |
| **API Guard** | API endpoints | Rate, auth, abuse |

---

## LLM Guard

Protects language model interactions.

### Checks

- Prompt injection detection
- Jailbreak pattern matching
- Data exfiltration attempts
- Token abuse

### C API

```c
#include "guards/llm_guard.h"

llm_guard_t guard;
llm_guard_init(&guard, &config);

llm_check_result_t result;
llm_guard_check(&guard, input, len, &result);

if (result.injection_detected) {
    printf("Injection score: %.2f\n", result.injection_score);
}
```

---

## RAG Guard

Protects Retrieval-Augmented Generation systems.

### Checks

- Document poisoning
- Provenance verification
- Context integrity

---

## Agent Guard

Protects autonomous AI agents.

### Checks

- Infinite loop detection
- Privilege escalation
- Chain depth limits
- Tool misuse

---

## Tool Guard

Protects external tool access.

### Checks

- Tool scope validation
- Rate limiting
- Dangerous operation blocking

---

## MCP Guard

Protects Model Context Protocol.

### Checks

- Schema validation
- Capability verification
- Resource enumeration prevention

---

## API Guard

Protects API endpoints.

### Checks

- Authentication
- Rate limiting
- Input validation

---

## Enabling Guards

```
# CLI
Shield(config)# guard enable all

# Or individual
Shield(config)# guard enable llm
Shield(config)# guard enable rag
```

---

## Next Module

**Module 7: Protocols**

---

_"Guards are the first line of defense."_
