# Deprecated Pattern Engines

These Python engines have been replaced by high-performance Rust implementations in `sentinel-core/src/engines/`.

## Replaced Engines

| Python Engine | Rust Replacement | Performance |
|--------------|------------------|-------------|
| `injection.py` | `injection.rs` | 1.3 µs |
| `pii.py` | `pii.rs` | 2.2 µs |
| `injection/` (multi-layer) | `injection.rs` | 1.3 µs |

## Migration Date
2026-02-04

## Reference
Use `sentinel_core.SentinelEngine` or `HybridAnalyzer` instead.

## Do NOT Delete
Keep for reference and potential rollback scenarios.
