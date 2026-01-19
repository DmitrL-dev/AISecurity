# C³ Crystal Architecture

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **Context Consciousness Crystal** — Semantic compression for unlimited context

## Overview

C³ provides 56x context compression through hierarchical knowledge extraction.

```
ProjectCrystal
├── ModuleCrystal (package)
│   └── FileCrystal (file)
│       └── Primitive (function, class, import...)
```

## Components

### Primitives
Atomic code elements extracted by HPE (Hierarchical Primitive Extractor):

| Type | Description |
|------|-------------|
| `FUNCTION` | Function definitions |
| `CLASS` | Class definitions |
| `METHOD` | Class methods |
| `IMPORT` | Import statements |
| `CONSTANT` | Module-level constants |
| `DOCSTRING` | Documentation strings |

```python
from rlm_toolkit.crystal import HPEExtractor, PrimitiveType

extractor = HPEExtractor()
primitives = extractor.extract_from_source(source_code)

for p in primitives:
    print(f"{p.ptype}: {p.name} (line {p.source_line})")
```

### FileCrystal
Single file representation:

```python
from rlm_toolkit.crystal import FileCrystal

crystal = extractor.extract_from_file("module.py", content)
print(f"Primitives: {len(crystal.primitives)}")
print(f"Compression: {crystal.compression_ratio}x")
```

### CrystalIndexer
Fast search across all primitives:

```python
from rlm_toolkit.crystal import CrystalIndexer

indexer = CrystalIndexer()
indexer.index_file(crystal)

results = indexer.search("authentication", top_k=5)
```

### SafeCrystal
Integrity-protected wrapper (tamper detection):

```python
from rlm_toolkit.crystal import wrap_crystal

safe = wrap_crystal(crystal, secret_key=b"...")
assert safe.verify()  # Integrity check
```

## Integration

### MCP Server
C³ is used by `rlm_analyze` tool:

```
rlm_analyze(goal="summarize")      # Uses HPE
rlm_analyze(goal="find_bugs")      # Scans primitives
rlm_analyze(goal="security_audit") # Pattern detection
```

### Metrics (v1.2.1)

| Metric | SENTINEL Codebase |
|--------|-------------------|
| Files indexed | 1,967 |
| Call relations | 17,095 |
| Symbols | 2,359 |
| Compression | 56x |

## Related

- [Freshness Monitoring](freshness.md)
- [Storage](storage.md)
- [MCP Server](../mcp-server.md)
