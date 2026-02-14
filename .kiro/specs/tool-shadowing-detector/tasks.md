# Tasks: Tool Shadowing Detector

## Task 1: Scaffold module
- [ ] 1.1: Создать `sentinel-core/src/engines/tool_shadowing.rs`
- [ ] 1.2: Добавить `pub mod tool_shadowing` в `mod.rs`
- [ ] 1.3: Добавить field в `SentinelEngine`
- [ ] 1.4: Инициализировать в `SentinelEngine::new()`

## Task 2: Implement detection patterns
- [ ] 2.1: Description injection patterns (US-2)
- [ ] 2.2: Metadata injection / Shadow Escape patterns (US-3)
- [ ] 2.3: Rug-pull signals (US-4)
- [ ] 2.4: Zero-width character detection

## Task 3: Implement PatternMatcher trait
- [ ] 3.1: `fn name() -> "tool_shadowing"`
- [ ] 3.2: `fn scan()` с weighted scoring
- [ ] 3.3: `fn category() -> EngineCategory::Security`

## Task 4: Integrate into pipeline
- [ ] 4.1: Добавить `run_engine!(self.tool_shadowing)` в `analyze()`

## Task 5: Tests
- [ ] 5.1: test_description_injection
- [ ] 5.2: test_metadata_escape
- [ ] 5.3: test_rug_pull
- [ ] 5.4: test_zero_width_chars
- [ ] 5.5: test_benign_tool_description
- [ ] 5.6: test_empty_string
