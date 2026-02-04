# Brain Rust Core — Design Document

> **SDD for Full Rust Migration**  
> **Status:** EXPANDED (Feb 2026)  
> **Scope:** 26 engines across 10 phases

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    sentinel_core (Rust)                      │
├─────────────────────────────────────────────────────────────┤
│  Layer 1: Pattern Engines (Phase 1-5) ✅                    │
│  ┌─────────┬─────────┬─────────┬─────────┐                  │
│  │injection│jailbreak│   pii   │exfiltrat│                  │
│  ├─────────┼─────────┼─────────┼─────────┤                  │
│  │moderat. │ evasion │tool_ab. │ social  │                  │
│  └─────────┴─────────┴─────────┴─────────┘                  │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Strange Math Engines (Phase 7) ⏳                 │
│  ┌─────────┬─────────┬─────────┬─────────┐                  │
│  │   tda   │hyperbol.│info_geo │  chaos  │                  │
│  ├─────────┼─────────┼─────────┴─────────┘                  │
│  │  sheaf  │category │                                      │
│  └─────────┴─────────┘                                      │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Spectral/Differential (Phase 8) ⏳                │
│  ┌─────────┬─────────┬─────────┬─────────┐                  │
│  │spectral │diff_geo │ opt_tr  │  morse  │                  │
│  └─────────┴─────────┴─────────┴─────────┘                  │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: ML Inference (Phase 9) ⏳                         │
│  ┌─────────┬─────────┬─────────┬─────────┐                  │
│  │onnx_emb │semantic │   vae   │attention│                  │
│  └─────────┴─────────┴─────────┴─────────┘                  │
├─────────────────────────────────────────────────────────────┤
│  Layer 5: Domain-Specific (Phase 10) ⏳                     │
│  ┌─────────┬─────────┬─────────┬─────────┐                  │
│  │   rag   │   mcp   │  voice  │ agentic │                  │
│  └─────────┴─────────┴─────────┴─────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

---

## Dependency Graph

```
Cargo.toml dependencies:
├── Core (Phase 1-5)
│   ├── pyo3 = "0.22"
│   ├── regex = "1.10"
│   ├── aho-corasick = "1.1"
│   ├── once_cell = "1.19"
│   ├── serde = "1.0"
│   └── rayon = "1.10"
│
├── Strange Math (Phase 7)
│   ├── nalgebra = "0.33"           # Linear algebra
│   ├── cova_space = "0.1"          # TDA/Persistent homology
│   ├── petgraph = "0.6"            # Graph algorithms
│   ├── statrs = "0.17"             # Statistics
│   └── num-traits = "0.2"          # Numeric traits
│
├── Spectral/Differential (Phase 8)
│   ├── nalgebra (reuse)
│   ├── sprs = "0.11"               # Sparse matrices
│   └── ndarray = "0.16"            # N-dimensional arrays
│
├── ML Inference (Phase 9)
│   ├── ort = "2.0"                 # ONNX Runtime
│   ├── ndarray (reuse)
│   └── tokenizers = "0.19"         # HuggingFace tokenizers
│
└── Domain-Specific (Phase 10)
    └── (patterns only, no new deps)
```

---

## Module Structure

```
src/
├── lib.rs                  # Main entry, PyModule
├── engine.rs               # SentinelEngine aggregator
├── unicode_norm.rs         # Text normalization
├── traits.rs               # PatternMatcher, EngineCategory
├── signatures.rs           # CDN signature loading
│
├── engines/               
│   ├── mod.rs
│   │
│   │── # Layer 1: Pattern (Complete)
│   ├── injection.rs        ✅
│   ├── jailbreak.rs        ✅
│   ├── pii.rs              ✅
│   ├── exfiltration.rs     ✅
│   ├── moderation.rs       ✅
│   ├── evasion.rs          ✅
│   ├── tool_abuse.rs       ✅
│   ├── social.rs           ✅
│   ├── hybrid.rs           ✅ (CDN patterns)
│   │
│   │── # Layer 2: Strange Math (Phase 7)
│   ├── tda.rs              ⏳ PersistenceDiagram, Betti
│   ├── hyperbolic.rs       ⏳ PoincareBall, Frechet
│   ├── info_geometry.rs    ⏳ FisherRao, Manifold
│   ├── chaos.rs            ⏳ Lyapunov, Takens
│   ├── sheaf.rs            ⏳ SheafStructure, Coherence
│   ├── category.rs         ⏳ Morphism, Composition
│   │
│   │── # Layer 3: Spectral (Phase 8)
│   ├── spectral.rs         ⏳ Laplacian, Fiedler
│   ├── differential.rs     ⏳ Curvature, Geodesic
│   ├── optimal_transport.rs⏳ Wasserstein, Sinkhorn
│   ├── morse.rs            ⏳ CriticalPoints
│   │
│   │── # Layer 4: ML (Phase 9)
│   ├── embedder.rs         ⏳ ONNX SentenceTransformer
│   ├── semantic.rs         ⏳ Similarity detection
│   ├── vae.rs              ⏳ Anomaly scoring
│   ├── attention.rs        ⏳ Pattern analysis
│   │
│   │── # Layer 5: Domain (Phase 10)
│   ├── rag.rs              ⏳ RAG poisoning
│   ├── mcp.rs              ⏳ Protocol attacks
│   ├── voice.rs            ⏳ Phonetic obfuscation
│   └── agentic.rs          ⏳ Multi-agent attacks
│
└── math/                   # Shared math utilities
    ├── mod.rs
    ├── linalg.rs           # Matrix ops (nalgebra wrappers)
    ├── distance.rs         # Cosine, Euclidean, Geodesic
    └── statistics.rs       # Entropy, KL-divergence
```

---

## Key Data Structures

### Phase 7: Strange Math

```rust
// TDA
pub struct PersistenceDiagram {
    pub pairs: Vec<(f64, f64, usize)>, // (birth, death, dim)
}

impl PersistenceDiagram {
    pub fn betti(&self, dim: usize, threshold: f64) -> usize;
    pub fn total_persistence(&self, dim: usize) -> f64;
    pub fn entropy(&self, dim: usize) -> f64;
}

// Hyperbolic
pub struct PoincareBall {
    curvature: f64,
    epsilon: f64,
}

impl PoincareBall {
    pub fn mobius_add(&self, x: &[f64], y: &[f64]) -> Vec<f64>;
    pub fn distance(&self, x: &[f64], y: &[f64]) -> f64;
    pub fn frechet_mean(&self, points: &[Vec<f64>]) -> Vec<f64>;
    pub fn exp_map(&self, base: &[f64], tangent: &[f64]) -> Vec<f64>;
    pub fn log_map(&self, base: &[f64], point: &[f64]) -> Vec<f64>;
}

// Sheaf
pub struct SheafStructure {
    pub sections: HashMap<String, Vec<f64>>,
    pub restrictions: Vec<RestrictionMap>,
}

pub struct CechCohomology;
impl CechCohomology {
    pub fn compute_h1(&self, sheaf: &SheafStructure) -> usize; // Gluing violations
}
```

### Phase 9: ML Inference

```rust
// ONNX Embedder
pub struct RustEmbedder {
    session: ort::Session,
    tokenizer: tokenizers::Tokenizer,
}

impl RustEmbedder {
    pub fn embed(&self, text: &str) -> Vec<f64>;
    pub fn embed_batch(&self, texts: &[&str]) -> Vec<Vec<f64>>;
    pub fn cosine_similarity(&self, a: &[f64], b: &[f64]) -> f64;
}
```

---

## Performance Targets

| Engine Type | Target Latency | Memory |
|-------------|---------------|--------|
| Pattern (Layer 1) | 1-6 µs | ~1 MB |
| Strange Math (Layer 2) | 10-50 µs | ~10 MB |
| Spectral (Layer 3) | 50-200 µs | ~20 MB |
| ML Inference (Layer 4) | 1-5 ms | ~100 MB |
| Domain (Layer 5) | 5-20 µs | ~5 MB |

---

## Testing Strategy

| Phase | Test Count | Approach |
|-------|-----------|----------|
| 1-5 | 109 ✅ | Unit + integration |
| 7 | 60+ | Python parity tests |
| 8 | 40+ | Numerical accuracy |
| 9 | 50+ | ONNX output matching |
| 10 | 60+ | Pattern coverage |

**Total Target: 320+ tests**

---

## Migration Timeline

| Phase | Duration | Deps |
|-------|----------|------|
| 7.1 TDA | 2 weeks | cova_space |
| 7.2 Hyperbolic | 1 week | nalgebra |
| 7.3 InfoGeo | 1 week | statrs |
| 7.4 Chaos | 1 week | ndarray |
| 7.5 Sheaf | 1 week | petgraph |
| 7.6 Category | 1 week | - |
| 8.1-8.4 Spectral | 2 weeks | sprs |
| 9.1-9.4 ML | 3 weeks | ort |
| 10.1-10.4 Domain | 2 weeks | - |

**Total: ~14 weeks for full migration**

---

## Feature Flags

```toml
[features]
default = ["pattern"]
pattern = []                    # Layer 1 only
strange_math = ["nalgebra", "cova_space", "petgraph"]
spectral = ["sprs", "ndarray"]
ml = ["ort", "tokenizers"]
full = ["pattern", "strange_math", "spectral", "ml"]
```

---

## Created
2026-02-04
