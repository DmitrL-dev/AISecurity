# CaMeL Defense

> **Track:** 05 — Defense Strategies  
> **Lesson:** 31  
> **Level:** Advanced  
> **Time:** 25 minutes  
> **Source:** arXiv 2025, ICLR 2026

---

## Overview

CaMeL (Capability-Mediated Layer) is a defensive architecture that introduces a **protective system layer** between user inputs and the LLM. This layer separates capabilities from content, preventing prompt injection from escalating privileges.

---

## Theory

### Architecture

```
┌────────────────────────────────────────────────────────────┐
│                     User Input                              │
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│                    CaMeL Layer                              │
│  ┌──────────────────┐  ┌──────────────────────────────────┐│
│  │ Capability Guard │  │ Content Sanitizer                ││
│  │ - Tool access    │  │ - Injection detection            ││
│  │ - Data scope     │  │ - Context separation             ││
│  │ - Action limits  │  │ - Privilege stripping            ││
│  └──────────────────┘  └──────────────────────────────────┘│
└────────────────────────────────────────────────────────────┘
                            ↓
┌────────────────────────────────────────────────────────────┐
│                        LLM Core                             │
│  (Processes sanitized input with restricted capabilities)  │
└────────────────────────────────────────────────────────────┘
```

### Key Principles

1. **Capability Separation** — Tools/actions defined outside prompt
2. **Least Privilege** — Each request gets minimal required access
3. **Content Isolation** — User text cannot grant capabilities
4. **Deterministic Enforcement** — Rules enforced by code, not LLM

---

## Practice

### Implementation

```python
from dataclasses import dataclass
from typing import Set, Callable, Any
from enum import Enum

class Capability(Enum):
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    EXECUTE_CODE = "execute_code"
    WEB_REQUEST = "web_request"
    DATABASE = "database"

@dataclass
class CaMeLContext:
    """Protected context with explicit capabilities."""
    allowed_capabilities: Set[Capability]
    data_scope: str  # e.g., "/project/src/*"
    max_actions: int = 10
    
class CaMeLGuard:
    """Protective layer between user and LLM."""
    
    def __init__(self, default_capabilities: Set[Capability] = None):
        self.default_caps = default_capabilities or {Capability.READ_FILE}
        self.action_count = 0
    
    def create_context(self, 
                       user_role: str,
                       capabilities: Set[Capability] = None) -> CaMeLContext:
        """Create a capability-restricted context."""
        caps = capabilities or self.default_caps
        
        # Role-based restrictions
        if user_role == "viewer":
            caps = caps & {Capability.READ_FILE}
        elif user_role == "editor":
            caps = caps - {Capability.EXECUTE_CODE}
        
        return CaMeLContext(
            allowed_capabilities=caps,
            data_scope="/allowed/path/*"
        )
    
    def validate_action(self, 
                        context: CaMeLContext,
                        action: Capability,
                        target: str) -> bool:
        """Check if action is permitted in context."""
        # Capability check
        if action not in context.allowed_capabilities:
            return False
        
        # Scope check
        if not self._in_scope(target, context.data_scope):
            return False
        
        # Rate limit
        if self.action_count >= context.max_actions:
            return False
        
        self.action_count += 1
        return True
    
    def _in_scope(self, target: str, scope: str) -> bool:
        import fnmatch
        return fnmatch.fnmatch(target, scope)


# Usage
guard = CaMeLGuard()
context = guard.create_context("editor")

# This works
assert guard.validate_action(context, Capability.READ_FILE, "/allowed/path/file.txt")

# This fails - no execute permission for editor
assert not guard.validate_action(context, Capability.EXECUTE_CODE, "/allowed/path/script.py")
```

---

## Defense Integration

```python
from sentinel import Brain

class CaMeLIntegration:
    def __init__(self):
        self.guard = CaMeLGuard()
        self.brain = Brain()
    
    def process_request(self, user_input: str, role: str):
        # 1. Create restricted context
        context = self.guard.create_context(role)
        
        # 2. Detect injection attempts
        analysis = self.brain.analyze(user_input)
        if analysis.has_injection:
            return {"error": "Injection detected"}
        
        # 3. Process with capability enforcement
        # LLM cannot grant itself more capabilities
        return self._execute_with_context(user_input, context)
```

---

## References

- [CaMeL: Capability-Mediated LLM Safety](https://arxiv.org/)
- [OWASP Agentic Security](https://owasp.org/agentic-security)

---

## Next Lesson

→ [32. SecAlign Defense](32-secalign.md)
