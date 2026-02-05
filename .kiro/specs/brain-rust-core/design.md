# Brain Rust Core — Design Document

> **SDD for Full Rust Migration**  
> **Status:** COMPLETE (Feb 2026)  
> **Scope:** 36 engines, 455 tests, 90.3% coverage

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    sentinel_core (Rust)                      │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Pattern Engines ✅                                │
│  ┌─────────┬─────────┬─────────┬─────────┐                  │
│  │injection│jailbreak│   pii   │exfiltrat│                  │
│  ├─────────┼─────────┼─────────┼─────────┤                  │
│  │moderat. │ evasion │tool_ab. │ social  │                  │
│  └─────────┴─────────┴─────────┴─────────┘                  │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Strange Math Engines ✅                           │
│  ┌─────────┬─────────┬─────────┬─────────┐                  │
│  │   tda   │hyperbol.│info_geo │  chaos  │                  │
│  ├─────────┼─────────┼─────────┴─────────┘                  │
│  │  sheaf  │category │                                      │
│  └─────────┴─────────┘                                      │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Semantic/Analysis ✅                              │
│  ┌─────────┬─────────┬─────────┬─────────┐                  │
│  │spectral │formal   │behavior.│ runtime │                  │
│  ├─────────┼─────────┼─────────┼─────────┤                  │
│  │knowledge│synth.   │proactive│supply_ch│                  │
│  └─────────┴─────────┴─────────┴─────────┘                  │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: ML Inference ✅                                   │
│  ┌─────────┬─────────┬─────────┬─────────┐                  │
│  │embedding│semantic │attention│   vae   │                  │
│  └─────────┴─────────┴─────────┴─────────┘                  │
├─────────────────────────────────────────────────────────────┤
│  Layer 5: Domain-Specific ✅                                │
│  ┌─────────┬─────────┬─────────┬─────────┐                  │
│  │   rag   │   mcp   │ agentic │privacy  │                  │
│  ├─────────┼─────────┼─────────┼─────────┤                  │
│  │orchestr.│threat_i.│obfuscat.│compli.  │                  │
│  └─────────┴─────────┴─────────┴─────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Dependency Graph (Feb 2026)

```toml
[dependencies]
# Core
pyo3 = "0.27.2"          # Python bindings (updated Jan 2026)
regex = "1.12.2"         # Pattern matching
aho-corasick = "1.1"     # Multi-pattern search
once_cell = "1.21.3"     # Lazy statics
serde = "1.0.228"        # Serialization
rayon = "1.11.0"         # Parallelism
thiserror = "2.0.18"     # Error handling

# Math/Linear Algebra
nalgebra = "0.33"        # Linear algebra
statrs = "0.18"          # Statistics

# ML Inference (feature = "ml")
ort = "2.0.0-rc.11"      # ONNX Runtime
ndarray = "0.17.2"       # N-dimensional arrays
tokenizers = "0.22.2"    # HuggingFace tokenizers

# CDN Signatures (feature = "cdn")
reqwest = "0.12"         # HTTP client
tokio = "1.49.0"         # Async runtime
sha2 = "0.10"            # Hash verification
directories = "5.0"      # Platform paths

[dev-dependencies]
criterion = "0.8.1"      # Benchmarks
proptest = "1.6"         # Property-based testing
arbitrary = "1.4"        # Fuzz testing

[features]
default = []
cdn = ["reqwest", "tokio", "sha2", "directories"]
ml = ["ort", "ndarray", "tokenizers"]
```

---

## Engine Inventory (36 Total)

| Category | Engines | Status |
|----------|---------|--------|
| Pattern (8) | injection, jailbreak, pii, exfiltration, moderation, evasion, tool_abuse, social | ✅ |
| Strange Math (6) | tda, hyperbolic, info_geometry, chaos, sheaf, category | ✅ |
| Semantic (8) | spectral, formal, behavioral, runtime, knowledge, synthesis, proactive, supply_chain | ✅ |
| ML (4) | embedding, semantic_engine, attention, vae | ✅ |
| Domain (10) | rag, mcp, agentic, privacy, orchestration, threat_intel, obfuscation, compliance, attack, hybrid | ✅ |

---

## Performance Verified

| Engine Type | Target | Actual |
|-------------|--------|--------|
| Pattern (Layer 1) | <10 µs | **1-6 µs** ✅ |
| Strange Math | <100 µs | **10-50 µs** ✅ |
| Semantic | <500 µs | **50-200 µs** ✅ |
| ML Inference (ONNX BGE-M3) | <100 ms | **42-66 ms** ✅ |
| Domain | <50 µs | **5-20 µs** ✅ |

---

## Testing Strategy (Feb 2026)

| Test Type | Count | Coverage |
|-----------|-------|----------|
| Unit tests | 433 | Core logic |
| Property tests (proptest) | 17 | Invariants |
| Golden tests | 5 | Regression |
| **Total** | **455** | **90.30%** |

### Property Tests Cover:
- No-panic on arbitrary input (all engines)
- Detection of known patterns (SQL tautology, DAN, emails, SSN)
- Determinism (same input → same output)
- Russian locale support

### Golden Tests Cover:
- SQL injection patterns
- Jailbreak patterns
- PII patterns
- Exfiltration patterns
- API stability

---

## ML Inference (ONNX BGE-M3)

```rust
pub struct OnnxEmbedder {
    session: Mutex<Session>,  // Thread-safe ONNX session
    tokenizer: Tokenizer,     // HuggingFace tokenizer
    dimension: usize,         // 1024 for BGE-M3
    max_length: usize,        // 512 tokens
}

impl EmbeddingProvider for OnnxEmbedder {
    fn embed(&self, text: &str) -> EmbeddingResult;
}
```

| Metric | Value |
|--------|-------|
| Model | BGE-M3 (BAAI) |
| Dimensions | 1024 |
| Model size | 2.2 GB |
| Load time | ~6s |
| Inference | 42-66 ms (CPU) |
| Semantic similarity | 0.88 (attack-attack) vs 0.60 (attack-benign) |

---

## ADR: Key Decisions

### ADR-001: Remove token_type_ids from ONNX inputs
- **Context:** BGE-M3 ONNX export only has 2 inputs (input_ids, attention_mask)
- **Decision:** Remove token_type_ids from embed() method
- **Consequence:** ONNX inference works correctly

### ADR-002: Use Mutex for ONNX Session
- **Context:** ORT Session doesn't support &self.run()
- **Decision:** Wrap Session in Mutex<Session>
- **Consequence:** Thread-safe inference, minor lock overhead

### ADR-003: Use fancy-regex over onig
- **Context:** onig causes Windows LNK2005 linker errors
- **Decision:** Use tokenizers with fancy-regex feature
- **Consequence:** No C++ runtime conflicts

### ADR-004: Update to PyO3 0.27
- **Context:** PyO3 0.22 was outdated
- **Decision:** Major version update 0.22 → 0.27
- **Consequence:** No breaking changes, improved performance

---

## Known Gaps (Future Work)

| Gap | Priority | Notes |
|-----|----------|-------|
| Discord webhooks | Low | Not detected by exfiltration engine |
| "pretend you have no restrictions" | Low | Not detected by jailbreak engine |
| GPU acceleration | Medium | ONNX supports CUDA/DirectML |
| CJK locale patterns | Low | Chinese/Japanese/Korean |

---

## Created/Updated
- Created: 2026-02-04
- Updated: 2026-02-05
