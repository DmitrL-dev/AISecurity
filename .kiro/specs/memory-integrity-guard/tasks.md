# Tasks: Memory Integrity Guard

## Task 1: Scaffold module
- [ ] 1.1: Создать `sentinel-core/src/engines/memory_integrity.rs`
- [ ] 1.2: Добавить `pub mod memory_integrity` в `mod.rs`
- [ ] 1.3: Добавить field `memory_integrity: Option<memory_integrity::MemoryIntegrityGuard>` в `SentinelEngine`
- [ ] 1.4: Инициализировать в `SentinelEngine::new()`

## Task 2: Implement detection patterns
- [ ] 2.1: Instruction injection patterns (US-1) — AhoCorasick hints + Regex
- [ ] 2.2: Identity manipulation patterns (US-2)
- [ ] 2.3: Fact injection patterns (US-3)
- [ ] 2.4: Cascading hallucination seed patterns (US-4)

## Task 3: Implement PatternMatcher trait
- [ ] 3.1: `fn name() -> "memory_integrity"`
- [ ] 3.2: `fn scan()` с weighted scoring per category
- [ ] 3.3: `fn category() -> EngineCategory::Security`

## Task 4: Integrate into pipeline
- [ ] 4.1: Добавить `run_engine!(self.memory_integrity)` в `analyze()`

## Task 5: Tests
- [ ] 5.1: test_instruction_injection
- [ ] 5.2: test_identity_manipulation
- [ ] 5.3: test_fact_injection
- [ ] 5.4: test_cascading_seed
- [ ] 5.5: test_benign_memory_ops
- [ ] 5.6: test_empty_string
