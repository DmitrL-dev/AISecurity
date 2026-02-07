# Tasks: Strike Force Modernization
**Status:** DRAFT
**Feature:** `strike-force-modernization`

## Phase 1: Setup & Domain Definition (Foundation)
- [ ] Initialize `strike-force` module dependencies (`go mod init`) <!-- id: 1 -->
- [ ] Define **Domain Entities** in `internal/domain` (Interfaces for Brain, Evasion, Transport) <!-- id: 2 -->
- [ ] Create Configuration Structs & Loader (`internal/config`) <!-- id: 3 -->

## Phase 2: Adapters Implementation (The Logic)
- [ ] Port **Artemis Core** to `internal/adapters/artemis` (Implementing `domain.Brain`) <!-- id: 4 -->
  - [ ] State Machine (Probe -> Escalate -> Exhaust)
  - [ ] Thread-safe stats tracking
- [ ] Port **Evasion Engine** to `internal/adapters/evasion` (Implementing `domain.EvasionStrategy`) <!-- id: 5 -->
  - [ ] WAF Bypass Techniques (URL, Hex, Case, etc.)
  - [ ] Payload Mutator
- [ ] Implement **Transport Adapter** in `internal/adapters/transport` <!-- id: 6 -->
  - [ ] `http.Client` with evasion (TLS fingerprinting)
- [ ] Implement **Payload Loader** in `internal/adapters/loader` <!-- id: 13 -->
  - [ ] CDN Fetcher (`web-payloads.json`) with caching
  - [ ] Local File Fallback
- [ ] Implement **Modules** in `internal/adapters/modules` (Artemis-inspired) <!-- id: 14 -->
  - [ ] `takeover` (Subdomain Takeover signatures)
  - [ ] `misconfig` (Basic headers/conf checks)
- [ ] Implement **AI Modules** in `internal/adapters/ai` <!-- id: 15 -->
  - [ ] **MCP Poisoning:** Tool description injection logic <!-- id: 16 -->
  - [ ] **Prompt Worms:** Self-replicating payload generator <!-- id: 17 -->
  - [ ] **VLM Attacks:** Adversarial image header generator (`[IMAGE]`) <!-- id: 18 -->

## Phase 3: Application & Orchetration (The Runner)
- [ ] Implement **Job Generator** which reads Target + Brain decisions <!-- id: 7 -->
- [ ] Implement **Worker Pool** (10k+ goroutine support) in `internal/app/worker.go` <!-- id: 8 -->
- [ ] Implement **Result Aggregator** loop <!-- id: 9 -->

## Phase 4: Integration (The Product)
- [ ] Wire everything in `cmd/strike-force/main.go` <!-- id: 10 -->
- [ ] Implement CLI Flags (cobra/pflag) <!-- id: 11 -->
- [ ] Verify against local targets (Integration Test) <!-- id: 12 -->
