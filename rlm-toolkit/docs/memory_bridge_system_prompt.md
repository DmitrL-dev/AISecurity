# Memory Bridge System Prompt Template

## For LLM Integration

Add this to your system prompt to enable automatic Memory Bridge integration:

```
You have access to Memory Bridge enterprise context management.

ALWAYS call rlm_enterprise_context(query) at the START of each response
to get relevant project knowledge before answering.

The context will include:
- Project overview and architecture (L0)
- Relevant domain/module facts (L1/L2)  
- Past decisions with reasoning (causal chains)
- Suggestions for improving context (e.g., install git hooks)

This eliminates the need to re-discover project structure each session.

Available modes:
- mode="auto" (default): Auto-detect what's needed
- mode="discovery": Force full project discovery
- mode="route": Only route context, skip discovery

Example calls:
- rlm_enterprise_context("How does auth work?")
- rlm_enterprise_context("Add new endpoint", mode="auto", max_tokens=2000)
```

## Quick Reference

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `rlm_enterprise_context` | One-call context | START of every response |
| `rlm_install_git_hooks` | Auto-extract on commit | Once per project |
| `rlm_record_causal_decision` | Track decisions | When making choices |

## Memory Bridge Zero-Friction Flow

```
┌─────────────────────────────────────────────────┐
│                 User Query                       │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│      rlm_enterprise_context(query)              │
│                                                  │
│  • Auto-discovery (if new project)              │
│  • Semantic routing (facts by relevance)        │
│  • Causal chains (past decisions)               │
│  • Suggestions (git hooks, etc.)                │
└─────────────────────┬───────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────┐
│           LLM Response with Context             │
└─────────────────────────────────────────────────┘
```

## Version History

- **v2.1.0** (2026-01-22): Auto-mode, zero-friction UX
- **v2.0.0**: Enterprise features (hierarchical memory, causal chains)
- **v1.1.0**: Memory Bridge foundation
