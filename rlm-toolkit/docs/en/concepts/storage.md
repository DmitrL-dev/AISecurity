# Storage Architecture

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **SQLite-based persistence** for crystals, metrics, and session data

## Overview

RLM-Toolkit uses SQLite for persistent storage of:
- Crystal index (primitives, relations)
- Session statistics (token savings)
- Metadata (TTL, freshness)

## Storage Location

```
.rlm/
├── rlm.db              # SQLite database
├── crystals/           # Serialized crystals
├── memory/             # H-MEM data
├── cache/              # Query cache
└── .encryption_key     # AES key (auto-generated)
```

> ⚠️ `.rlm/` is excluded from git via `.gitignore`

## API

### get_storage()

```python
from rlm_toolkit.storage import get_storage
from pathlib import Path

storage = get_storage(Path("/project"))

# Save crystal
storage.save_crystal(file_path, crystal_data)

# Load all
all_crystals = storage.load_all()

# Get stats
stats = storage.get_stats()
# {'total_crystals': 1967, 'total_tokens': 586700000, 'db_size_mb': 12.5}
```

### Metadata

```python
# Get/set metadata
storage.set_metadata("ttl_hours", 24)
ttl = storage.get_metadata("ttl_hours")

# Session stats
storage.set_metadata("session_stats", {
    "queries": 42,
    "tokens_saved": 1000000
})
```

### Freshness Queries

```python
# Get modified files (need reindex)
modified = storage.get_modified_files(Path("/project"))

# Get stale crystals
stale = storage.get_stale_crystals(ttl_hours=24)
```

## Schema

### crystals table
| Column | Type | Description |
|--------|------|-------------|
| path | TEXT | File path (primary key) |
| crystal | BLOB | Serialized crystal |
| hash | TEXT | Content hash |
| indexed_at | TIMESTAMP | Index time |

### metadata table
| Column | Type | Description |
|--------|------|-------------|
| key | TEXT | Metadata key |
| value | TEXT | JSON value |

## Performance

| Metric | Value |
|--------|-------|
| Index 1967 files | < 30s |
| Query latency | < 10ms |
| DB size (SENTINEL) | 12.5 MB |

## Related

- [Crystal](crystal.md)
- [Freshness Monitoring](freshness.md)
