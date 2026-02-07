# Requirements: Strike Force Modernization (Hardcore Go)
**Status:** DRAFT
**Feature:** `strike-force-modernization`

## 1. Executive Summary
Complete rewrite of the legacy Python `sentinel-strike` tool into a single, static Go binary (`strike-force`). This addresses critical dependency supply chain risks and performance limitations (GIL). The new engine must maintain 100% adherence to existing "Artemis" adaptive logic and WAF evasion capabilities while delivering >10k concurrent/second performance.

### 1.5 Unique Value Proposition (UVP)
Unlike 2026 competitors (Agentic Research Frameworks like RedTeamLLM, or Commercial MCP Scanners like Lasso):
1.  **Single Binary Primitives:** We provide the *building blocks* of Agentic attacks (Worms, MCP Poisoning) in a single high-performance binary. We are the "Metasploit for Agents", not the Agent itself.
2.  **Hybrid Offensive:** Changes payload encoding (WAF Bypass) *before* sending AI prompts. Garak/PyRIT send plain prompts that Cloudflare blocks.
3.  **High Velocity:** 10k RPS worker pool vs 100 RPS Python synchronous loops.
4.  **"Artemis" FSM:** Stateful logic that adapts to WAF blocking behavior, not just random fuzzing.

## 2. Functional Requirements



### 2.1 Core Engine
- **[REQ-CORE-001] Single Binary:** The application MUST compile to a single static binary with NO runtime dependencies (Python, Lua, etc.).
- **[REQ-CORE-002] Concurrency:** MUST support >10,000 concurrent workers via a non-blocking worker pool pattern.
- **[REQ-CORE-003] Configuration:** MUST load attack profiles from a generic YAML configuration file (`strike_config.yaml`) and support Environment Variable overrides.
- **[REQ-CORE-004] Dynamic Payloads:** MUST load attack payloads from external JSON sources (CDN with local file fallback) to support auto-updates without recompilation. Schema matches `web-payloads.json` (PayloadsAllTheThings aggregated).

### 2.2 Artemis Intelligence (The "Brain")
- **[REQ-ART-001] State Machine:** MUST implement the Artemis "Exhaustion Principle" as a formal Finite State Machine (FSM).
- **[REQ-ART-002] Adaptive Context:** MUST track the last N responses (sliding window) to trigger:
  - **Technique Rotation:** Switch attack vector after X blocks.
  - **Auto-Correction:** Split complex payloads upon systemic failure.
- **[REQ-ART-003] Thread Safety:** All shared state (tested vectors, success maps) MUST be thread-safe (Mutex/RWMutex) without lock contention bottlenecks.

### 2.3 Evasion Capabilities
- **[REQ-EVA-001] WAF Bypass:** MUST port all 24 Python evasion techniques (Unicode, double-verify, etc.) to native Go string manipulation.
- **[REQ-EVA-002] Mutation Engine:** MUST implement deterministic payload mutation (Fibonacci, Golden Ratio injection) without external math libraries.
- **[REQ-EVA-003] TLS Tuning:** MUST support low-level TLS fingerprint manipulation (JA3 evasion) via `crypto/tls` config.

## 3. Non-Functional Requirements
- **[NFR-PERF-001]** Zero-allocation networking loop for the hot path.
- **[NFR-SEC-001]** No external dependencies for core logic (standard library preferred).
- **[NFR-OBS-001]** Structured JSON logging for all attack events (compatible with Sentinel Shield).

## 4. Constraints
- **Language:** Go 1.24+
- **Architecture:** Clean Architecture (Domains -> UseCases -> Adapters).
- **Forbidden:** cgo, Python embedded interpreters.
