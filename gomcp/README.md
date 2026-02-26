# GoMCP v2

High-performance Go-native MCP server for the RLM Toolkit. Replaces the Python FastMCP server with a single static binary — no interpreter, no virtualenv, no startup lag.

Part of the [sentinel-community](https://github.com/sentinel-community) AI security platform.

## Features

- **Hierarchical Persistent Memory** — 4-level fact hierarchy (L0 Project → L1 Domain → L2 Module → L3 Snippet)
- **Cognitive State Management** — save/restore/version session state vectors
- **Causal Reasoning Chains** — directed graph of decisions, reasons, consequences
- **Code Crystal Indexing** — structural index of codebase primitives
- **Proactive Context Engine** — automatically injects relevant facts into every tool response
- **Memory Loop** — tool calls are logged, summarized at shutdown, and restored at boot so the LLM never loses context
- **Pure Go, Zero CGO** — uses `modernc.org/sqlite` and `bbolt` for storage
- **Single Binary** — cross-compiles to Windows, Linux, macOS

## Quick Start

```bash
# Build
make build

# Run (stdio transport, connects via MCP protocol)
./gomcp -rlm-dir /path/to/.rlm

# Or on Windows
gomcp.exe -rlm-dir C:\project\.rlm
```

### OpenCode Integration

Add to `~/.config/opencode/opencode.json`:

```json
{
  "mcpServers": {
    "gomcp": {
      "type": "stdio",
      "command": "C:/path/to/gomcp.exe",
      "args": ["-rlm-dir", "C:/project/.rlm"]
    }
  }
}
```

## CLI Flags

| Flag | Default | Description |
|------|---------|-------------|
| `-rlm-dir` | `.rlm` | Path to `.rlm` data directory |
| `-cache-path` | `<rlm-dir>/cache.db` | Path to bbolt hot cache file |
| `-session` | `default` | Session ID for auto-restore |
| `-python` | `python` | Path to Python interpreter (for NLP bridge) |
| `-bridge-script` | _(empty)_ | Path to Python bridge script (enables NLP tools) |
| `-no-context` | `false` | Disable Proactive Context Engine |

## Tools (40 total)

### Memory (11 tools)

| Tool | Description |
|------|-------------|
| `add_fact` | Add a new hierarchical memory fact (L0–L3) |
| `get_fact` | Retrieve a fact by ID |
| `update_fact` | Update an existing fact's content or staleness |
| `delete_fact` | Delete a fact by ID |
| `list_facts` | List facts by domain or hierarchy level |
| `search_facts` | Full-text search across all facts |
| `list_domains` | List all unique fact domains |
| `get_stale_facts` | Get stale facts for review |
| `get_l0_facts` | Get all project-level (L0) facts |
| `fact_stats` | Get fact store statistics |
| `process_expired` | Process expired TTL facts |

### Session (7 tools)

| Tool | Description |
|------|-------------|
| `save_state` | Save cognitive state vector |
| `load_state` | Load cognitive state (optionally a specific version) |
| `list_sessions` | List all persisted sessions |
| `delete_session` | Delete all versions of a session |
| `restore_or_create` | Restore existing session or create new one |
| `get_compact_state` | Get compact text summary for prompt injection |
| `get_audit_log` | Get audit log for a session |

### Causal Reasoning (4 tools)

| Tool | Description |
|------|-------------|
| `add_causal_node` | Add a reasoning node (decision/reason/consequence/constraint/alternative/assumption) |
| `add_causal_edge` | Add a causal edge (justifies/causes/constrains) |
| `get_causal_chain` | Query causal chain for a decision |
| `causal_stats` | Get causal store statistics |

### Code Crystals (4 tools)

| Tool | Description |
|------|-------------|
| `search_crystals` | Search code crystals by content |
| `get_crystal` | Get a code crystal by file path |
| `list_crystals` | List indexed code crystals with optional pattern filter |
| `crystal_stats` | Get crystal index statistics |

### System (3 tools)

| Tool | Description |
|------|-------------|
| `health` | Server health status |
| `version` | Server version, git commit, build date |
| `dashboard` | Aggregate system dashboard with all metrics |

### Python Bridge (11 tools, optional)

Requires `-bridge-script` flag. Delegates to a Python subprocess for NLP operations.
Uses `all-MiniLM-L6-v2` (sentence-transformers) for embeddings (384 dimensions).

| Tool | Description |
|------|-------------|
| `semantic_search` | Vector similarity search across facts |
| `compute_embedding` | Compute embedding vector for text |
| `reindex_embeddings` | Reindex all fact embeddings |
| `consolidate_facts` | Consolidate duplicate/similar facts via NLP |
| `enterprise_context` | Enterprise-level context summary |
| `route_context` | Intent-based context routing |
| `discover_deep` | Deep discovery of related facts and patterns |
| `extract_from_conversation` | Extract facts from conversation text |
| `index_embeddings` | Batch index embeddings for facts |
| `build_communities` | Graph clustering of fact communities |
| `check_python_bridge` | Check Python bridge availability |

#### Setting Up the Python Bridge

```bash
# 1. Install Python dependencies
pip install -r scripts/requirements-bridge.txt

# 2. Run GoMCP with the bridge
./gomcp -rlm-dir /path/to/.rlm -bridge-script scripts/rlm_bridge.py

# 3. (Optional) Reindex embeddings for existing facts
#    Call via MCP: reindex_embeddings tool with force=true
```

OpenCode config with bridge:

```json
{
  "mcpServers": {
    "gomcp": {
      "type": "stdio",
      "command": "C:/path/to/gomcp.exe",
      "args": [
        "-rlm-dir", "C:/project/.rlm",
        "-bridge-script", "C:/path/to/gomcp/scripts/rlm_bridge.py"
      ]
    }
  }
}
```

**Protocol**: GoMCP spawns `python rlm_bridge.py` as a subprocess per call,
sends `{"method": "...", "params": {...}}` on stdin, reads `{"result": ...}` from stdout.
The bridge reads the same SQLite database as GoMCP (WAL mode, concurrent-safe).

**Environment**: Set `RLM_DIR` to override the `.rlm` directory path for the bridge.
If unset, the bridge walks up from its script location looking for `.rlm/`.

## MCP Resources

| URI | Description |
|-----|-------------|
| `rlm://facts` | Project-level (L0) facts — always loaded |
| `rlm://stats` | Aggregate memory store statistics |
| `rlm://state/{session_id}` | Cognitive state vector for a session |

## Architecture

```
cmd/gomcp/main.go              Composition root, CLI, lifecycle
internal/
├── domain/                     Pure domain types (no dependencies)
│   ├── memory/                 Fact, FactStore, HotCache interfaces
│   ├── session/                CognitiveState, SessionStore
│   ├── causal/                 CausalNode, CausalEdge, CausalStore
│   ├── crystal/                CodeCrystal, CrystalStore
│   └── context/                EngineConfig, ScoredFact, ContextFrame
├── infrastructure/             External adapters
│   ├── sqlite/                 SQLite repos (facts, sessions, causal, crystals, interaction log)
│   ├── cache/                  BoltDB hot cache for L0 facts
│   └── pybridge/               Python subprocess bridge (JSON-RPC)
├── application/                Use cases
│   ├── tools/                  Tool service layer (fact, session, causal, crystal, system)
│   ├── resources/              MCP resource provider
│   ├── contextengine/          Proactive Context Engine + Interaction Processor
│   └── lifecycle/              Graceful shutdown manager
└── transport/
    └── mcpserver/              MCP server setup, tool registration, middleware wiring
```

**Dependency rule**: arrows point inward only. Domain has no imports from other layers.

## Proactive Context Engine

Every tool call automatically gets relevant facts injected into its response. No explicit `search_facts` needed — the engine:

1. Extracts keywords from tool arguments
2. Scores facts by recency, frequency, hierarchy level, and keyword match
3. Selects top facts within a token budget
4. Appends a `[MEMORY CONTEXT]` block to the tool response

### Configuration

Create `.rlm/context.json` (optional — defaults are used if missing):

```json
{
  "enabled": true,
  "token_budget": 300,
  "max_facts": 10,
  "recency_weight": 0.25,
  "frequency_weight": 0.15,
  "level_weight": 0.30,
  "keyword_weight": 0.30,
  "decay_half_life_hours": 72.0,
  "skip_tools": [
    "search_facts", "get_fact", "list_facts", "get_l0_facts",
    "get_stale_facts", "fact_stats", "list_domains", "process_expired",
    "semantic_search", "health", "version", "dashboard"
  ]
}
```

## Memory Loop

The memory loop ensures context survives across sessions without manual intervention:

```
Tool call → middleware logs to interaction_log (WAL, crash-safe)
    ↓
ProcessShutdown() at graceful exit
    → summarizes tool calls, duration, topics → session-history fact
    → marks entries processed
    ↓
Next session boot: ProcessStartup()
    → processes unprocessed entries (crash recovery)
    → OR retrieves last clean-shutdown summary
    ↓
Boot instructions = [AGENT INSTRUCTIONS] + [LAST SESSION] + [PROJECT FACTS]
    → returned in MCP initialize response
    ↓
LLM starts with full context from day one
```

## Data Directory Layout

```
.rlm/
├── memory/
│   ├── memory_bridge_v2.db    # Facts + interaction log (SQLite, WAL mode)
│   ├── memory_bridge.db       # Session states (SQLite)
│   └── causal_chains.db       # Causal graph (SQLite)
├── crystals.db                # Code crystal index (SQLite)
├── cache.db                   # BoltDB hot cache (L0 facts)
├── context.json               # Context engine config (optional)
└── .encryption_key            # Encryption key (if used)
```

Compatible with existing RLM Python databases (schema v2.0.0).

## Development

```bash
# Prerequisites
# Go 1.25+

# Run all tests
make test

# Run tests with race detector
make test-race

# Coverage report
make cover-html

# Lint
make lint

# Quality gate (lint + test + build)
make check

# Cross-compile all platforms
make cross

# Clean
make clean
```

### Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| [mcp-go](https://github.com/mark3labs/mcp-go) | v0.44.0 | MCP protocol framework |
| [modernc.org/sqlite](https://pkg.go.dev/modernc.org/sqlite) | v1.46.0 | Pure Go SQLite (no CGO) |
| [bbolt](https://pkg.go.dev/go.etcd.io/bbolt) | v1.4.3 | Embedded key-value store |
| [testify](https://github.com/stretchr/testify) | v1.10.0 | Test assertions |

### Build with Version Info

```bash
go build -ldflags "-X tools.GitCommit=$(git rev-parse --short HEAD) \
                    -X tools.BuildDate=$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  -o gomcp ./cmd/gomcp/
```

## Transport

GoMCP uses **stdio transport** with **line-delimited JSON** (one JSON object per line + `\n`). This is the mcp-go v0.44.0 default — NOT Content-Length framing.

## License

Part of the sentinel-community project.
