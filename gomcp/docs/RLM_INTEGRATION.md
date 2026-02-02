# RLM Integration Guide

> How to integrate GoMCP as the MCP backend for RLM Toolkit

## Overview

GoMCP provides a high-performance MCP server that replaces the Python spawn approach in RLM Toolkit. This eliminates cold-start latency and event loop blocking issues.

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                 VSCode Extension                          │
│                   (TypeScript)                            │
│  ┌────────────────────────────────────────────────────┐  │
│  │              GoMCPClient                            │  │
│  │  - Persistent connection                            │  │
│  │  - JSON-RPC over stdio                              │  │
│  └────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────┘
                         │ stdio
                         ▼
┌──────────────────────────────────────────────────────────┐
│                  rlm-mcp-server                           │
│                      (Go)                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌─────────────┐  │
│  │ Session  │ │ Tasks    │ │ Hooks    │ │ Python      │  │
│  │ Manager  │ │ Manager  │ │ Registry │ │ Bridge      │  │
│  └──────────┘ └──────────┘ └──────────┘ └─────────────┘  │
└────────────────────────┬─────────────────────────────────┘
                         │ Python bridge (for complex tools)
                         ▼
┌──────────────────────────────────────────────────────────┐
│                   rlm_worker.py                           │
│  - HierarchicalMemoryStore                                │
│  - Extractors                                             │
│  - Vector search                                          │
└──────────────────────────────────────────────────────────┘
```

## Installation

### 1. Build the Server

```bash
cd gomcp
go build -o bin/rlm-mcp-server ./cmd/rlm-mcp-server/
```

### 2. Install TypeScript SDK

```bash
cd sdk/typescript
npm install
npm run build
```

### 3. Update VSCode Extension

Replace `RLMMcpClient` with `GoMCPClient`:

```typescript
// Before
import { RLMMcpClient } from './mcpClient';
const client = new RLMMcpClient();
const status = await client.getStatus();

// After
import { GoMCPClient } from '@gomcp/client';
const client = new GoMCPClient({ projectRoot: '/path/to/project' });
await client.start();
const status = await client.getStatus();
```

## Usage

### Quick Start

```typescript
import { GoMCPClient } from '@gomcp/client';

// Create client
const client = new GoMCPClient({
    projectRoot: vscode.workspace.workspaceFolders[0].uri.fsPath,
});

// Start server (persistent connection)
await client.start();

// Use RLM tools
const status = await client.getStatus();
const health = await client.healthCheck();
const context = await client.enterpriseContext("architecture patterns");

// Clean up
client.stop();
```

### Hybrid Mode (Fallback to Python)

```typescript
import { RLMHybridClient } from '@gomcp/client';

const client = new RLMHybridClient(projectRoot);
await client.initialize();  // Tries GoMCP, falls back to Python

const status = await client.getStatus();  // Uses best available backend
```

## Server Options

```bash
rlm-mcp-server [options]

Options:
  -mode string      Server mode: stdio, http, grpc (default "stdio")
  -port int         Port for HTTP/gRPC mode (default 8080)
  -project string   Project root path
  -python string    Python interpreter (default "python")
  -worker string    Python worker script path
  -debug            Enable debug logging
```

## Tools

### Go Native (Fast Path)

These tools are implemented in Go for maximum performance:

| Tool | Description |
|------|-------------|
| `rlm_status` | Server status and metrics |
| `rlm_health_check` | Component health |

### Python Bridge (Delegated)

These tools require Python for complex operations:

| Tool | Description |
|------|-------------|
| `rlm_discover_project` | Project discovery with extractors |
| `rlm_enterprise_context` | Semantic search + causal chains |
| `rlm_get_hierarchy_stats` | Memory store statistics |
| `rlm_add_hierarchical_fact` | Add facts to memory |
| `rlm_search_facts` | Hybrid search |
| `rlm_reindex` | Full reindex with Python indexer |

## Performance

| Metric | Python Spawn | GoMCP |
|--------|--------------|-------|
| Startup | ~500ms | ~5ms |
| Memory | 50MB/call | Shared |
| Concurrency | Limited | Unlimited |
| Event loop | Blocking | Non-blocking |

## Troubleshooting

### Server won't start

1. Check if binary exists:
   ```bash
   which rlm-mcp-server
   ```

2. Check Python availability:
   ```bash
   python --version
   ```

3. Enable debug mode:
   ```bash
   rlm-mcp-server -debug -mode=stdio
   ```

### Python tools fail

1. Verify `rlm_worker.py` exists
2. Check RLM_PROJECT_ROOT environment variable
3. Ensure rlm_toolkit is installed:
   ```bash
   pip install -e rlm-toolkit
   ```
