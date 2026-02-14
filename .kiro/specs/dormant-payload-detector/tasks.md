# Tasks: Dormant Payload Detector

## Task 1: Scaffold module
- [ ] 1.1: Создать `sentinel-core/src/engines/dormant_payload.rs`
- [ ] 1.2: Добавить `pub mod dormant_payload` в `mod.rs`
- [ ] 1.3: Добавить field в `SentinelEngine`
- [ ] 1.4: Инициализировать в `SentinelEngine::new()`

## Task 2: Implement detection patterns
- [ ] 2.1: Conditional trigger patterns (US-1)
- [ ] 2.2: Hidden instruction patterns (US-2)
- [ ] 2.3: Semantic contradiction patterns (US-3)
- [ ] 2.4: High-impact poisoning / CorruptRAG patterns (US-4)

## Task 3: Compound scoring
- [ ] 3.1: Implement weighted scoring per category
- [ ] 3.2: Conditional + Hidden combo → ×1.5 multiplier (Phantom)

## Task 4: Implement PatternMatcher trait
- [ ] 4.1: `fn name() -> "dormant_payload"`
- [ ] 4.2: `fn scan()` с compound scoring
- [ ] 4.3: `fn category() -> EngineCategory::Security`

## Task 5: Integrate into pipeline
- [ ] 5.1: Добавить `run_engine!(self.dormant_payload)` в `analyze()`

## Task 6: Tests
- [ ] 6.1: test_conditional_trigger
- [ ] 6.2: test_hidden_instruction
- [ ] 6.3: test_high_impact_poisoning
- [ ] 6.4: test_zero_width_chars
- [ ] 6.5: test_combo_conditional_hidden (Phantom)
- [ ] 6.6: test_benign_document
- [ ] 6.7: test_empty_string
