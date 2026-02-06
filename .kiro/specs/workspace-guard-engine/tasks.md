# Workspace Guard Engine — Tasks

## Phase 1: TDD Setup
- [ ] Create `workspace_guard.rs` with test stubs
- [ ] Write test_c2_trigger_detection
- [ ] Write test_callback_detection
- [ ] Write test_rce_detection
- [ ] Write test_benign_pass
- [ ] Write test_sensitive_file_detection

## Phase 2: Rust Implementation
- [ ] Define ThreatType enum
- [ ] Define WorkspaceThreat struct
- [ ] Implement C2 RegexSet patterns
- [ ] Implement Callback RegexSet patterns
- [ ] Implement RCE RegexSet patterns
- [ ] Implement scan_content() method
- [ ] Implement is_sensitive_file() method
- [ ] Implement PatternMatcher trait

## Phase 3: Integration
- [ ] Add `pub mod workspace_guard` to mod.rs
- [ ] Add WorkspaceGuard to EngineRegistry in bindings.rs
- [ ] Update list_pattern_engines()

## Phase 4: Verification
- [ ] Run `cargo test workspace_guard --release`
- [ ] Run `pip install -e .`
- [ ] Verify Python import
- [ ] Test via analyze_with('workspace_guard', ...)

## Acceptance Criteria
- [ ] 6+ Rust tests passing
- [ ] Python bindings working
- [ ] C2/Callback/RCE patterns detected
- [ ] Benign content passes
