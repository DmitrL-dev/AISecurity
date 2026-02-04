# Brain Rust Core — Tasks

## Phase 1: Project Setup (Week 1)

### Task 1.1: Cargo + PyO3 Scaffold
- [x] Создать `sentinel_core/` directory
- [x] `Cargo.toml` с pyo3, regex, aho-corasick
- [x] `pyproject.toml` для maturin
- [x] `src/lib.rs` — basic module structure
- [x] `maturin develop` успешно

### Task 1.2: CI Setup
- [ ] GitHub Actions workflow для wheels
- [ ] Matrix: Windows/Linux/macOS × Python 3.10-3.12
- [ ] Artifact upload

---

## Phase 2: Core Infrastructure (Week 1-2)

### Task 2.1: Unicode Module
- [x] `src/unicode_norm.rs`
- [x] NFKC normalization
- [x] HTML entity decode
- [x] URL decode
- [ ] Base64 detection
- [x] Unit tests

### Task 2.2: Regex Engine
- [x] `src/engines/injection.rs` (contains regex engine)
- [x] `KeywordFilter` (Aho-Corasick) — Lazy static
- [x] `CompiledPattern` struct — via Lazy<Vec<Regex>>
- [x] `tiered_scan()` function — in InjectionEngine.scan()
- [ ] Benchmarks

---

## Phase 3: Super-Engines (Week 2-4)

### Task 3.1: Pattern Migration Script
- [ ] `scripts/migrate_patterns.py`
- [ ] Extract patterns from 210 Python engines
- [ ] Output: `patterns.json`

### Task 3.2: InjectionEngine
- [x] `src/engines/injection.rs`
- [x] SQL, NoSQL, Command patterns (initial)
- [/] ~50 patterns migrated (partial)
- [x] Tests (basic)

### Task 3.3: JailbreakEngine
- [x] `src/engines/jailbreak.rs`
- [x] DAN, roleplay, ignore-previous patterns
- [/] ~30 patterns (partial)
- [x] Tests (basic)

### Task 3.4: PIIEngine
- [ ] `src/patterns/pii.rs`
- [ ] SSN, CC, phone, email, address
- [ ] ~25 patterns
- [ ] Tests

### Task 3.5: Remaining Engines
- [ ] ExfiltrationEngine (~20 patterns)
- [ ] ModerationEngine (~20 patterns)
- [ ] EvasionEngine (~15 patterns)
- [ ] ToolAbuseEngine (~15 patterns)
- [ ] SocialEngine (~12 patterns)

---

## Phase 4: Python Integration (Week 4-5)

### Task 4.1: Python API
- [x] `SentinelEngine` class с #[pymethods]
- [x] `AnalysisResult` / `MatchResult` classes
- [x] `quick_scan()` function

### Task 4.2: Type Stubs
- [ ] `sentinel_core.pyi`
- [ ] Type annotations для всех публичных API

### Task 4.3: Hybrid Analyzer
- [ ] `src/brain/engines/hybrid_analyzer.py`
- [ ] ML router integration
- [ ] Fusion logic

---

## Phase 5: Testing & Rollout (Week 5-6)

### Task 5.1: Regression Tests
- [ ] Migrate all existing Python engine tests
- [ ] 100% pass rate required

### Task 5.2: Benchmarks
- [ ] Latency comparison: Python vs Rust
- [ ] Throughput test
- [ ] Memory profiling

### Task 5.3: A/B Deploy
- [ ] Feature flag: `USE_RUST_ENGINE`
- [ ] Shadow mode comparison
- [ ] Gradual rollout

### Task 5.4: Cleanup
- [ ] Archive 187 Python engines
- [ ] Update documentation
- [ ] Release v2.0

---

**Created:** 2026-02-04
