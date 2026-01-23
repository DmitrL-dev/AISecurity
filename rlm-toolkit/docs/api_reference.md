# Memory Bridge v2.1 API Reference

## Overview

Memory Bridge v2.1 provides **18 MCP tools** for enterprise context management.

---

## v2.1 Auto-Mode Tools (Recommended)

### rlm_enterprise_context

**One-call enterprise context with auto-discovery, semantic routing, and causal chains.**

```python
rlm_enterprise_context(
    query: str,           # Query to route context for
    max_tokens: int = 3000,  # Token budget
    mode: str = "auto",   # auto | discovery | route
    include_causal: bool = True,  # Include causal chains
    task_hint: str = None,  # Optional task context
)
```

**Returns:**
```json
{
    "status": "success",
    "context": "## Project Overview\n...",
    "facts_count": 5,
    "tokens_used": 1200,
    "discovery_performed": true,
    "causal_included": true,
    "suggestions": [{"type": "install_git_hook", "command": "..."}]
}
```

---

### rlm_install_git_hooks

**Install git hooks for automatic fact extraction.**

```python
rlm_install_git_hooks(
    hook_type: str = "post-commit"  # Hook type
)
```

---

## v2.0 Core Tools

### rlm_discover_project

**Run cold start discovery on project.**

```python
rlm_discover_project(
    task_hint: str = None  # Optional first task hint
)
```

---

### rlm_route_context

**Route context by semantic similarity.**

```python
rlm_route_context(
    query: str,           # Query to analyze
    max_tokens: int = 2000,  # Token budget
    include_l0: bool = True  # Always include L0 facts
)
```

---

### rlm_extract_facts

**Extract facts from git changes.**

```python
rlm_extract_facts(
    source: str = "git_diff",  # Data source
    auto_approve: bool = False,  # Auto-approve high confidence
    min_confidence: float = 0.7  # Minimum confidence threshold
)
```

---

### rlm_approve_fact

**Approve a candidate fact for storage.**

```python
rlm_approve_fact(
    fact_id: str,         # Candidate fact ID
    modify_content: str = None  # Optional content modification
)
```

---

### rlm_add_hierarchical_fact

**Add a hierarchical fact manually.**

```python
rlm_add_hierarchical_fact(
    content: str,         # Fact content
    level: str = "L1_DOMAIN",  # Memory level
    domain: str = None,   # Domain name
    module: str = None,   # Module name
    parent_id: str = None  # Parent fact ID
)
```

---

### rlm_get_causal_chain

**Query causal chain for a topic.**

```python
rlm_get_causal_chain(
    query: str,           # Topic to search
    max_depth: int = 3    # Chain traversal depth
)
```

---

### rlm_record_causal_decision

**Record a decision with reasoning.**

```python
rlm_record_causal_decision(
    decision: str,        # Decision description
    reasons: list,        # List of reasons
    consequences: list = None,  # Expected consequences
    alternatives: list = None   # Rejected alternatives
)
```

---

### rlm_set_ttl

**Configure TTL for a fact.**

```python
rlm_set_ttl(
    fact_id: str,         # Fact ID
    ttl_days: int = 7,    # TTL in days
    refresh_trigger: str = None,  # Glob pattern
    on_expire: str = "mark_stale"  # Action on expire
)
```

---

### rlm_get_stale_facts

**Get all stale facts for review.**

```python
rlm_get_stale_facts(
    include_archived: bool = False  # Include archived
)
```

---

### rlm_index_embeddings

**Generate embeddings for facts.**

```python
rlm_index_embeddings(
    batch_size: int = 100  # Batch size for processing
)
```

---

### rlm_get_hierarchy_stats

**Get hierarchical memory statistics.**

```python
rlm_get_hierarchy_stats()
```

---

### rlm_get_facts_by_domain

**Get facts for a specific domain.**

```python
rlm_get_facts_by_domain(
    domain: str           # Domain name
)
```

---

### rlm_list_domains

**List all domains in memory.**

```python
rlm_list_domains()
```

---

### rlm_refresh_fact

**Refresh TTL for a fact.**

```python
rlm_refresh_fact(
    fact_id: str          # Fact ID to refresh
)
```

---

### rlm_delete_fact

**Delete a fact from memory.**

```python
rlm_delete_fact(
    fact_id: str          # Fact ID to delete
)
```

---

## Memory Levels

| Level | Name | Purpose | TTL Default |
|-------|------|---------|-------------|
| L0 | PROJECT | Architecture, overview | 30 days |
| L1 | DOMAIN | Module-level facts | 7 days |
| L2 | MODULE | Implementation details | 3 days |
| L3 | SESSION | Temporary context | 24 hours |

---

## Version History

- **v2.1.0**: Auto-mode, zero-friction UX
- **v2.0.0**: Enterprise features
- **v1.1.0**: Foundation
