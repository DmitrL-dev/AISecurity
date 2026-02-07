# Tasks: GoMCP OAuth Hardening

## Phase 1: Preparation & TDD
- [ ] **Reproduce Vulnerability** <!-- id: 1 -->
  - Create `TestInitialize_NoClientInfo` in `pkg/stdio/adapter_test.go`.
  - Assert that it currently succeeds (returns server info).
  - _Requirements: 1, 2_

## Phase 2: Implementation
- [ ] **Define Data Models** <!-- id: 2 -->
  - Add `ClientInfo` and `InitializeParams` structs to `pkg/stdio/stdio.go`.
  - _Requirements: 1_
- [ ] **Implement Validation Logic** <!-- id: 3 -->
  - Update `handleInitialize` in `pkg/stdio/adapter.go`.
  - Log warning if `clientInfo` is missing.
  - Return error if `clientInfo` is explicitly invalid (empty name).
  - _Requirements: 2, NF-1, NF-2_

## Phase 3: Refactoring (The Gemini Touch)
- [ ] **Clean Main.go** <!-- id: 4 -->
  - Remove `findWorkerPath` hardcoding.
  - Enforce `worker` flag or `RLM_WORKER_PATH` env var.
  - _Requirements: 3_

## Phase 4: Verification
- [ ] **Run All Tests** <!-- id: 5 -->
  - `go test ./...`
  - _Requirements: All_
