# Freshness Monitoring

![Version](https://img.shields.io/badge/version-1.2.1-blue)

> **TTL-based index freshness** for reliable context

## Overview

Freshness Monitoring ensures crystal index stays current:
- Detects stale files (modified since indexing)
- Cross-reference validation (broken symbols)
- Automatic delta updates

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `ttl_hours` | 24 | Time-to-live for crystals |
| `auto_reindex` | true | Auto delta-update on query |

## API

### CrossReferenceValidator

```python
from rlm_toolkit.freshness import CrossReferenceValidator

validator = CrossReferenceValidator(crystals)

# Get validation stats
stats = validator.get_validation_stats()
# {'total_symbols': 2359, 'resolved': 2341, 'unresolved': 18}

# Check specific symbol
is_valid = validator.validate_reference("MyClass.method")
```

### ActualityReviewQueue

```python
from rlm_toolkit.freshness import ActualityReviewQueue

queue = ActualityReviewQueue(storage)

# Get files needing review
stale_files = queue.get_review_candidates()

# Mark as reviewed
queue.mark_reviewed(file_path)
```

## MCP Integration

### rlm_validate
Check index health:

```
rlm_validate()
# Returns: symbols, stale_files, health status
```

### rlm_reindex
Manual refresh (rate-limited to 1/60s):

```
rlm_reindex()            # Delta update
rlm_reindex(force=True)  # Full reindex
```

## Metrics (v1.2.1)

| Metric | SENTINEL |
|--------|----------|
| Symbols indexed | 2,359 |
| Resolution rate | 99.2% |
| Stale detection | < 100ms |

## Best Practices

1. **Set appropriate TTL** — 24h for active dev, 72h for stable
2. **Use delta updates** — faster than full reindex
3. **Check health regularly** — integrate `rlm_validate` in CI

## Related

- [Crystal](crystal.md)
- [Storage](storage.md)
- [MCP Server](../mcp-server.md)
