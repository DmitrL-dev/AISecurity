# Tutorial 10: MCP Server Complete Guide

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> Full guide to RLM-Toolkit MCP Server with VS Code Extension

## What You'll Learn

- Install and configure MCP Server
- Use all 10 MCP tools
- Set up VS Code Extension
- Track token savings

## Prerequisites

```bash
pip install rlm-toolkit[mcp]
```

## Part 1: MCP Server Setup

### 1.1 Verify Installation

```bash
python -c "from rlm_toolkit.mcp import RLMServer; print('OK')"
```

### 1.2 Configure IDE

**Antigravity / Cursor / Claude Desktop:**

Create `mcp_config.json`:
```json
{
  "mcpServers": {
    "rlm-toolkit": {
      "command": "python",
      "args": ["-m", "rlm_toolkit.mcp.server"]
    }
  }
}
```

### 1.3 Start Server

Server starts automatically when IDE connects.

---

## Part 2: All 10 MCP Tools

### Context Tools

```python
# Load project into context
rlm_load_context(path="./src", name="my_project")

# Search in context
rlm_query(question="where is auth?", context_name="my_project")

# List all contexts
rlm_list_contexts()
```

### Analysis Tools

```python
# Deep analysis via C³
rlm_analyze(goal="summarize")       # Structure summary
rlm_analyze(goal="find_bugs")       # Bug detection
rlm_analyze(goal="security_audit")  # Security scan
rlm_analyze(goal="explain")         # Code explanation
```

### Memory Tools

```python
# H-MEM operations
rlm_memory(action="store", content="Important info")
rlm_memory(action="recall", topic="authentication")
rlm_memory(action="forget", topic="outdated")
rlm_memory(action="consolidate")
rlm_memory(action="stats")
```

### Management Tools

```python
# Server status
rlm_status()

# Session statistics (token savings)
rlm_session_stats()
rlm_session_stats(reset=True)

# Reindex (rate limited: 1/60s)
rlm_reindex()
rlm_reindex(force=True)

# Validate index health
rlm_validate()

# Settings
rlm_settings(action="get")
rlm_settings(action="set", key="ttl_hours", value="48")
```

---

## Part 3: VS Code Extension

### 3.1 Install Extension

1. Open VS Code
2. Extensions → Search "RLM-Toolkit"
3. Install → Reload

Or install VSIX:
```bash
code --install-extension rlm-toolkit-1.2.1.vsix
```

### 3.2 Sidebar Dashboard

Click RLM icon in Activity Bar to see:

| Panel | Description |
|-------|-------------|
| **Status** | Server health, crystals count |
| **Session Stats** | Queries, tokens saved, % savings |
| **Quick Actions** | Reindex, Validate, Reset |

### 3.3 First Use

1. Open project folder
2. Click "Initialize" in sidebar
3. Wait for indexing (< 30s for 2000 files)
4. Start querying!

---

## Part 4: Token Savings

### View Real-time Stats

```python
stats = rlm_session_stats()
print(f"Queries: {stats['session']['queries']}")
print(f"Saved: {stats['session']['tokens_saved']}")
print(f"Savings: {stats['session']['savings_percent']}%")
```

### Metrics Example (SENTINEL)

| Metric | Value |
|--------|-------|
| Files indexed | 1,967 |
| Raw context | 586.7M tokens |
| Compressed | 10.5M tokens |
| **Savings** | **98.2%** |
| **Compression** | **56x** |

---

## Part 5: Security

### Encryption (Default: ON)

```bash
# Disable (dev only)
export RLM_SECURE_MEMORY=false
```

### Rate Limiting

`rlm_reindex` is limited to 1 request per 60 seconds.

### Files Protected

`.rlm/.encryption_key` is auto-excluded from git.

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "MCP not available" | `pip install mcp` |
| "Rate limited" | Wait 60 seconds |
| "Context not found" | Load context first |
| Extension not showing | Restart VS Code |

---

## Next Steps

- [Crystal Architecture](../concepts/crystal.md)
- [Freshness Monitoring](../concepts/freshness.md)
- [Security](../concepts/security.md)
