# RLM-Toolkit VS Code Extension

VS Code / Antigravity IDE extension for RLM-Toolkit.

## Features

- 📊 **Sidebar Dashboard** - View index stats, compression, memory
- 🔄 **One-click Reindex** - Reindex project from UI
- ✓ **Validation** - Check index freshness
- 🧠 **Memory Management** - Consolidate H-MEM
- 📈 **Compression Stats** - See 56x token savings

## Installation

### From Source

```bash
cd rlm-vscode-extension
npm install
npm run compile
```

Then press F5 in VS Code to launch extension in debug mode.

### Package as VSIX

```bash
npm run package
```

Install the generated `.vsix` file via:
- VS Code: Extensions → ... → Install from VSIX

## Usage

1. Open a project in VS Code/Antigravity
2. Click the RLM icon in the Activity Bar (left sidebar)
3. View stats and use buttons to reindex/validate

## Configuration

- `rlm.projectRoot` - Project root for indexing
- `rlm.autoIndex` - Enable auto-indexing on file changes
- `rlm.encryption` - Enable AES-256 encryption

## Requirements

- Python 3.10+
- RLM-Toolkit installed (`pip install rlm-toolkit`)
