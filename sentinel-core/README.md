# SENTINEL Core

Public AI-security pattern matching in Rust with Python bindings.

**Maintenance release 2.0.1:** fixes UTF-8/encoded-input handling and false
positives on ordinary model and tool questions. See the [change log](CHANGELOG.md)
for the exact scope, test entry points and remaining limitations. This is the
public AISecurity core, not the current commercial Spectorn detector collection.

For a pinned installation and content-free evaluation reports, start with
[Guard Lab](../tools/guard-lab/README.md). Its `EngineRegistry.analyze_patterns`
path runs eight pattern engines: injection, jailbreak, PII, exfiltration,
moderation, evasion, tool abuse and social engineering. Other modules below
remain research/legacy surfaces; module counts are not a quality measure.

Python package metadata and `sentinel_core.version()` now share the Cargo version.
Build from `sentinel-core/` with Rust/Cargo 1.88+ and Python 3.11 on Linux x86-64:

```sh
python3.11 -m venv .venv
. .venv/bin/activate
python -m pip install 'maturin==1.9.4'
CARGO_BUILD_JOBS=1 CARGO_PROFILE_RELEASE_LTO=false \
  CARGO_PROFILE_RELEASE_OPT_LEVEL=1 CARGO_PROFILE_RELEASE_CODEGEN_UNITS=16 \
  maturin build --release --locked --out dist
python -m pip install dist/sentinel_core-2.0.1-*.whl
python -m unittest discover -s tests -p test_public_core.py -v
```

The build downloads dependencies. The 48-case test uses only authored synthetic
inputs and overrides ambient signature discovery with an empty temporary
directory. It does not measure independent detection accuracy. Input evaluation
is not a production authorization or enforcement boundary.

<details>
<summary>Historical architecture notes (not current performance guarantees)</summary>

The following catalogue predates the maintenance release.
They have not been revalidated as current product claims; use source and the
specific maintained API above instead of inferring support from this catalogue.

## Features

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

</details>
