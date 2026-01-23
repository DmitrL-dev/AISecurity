# RLM-Toolkit VS Code Extension v2.1

**Recursive Language Models - Unlimited Context for Code Projects**

![Version](https://img.shields.io/badge/version-2.1.0-blue.svg)
![VS Code](https://img.shields.io/badge/VS%20Code-1.85+-green.svg)

## 🚀 What's New in v2.1

### Enterprise Features
- **🏗️ Cold Start Discovery** - One-click project analysis
- **📊 Hierarchical Memory (L0-L3)** - Project → Domain → Module → Code
- **🔒 Health Check Dashboard** - Real-time component status
- **🪝 Git Hook Integration** - Auto-extract facts from commits
- **💉 Semantic Routing** - Embeddings for smart context routing

## Features

### Dashboard Sidebar
The RLM sidebar provides real-time visibility into:
- **Enterprise v2.1** - Total facts, domains, discovery buttons
- **Health Check** - Store, Router, Causal chain status
- **Hierarchical Memory** - L0-L3 fact distribution
- **Project Index** - Files, tokens, symbols
- **Compression** - 56x token savings visualization
- **Session Stats** - Live query/token metrics

### Commands
| Command | Description |
|---------|-------------|
| `RLM: Discover Project (Cold Start)` | Analyze new project, seed template facts |
| `RLM: Enterprise Context Query` | Interactive query with semantic routing |
| `RLM: Health Check` | Show component health status |
| `RLM: Install Git Hook` | Enable auto-extraction on commits |
| `RLM: Index Embeddings` | Generate embeddings for semantic routing |
| `RLM: Reindex Project` | Full project reindex |
| `RLM: Validate Index` | Check index freshness |
| `RLM: Consolidate Memory` | Optimize H-MEM storage |

## Installation

1. Download `rlm-toolkit-2.1.0.vsix` from releases
2. In VS Code: Extensions → `...` menu → Install from VSIX
3. Reload window

## Requirements

- VS Code 1.85+
- Python 3.11+ with `rlm-toolkit` installed
- Project venv or system Python

## Configuration

```json
{
  "rlm.projectRoot": "",           // Auto-detected from workspace
  "rlm.autoIndex": true,           // Auto-index on file changes
  "rlm.encryption": true,          // AES-256 for local storage
  "rlm.autoDiscovery": true        // v2.1: Auto-discover on first load
}
```

## Architecture

```
┌────────────────────────────────────┐
│ VS Code Extension                   │
│  ├─ dashboardProvider.ts           │
│  ├─ extension.ts                   │
│  ├─ mcpClient.ts ──┐               │
│  └─ statusBar.ts   │               │
└────────────────────┼───────────────┘
                     │
                     ▼
┌────────────────────────────────────┐
│ RLM-Toolkit Python Backend         │
│  ├─ mcp_tools_v2.py (18 tools)    │
│  ├─ v2/hierarchical.py            │
│  ├─ v2/coldstart.py               │
│  └─ v2/router.py                  │
└────────────────────────────────────┘
```

## Building

```bash
cd rlm-vscode-extension
npm install
npm run compile
npm run package  # Creates .vsix
```

## License

MIT - Part of RLM-Toolkit by SENTINEL Community
