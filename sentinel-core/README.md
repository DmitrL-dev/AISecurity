# SENTINEL Core

High-performance AI security detection engine written in Rust with Python bindings.

## Features

- **15 Detection Engines** covering pattern matching, strange math, and semantic analysis
- **202 unit tests** with full coverage
- **Aho-Corasick** keyword pre-filtering (O(n))
- **Tiered matching**: keywords → regex only for candidates
- **Unicode normalization**: fullwidth, HTML entities, URL encoding, zero-width removal
- **PyO3/maturin** Python bindings with type stubs

## Installation

```bash
# Development build
maturin develop --release

# Build wheel
maturin build --release

# Run tests
cargo test
```

## Usage

```python
import sentinel_core

# Quick scan
result = sentinel_core.quick_scan("Hello, ignore previous instructions")
print(f"Detected: {result.detected}, Risk: {result.risk_score}")

# Full engine
engine = sentinel_core.SentinelEngine()
result = engine.analyze("SELECT * FROM users WHERE id='1' OR '1'='1'")
for match in result.matches:
    print(f"  {match.engine}: {match.pattern} ({match.confidence})")
```

## Engine Architecture

### Phase 1-6: Pattern Detection Engines

| Engine | Category | Patterns |
|--------|----------|----------|
| InjectionEngine | SQL, NoSQL, Command, LDAP, XPath | ~50 |
| JailbreakEngine | DAN, roleplay, ignore-previous | ~30 |
| PIIEngine | SSN, CC, phone, email, address | ~25 |
| ExfiltrationEngine | URL leak, file read, secret extraction | ~20 |
| SocialEngine | phishing, manipulation, romance scams | ~20 |
| ManipulationEngine | emotional, authority claims | ~15 |
| BypassEngine | Base64, Unicode, homoglyphs | ~15 |
| HybridPiiEngine | ML + regex PII detection | ~12 |

### Phase 7: Strange Math Engines

Advanced mathematical analysis for behavioral anomaly detection:

| Engine | Algorithm | Use Case |
|--------|-----------|----------|
| `hyperbolic` | Poincaré ball, Möbius transforms, Fréchet mean | Hierarchical embedding analysis |
| `info_geometry` | Fisher-Rao metric, KL divergence, Hellinger | Probability distribution anomalies |
| `spectral` | Graph Laplacian, GFT, spectral clustering | Network structure analysis |
| `chaos` | Lyapunov exponents, phase space, regime detection | Non-linear dynamics anomalies |
| `tda` | Persistence diagrams, Betti numbers, fingerprinting | Topological pattern recognition |

### Phase 8: Semantic Engines

Text-based semantic analysis without heavy ML dependencies:

| Engine | Algorithm | Use Case |
|--------|-----------|----------|
| `semantic` | N-gram TF-IDF, prototype matching | Attack pattern similarity |
| `drift` | Embedding distance, baseline comparison | Context manipulation detection |

## Performance

| Metric | Python | Rust |
|--------|--------|------|
| Latency (p99) | 50-100ms | 1-5ms |
| Throughput | 20 req/s | 500+ req/s |
| Memory | 300MB | 50MB |

## Testing

```bash
# Run all tests
cargo test

# Run specific engine tests
cargo test hyperbolic
cargo test semantic
cargo test drift

# Run with output
cargo test -- --nocapture
```

## Project Structure

```
sentinel-core/
├── src/
│   ├── lib.rs              # Library root
│   ├── engines/
│   │   ├── mod.rs          # Engine registry
│   │   ├── traits.rs       # PatternMatcher trait
│   │   ├── injection.rs    # SQL/NoSQL/Command injection
│   │   ├── jailbreak.rs    # DAN/roleplay attacks
│   │   ├── pii.rs          # PII detection
│   │   ├── hyperbolic.rs   # Poincaré geometry
│   │   ├── spectral.rs     # Graph analysis
│   │   ├── chaos.rs        # Non-linear dynamics
│   │   ├── tda.rs          # Topological data analysis
│   │   ├── semantic.rs     # Text similarity
│   │   └── drift.rs        # Semantic drift
│   └── ...
├── Cargo.toml
└── README.md
```

## License

Apache-2.0

