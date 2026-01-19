# How-To: Indexing Projects

![Version](https://img.shields.io/badge/version-1.2.1-blue)

## Quick Start

```python
from rlm_toolkit.indexer import AutoIndexer
from pathlib import Path

indexer = AutoIndexer(Path("/my/project"))
result = indexer.index()

print(f"Files: {result.files_indexed}")
print(f"Duration: {result.duration_seconds}s")
```

## CLI Usage

```bash
# Full index
rlm index /path/to/project

# Delta update only
rlm index /path/to/project --delta

# Force reindex
rlm index /path/to/project --force
```

## MCP Usage

```
rlm_reindex()                 # Delta update
rlm_reindex(force=True)       # Full reindex
rlm_reindex(path="./src")     # Specific path
```

> ⚠️ Rate limited: 1 request per 60 seconds

## Configuration

### .rlmignore

Create `.rlmignore` to exclude files:

```
# Ignore tests
tests/
*_test.py

# Ignore generated
*.generated.py
__pycache__/
```

### Programmatic

```python
indexer = AutoIndexer(
    Path("/project"),
    exclude_patterns=["tests/", "*.min.js"],
    max_file_size_mb=10,
    parallel_workers=4
)
```

## Performance Tips

| Tip | Impact |
|-----|--------|
| Use `.rlmignore` | -30% time |
| Use delta updates | -90% time |
| Increase workers | -50% on multi-core |
| Exclude binaries | -20% storage |

## Troubleshooting

### "Rate limited"
Wait 60 seconds between reindex requests.

### "File too large"
Increase `max_file_size_mb` or add to `.rlmignore`.

### "Permission denied"
Run with appropriate file permissions.

## Related

- [Crystal](../concepts/crystal.md)
- [Freshness](../concepts/freshness.md)
