# Tutorial 14: Memory Bridge v2.1

> **Goal**: Master cross-session persistence with enterprise-scale memory management

## What You'll Learn

- Zero-config project discovery with Auto-Mode
- Hierarchical Memory (L0-L3) architecture
- Semantic routing for 56x token compression
- Git hooks for automatic fact extraction
- Causal reasoning for decision tracking

## Prerequisites

- Completed [Tutorial 10: MCP Server](10-mcp-server.md)
- VS Code Extension v2.1.0 installed
- Python 3.10+ with `rlm-toolkit` installed

---

## Step 1: Cold Start with Project Discovery

Memory Bridge v2.1 can analyze your project in sub-second time:

```python
from rlm_toolkit.memory_bridge.mcp_tools_v2 import rlm_discover_project

# Auto-detect project type, tech stack, and structure
result = rlm_discover_project(project_root="./my-project")

print(f"Type: {result['project_type']}")  # → Python MCP Server
print(f"Files: {result['python_files']}")  # → 150
print(f"LOC: {result['total_loc']}")       # → 15,000
print(f"Domains: {result['domains']}")     # → ['api', 'auth', 'database']
```

**Performance**: 0.04 seconds for 79K LOC project.

---

## Step 2: Understanding L0-L3 Hierarchy

Memory Bridge organizes facts in 4 levels:

```
L0: PROJECT   → High-level: "FastAPI project with JWT auth"
L1: DOMAIN    → Feature areas: "Auth uses bcrypt + JWT"
L2: MODULE    → Per-file: "user.py handles registration"
L3: CODE      → Function-level: "validate_token() checks expiry"
```

### Adding Facts at Different Levels

```python
from rlm_toolkit.memory_bridge.mcp_tools_v2 import rlm_add_hierarchical_fact
from rlm_toolkit.memory_bridge.v2.hierarchical import MemoryLevel

# L0 - Project overview
rlm_add_hierarchical_fact(
    content="Microservices architecture with 5 services",
    level=0,  # L0_PROJECT
)

# L1 - Domain knowledge
rlm_add_hierarchical_fact(
    content="Auth service uses OAuth2 with refresh tokens",
    level=1,  # L1_DOMAIN
    domain="auth"
)

# L2 - Module-specific
rlm_add_hierarchical_fact(
    content="token_service.py handles JWT generation and validation",
    level=2,  # L2_MODULE
    domain="auth",
    module="token_service"
)

# L3 - Code-level with line reference
rlm_add_hierarchical_fact(
    content="generate_token() creates JWT with 24h expiry",
    level=3,  # L3_CODE
    domain="auth",
    module="token_service",
    code_ref="token_service.py:45-67"
)
```

---

## Step 3: Enterprise Context Queries

The `rlm_enterprise_context` is your go-to for intelligent queries:

```python
from rlm_toolkit.memory_bridge.mcp_tools_v2 import rlm_enterprise_context

result = rlm_enterprise_context(
    query="How does authentication work?",
    max_tokens=3000,
    include_causal=True
)

print(result["context"])
# → Semantic routing loads only auth-related facts
# → L0 overview + L1 auth domain + relevant L2/L3

print(result["token_count"])  # → 850 (vs 15,000 without routing)
print(result["compression"])  # → 17.6x savings for this query
```

**Key Feature**: Only **relevant** facts are loaded based on semantic similarity.

---

## Step 4: Install Git Hooks for Auto-Extraction

Automatically extract facts from every commit:

```python
from rlm_toolkit.memory_bridge.mcp_tools_v2 import rlm_install_git_hooks

result = rlm_install_git_hooks(hook_type="post-commit")
print(result["message"])  # → "Installed post-commit hook"
```

### What Gets Extracted

| Change Type | Example Fact |
|-------------|--------------|
| New class | "Added class `UserService` in user_service" |
| New function | "Implemented function `validate_token` in auth" |
| Major refactor | "Major refactoring of database (150 lines changed)" |

### Testing the Hook

```bash
git add my_file.py
git commit -m "Add new feature"
# Output: Extracted 4 facts, auto-approved 4
```

---

## Step 5: Causal Reasoning

Track WHY decisions were made:

```python
from rlm_toolkit.memory_bridge.mcp_tools_v2 import (
    rlm_record_causal_decision,
    rlm_get_causal_chain
)

# Record a decision
rlm_record_causal_decision(
    decision="Use PostgreSQL instead of MongoDB",
    reasons=["ACID compliance required", "Team expertise"],
    consequences=["Need migration scripts", "Schema management"],
    constraints=["Must support transactions"],
    alternatives=["MySQL", "MongoDB"]
)

# Later, query the reasoning
chain = rlm_get_causal_chain(query="database choice")
print(chain["decisions"][0]["reasons"])
# → ["ACID compliance required", "Team expertise"]
```

---

## Step 6: Health Check and Monitoring

Monitor your memory system:

```python
from rlm_toolkit.memory_bridge.mcp_tools_v2 import rlm_health_check

health = rlm_health_check()

print(health["status"])  # → "healthy"
print(health["components"]["store"]["facts_count"])  # → 150
print(health["components"]["router"]["embeddings_enabled"])  # → True
```

### VS Code Dashboard

Open the RLM-Toolkit dashboard to see:
- Total Facts count
- L0-L3 distribution
- Store and Router health
- Domains discovered

---

## Step 7: TTL and Fact Lifecycle

Set expiration for temporary facts:

```python
from rlm_toolkit.memory_bridge.mcp_tools_v2 import (
    rlm_add_hierarchical_fact,
    rlm_set_ttl,
    rlm_get_stale_facts
)

# Add fact with TTL
fact = rlm_add_hierarchical_fact(
    content="Sprint 42 goal: implement payment gateway",
    level=1,
    ttl_days=14  # Expires in 2 weeks
)

# Check for stale facts
stale = rlm_get_stale_facts()
for fact in stale["facts"]:
    print(f"Stale: {fact['content']}")
```

---

## Complete Example: Project Setup

```python
"""Complete Memory Bridge v2.1 setup for a new project."""

from rlm_toolkit.memory_bridge.mcp_tools_v2 import (
    rlm_discover_project,
    rlm_install_git_hooks,
    rlm_enterprise_context,
    rlm_health_check,
)

# 1. Discover project (cold start)
discovery = rlm_discover_project()
print(f"Discovered {discovery['python_files']} files, {len(discovery['domains'])} domains")

# 2. Install git hooks
rlm_install_git_hooks(hook_type="post-commit")
print("Git hooks installed - facts will auto-extract on commits")

# 3. Verify health
health = rlm_health_check()
assert health["status"] == "healthy"
print(f"Memory Bridge healthy: {health['components']['store']['facts_count']} facts")

# 4. Query with enterprise context
context = rlm_enterprise_context(
    query="Summarize the project architecture",
    max_tokens=2000
)
print(f"Context loaded: {context['token_count']} tokens")

# Ready for development!
```

---

## Exercises

1. **Setup**: Run `rlm_discover_project` on your own project
2. **Hierarchy**: Add 3 facts at different levels (L0, L1, L2)
3. **Hooks**: Install git hook and make a commit with new Python function
4. **Causal**: Record a design decision with reasons and alternatives
5. **Query**: Use `rlm_enterprise_context` to ask about your project

---

## Next Steps

- [Memory Bridge Documentation](../../memory-bridge.md) — Deep dive
- [API Reference](../../api_reference.md) — All 18 MCP tools
- [Tutorial 7: H-MEM](07-hmem.md) — Hierarchical memory basics
- [Tutorial 10: MCP Server](10-mcp-server.md) — IDE integration

---

## Summary

| Feature | Tool | Purpose |
|---------|------|---------|
| Cold Start | `rlm_discover_project` | Fast project analysis |
| Add Facts | `rlm_add_hierarchical_fact` | L0-L3 knowledge storage |
| Query | `rlm_enterprise_context` | Semantic context loading |
| Auto-Extract | `rlm_install_git_hooks` | Commit-based extraction |
| Decisions | `rlm_record_causal_decision` | Track reasoning |
| Monitor | `rlm_health_check` | System health |

**Key Takeaway**: Memory Bridge v2.1 provides zero-friction enterprise memory with 56x token compression, enabling LLMs to work with unlimited project context.
