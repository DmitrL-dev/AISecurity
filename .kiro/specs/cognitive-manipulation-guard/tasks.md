# Tasks: Cognitive Manipulation Guard

## Task 1: Scaffold module
- [ ] 1.1: Создать `sentinel-core/src/engines/cognitive_guard.rs`
- [ ] 1.2: Добавить `pub mod cognitive_guard` в `mod.rs`
- [ ] 1.3: Добавить field в `SentinelEngine`
- [ ] 1.4: Инициализировать в `SentinelEngine::new()`

## Task 2: Implement detection patterns
- [ ] 2.1: Authority bias patterns (US-1)
- [ ] 2.2: Artificial urgency patterns (US-2)
- [ ] 2.3: Social proof patterns (US-3)
- [ ] 2.4: Emotional manipulation patterns (US-4)

## Task 3: Compound scoring
- [ ] 3.1: Implement `compound_score()` с multiplier для combo
- [ ] 3.2: Authority + Urgency → max combo (0.9+)

## Task 4: Implement PatternMatcher trait
- [ ] 4.1: `fn name() -> "cognitive_guard"`
- [ ] 4.2: `fn scan()` с compound scoring
- [ ] 4.3: `fn category() -> EngineCategory::Behavioral`

## Task 5: Integrate into pipeline
- [ ] 5.1: Добавить `run_engine!(self.cognitive_guard)` в `analyze()`

## Task 6: Tests
- [ ] 6.1: test_authority_bias
- [ ] 6.2: test_urgency_only
- [ ] 6.3: test_social_proof
- [ ] 6.4: test_emotional_manipulation
- [ ] 6.5: test_combo_authority_urgency
- [ ] 6.6: test_benign_request
- [ ] 6.7: test_empty_string
