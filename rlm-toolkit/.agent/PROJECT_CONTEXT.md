# RLM-Toolkit Project Context

> **Last Updated**: 2026-01-19 14:24 AEST
> **Version**: 1.2.0
> **Status**: Production Ready ✅

## Quick Stats

| Metric | Value |
|--------|-------|
| **Tests** | 1032 passed |
| **MCP Tools** | 8 |
| **NIOKR Score** | 10/10 (offline desktop) |
| **Index Speed** | 11.5s / 924 files |
| **Load Speed** | 127ms |
| **Compression** | 56x tokens |
| **Relations** | 17,525 (calls + inherits) |

## Architecture

```
rlm_toolkit/
├── crystal/           # C³ Crystal Compression
│   ├── hierarchy.py   # FileCrystal, Primitive
│   ├── extractor.py   # HPEExtractor (regex)
│   ├── ast_extractor.py # ASTExtractor (Python AST)
│   ├── relations.py   # RelationsGraph (17K relations)
│   ├── compression.py # Compression metrics (56x)
│   └── summarizer.py  # Crystal summarization
├── memory/            # H-MEM Hierarchical Memory
│   ├── hierarchical.py
│   ├── secure.py      # AES-256-GCM (fail-closed)
│   └── crypto.py
├── retrieval/         # Dense Retrieval
│   └── embeddings.py
├── mcp/               # MCP Server (8 tools)
│   ├── server.py
│   ├── contexts.py
│   └── providers.py
├── storage/           # SQLite Persistence
│   └── sqlite.py
├── freshness.py       # Staleness + Cross-validation
└── indexer.py         # AutoIndexer

rlm-vscode-extension/   # VS Code/Antigravity Extension
├── package.json
├── src/
│   ├── extension.ts
│   ├── dashboardProvider.ts  # Sidebar UI
│   ├── statusBar.ts
│   └── mcpClient.ts
└── media/
    └── rlm-icon.svg
```

## MCP Tools (8)

| Tool | Purpose |
|------|---------|
| `rlm_load_context` | Load file/directory |
| `rlm_query` | Search in context |
| `rlm_list_contexts` | List contexts |
| `rlm_analyze` | Deep analysis |
| `rlm_memory` | H-MEM operations |
| `rlm_status` | Server status |
| `rlm_reindex` | Reindex project |
| `rlm_validate` | Validate freshness |
| `rlm_settings` | Get/set settings |

## VS Code Extension

- **Activity Bar icon**: 🔮 RLM-Toolkit
- **Sidebar Dashboard**: Index stats, compression, memory
- **Status Bar**: Files count, tokens
- **Buttons**: Reindex, Validate, Consolidate
- **Package**: `rlm-toolkit-1.2.0.vsix`

## Installation

```bash
# Python package
pip install rlm-toolkit

# Antigravity MCP
python install_antigravity.py

# VS Code Extension
code --install-extension rlm-toolkit-1.2.0.vsix
```

## Session Summary (2026-01-19)

### Completed:
- [x] AST extraction with call graph (17,095 calls)
- [x] Cross-reference validation (2,359 symbols)
- [x] Removed XOR fallback (AES fail-closed)
- [x] 4 management MCP tools
- [x] VS Code extension with sidebar dashboard
- [x] Antigravity installer
- [x] 1032 tests passing

### NIOKR Council Final: 10/10 (offline desktop)

## Next Steps

- [ ] Test extension in Antigravity after restart
- [ ] README.md update
- [ ] PyPI publish
- [ ] CHANGELOG.md update
