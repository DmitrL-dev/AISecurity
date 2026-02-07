# Design: Strike Force (Go)
**Status:** DRAFT
**Feature:** `strike-force-modernization`

## 1. Architecture Overview
We follow **Clean Architecture** principles. The application is divided into:
- **Domain (Core)**: Entities (`Target`, `Attack`) and Interfaces (`Brain`, `Evasion`).
- **Use Cases (App)**: The `Orchestrator` logic and `Worker` pools.
- **Adapters (Infra)**: HTTP/gRPC Transports, CLI methods, Config loaders.

### 1.1 Package Structure
```text
strike-force/
├── cmd/strike-force/           # Main
├── internal/
│   ├── domain/                 # Pure Interfaces & Types
│   │   ├── artemis.go         # Interface for the Brain
│   │   ├── evasion.go         # Interface for WAF/Mutator
│   │   └── models.go          # Attack/Result structs
│   ├── app/                    # Application Business Logic
│   │   ├── orchestrator.go    # Manages the Campaign
│   │   └── worker.go          # The "Muscle" (10k+ routines)
│   ├── adapters/               # Infrastructure implementations
│   │   ├── artemis/           # FSM Implementation
│   │   ├── evasion/           # Native Go string manipulation
│   │   ├── transport/         # net/http with evasion
│   │   ├── loader/            # CDN/File Payload Loader
│   │   └── modules/           # Attack Modules (Inspired by CERT-Polska)
│   │       ├── takeover/      # Subdomain Takeover
│   │       └── misconfig/     # Misconfiguration Scanner
│   │   ├── ai/                # AI-Specific Attack Modules
│   │   │   ├── mcp/           # MCP Tool Poisoning
│   │   │   ├── vlm/           # Visual Prompt Injection
│   │   │   └── worms/         # Prompt Infection/Worms
│   └── config/                 # YAML Configuration
└── pkg/                        # Public libraries (if shared)
```

## 2. Core Interfaces (Domain)

### 2.1 The Brain (Artemis)
```go
package domain

type AttackType string

type Brain interface {
    // Decision Loop
    Decide(history []Result) Action
    
    // Feedback
    RecordResult(result Result)
    
    // State Query
    IsExhausted() bool
    GetStats() Stats
}

type Action struct {
    Type    ActionType // ATTACK, ROTATE, SLEEP, STOP
    Payload string
    Context map[string]string
}

type PayloadLoader interface {
    Load(source string) (map[string][]string, error)
}
```

### 2.2 Evasion
```go
package domain

type EvasionStrategy interface {
    // Core Bypass
    Mutate(payload string, aggression Level) string
    
    // WAF Specific
    GenerateVariants(payload string) []string
}

// Inspired by CERT-Polska/Artemis
type Module interface {
    Name() string
    Execute(target string) ([]Result, error)
}
```

## 3. Concurrency Model
We use a **pipeline pattern** to minimize lock contention:

1.  **Generator:** `Orchestrator` pushes `Jobs` into a buffered channel `chan domain.Job`.
2.  **Workers:** `N` goroutines read from `jobs`.
    *   Each worker holds a thread-local copy of `transport.Client` (to reuse TCP connections).
    *   Worker applies `Evasion.Mutate(job.Payload)`.
    *   Worker executes HTTP request.
3.  **Aggregator:** Workers push `Result` to `chan domain.Result`.
    *   Single `Brain` goroutine reads results and updates the State Machine (eliminating mutex requirement on hot path).

## 4. Configuration Schema (`strike_config.yaml`)

```yaml
campaign:
  target: "https://example.com"
  threads: 50
  timeout: "5s"

artemis:
  mode: "aggressive" # stealth, normal, aggressive
  exhaustion: true   # Keep going until 100% vector coverage

evasion:
  waf_type: "auto"   # aws, cloudflare, auto
  aggression: 5      # 1-10
  techniques:
    - "url_double"
    - "case_random"
```

## 5. Migration Strategy
1.  **Phase 1 (Skeleton):** Setup Clean Arch structure. (Done)
2.  **Phase 2 (Domain):** Define strict interfaces in `internal/domain`.
3.  **Phase 3 (Adapters):** Port Python logic into `internal/adapters/artemis` and `internal/adapters/evasion`.
4.  **Phase 4 (App):** Wire up the Orchestrator with the Concurrency Pipeline.
