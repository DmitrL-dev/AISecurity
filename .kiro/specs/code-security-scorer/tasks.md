# Tasks: Code Security Scorer

## Task 1: Scaffold module
- [ ] 1.1: Создать `sentinel-core/src/engines/code_security.rs`
- [ ] 1.2: Добавить `pub mod code_security` в `mod.rs`
- [ ] 1.3: Добавить field в `SentinelEngine`
- [ ] 1.4: Инициализировать в `SentinelEngine::new()`

## Task 2: Implement detection patterns
- [ ] 2.1: SQL injection patterns (US-1)
- [ ] 2.2: OS command injection patterns (US-1)
- [ ] 2.3: XSS patterns (US-1)
- [ ] 2.4: Hardcoded secret patterns (US-2) — API keys, passwords, JWT
- [ ] 2.5: Insecure crypto patterns (US-3) — MD5, eval, disabled TLS
- [ ] 2.6: Path traversal patterns (US-4)
- [ ] 2.7: Slopsquatting heuristics (US-5) — suspicious imports

## Task 3: Implement PatternMatcher trait
- [ ] 3.1: `fn name() -> "code_security"`
- [ ] 3.2: `fn scan()` с CWE-based category tagging
- [ ] 3.3: `fn category() -> EngineCategory::Security`

## Task 4: Integrate into pipeline
- [ ] 4.1: Добавить `run_engine!(self.code_security)` в `analyze()`

## Task 5: Tests
- [ ] 5.1: test_sql_injection
- [ ] 5.2: test_command_injection
- [ ] 5.3: test_xss
- [ ] 5.4: test_api_key_detection
- [ ] 5.5: test_hardcoded_password
- [ ] 5.6: test_weak_crypto
- [ ] 5.7: test_path_traversal
- [ ] 5.8: test_placeholder_not_flagged
- [ ] 5.9: test_benign_code
- [ ] 5.10: test_empty_string
