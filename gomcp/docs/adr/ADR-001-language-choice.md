# ADR-001: Language Choice for GoMCP Core

## Status
**Accepted**

## Context
MCP (Model Context Protocol) has fundamental issues with blocking I/O and Python's GIL causing server deadlocks. We need a language that:
- Handles concurrent I/O without blocking
- Compiles to single binary (easy distribution)
- Has ecosystem for network services
- Is accessible to contributors

## Options Considered

### Option 1: Python + uvloop
- ✅ Familiar to AI/ML community
- ✅ Huge ecosystem
- ❌ GIL limits true parallelism
- ❌ Blocking I/O in async context causes deadlocks
- ❌ Requires venv/dependencies

### Option 2: Rust
- ✅ Memory-safe, zero-cost abstractions
- ✅ Excellent async (tokio)
- ✅ Single binary
- ❌ Steep learning curve
- ❌ Smaller contributor pool

### Option 3: Go
- ✅ Goroutines solve blocking I/O naturally
- ✅ Single binary, fast compilation
- ✅ Large ecosystem for servers
- ✅ Accessible learning curve
- ❌ Slightly slower than Rust
- ❌ Less type expressiveness

### Option 4: TypeScript/Bun
- ✅ Same language as VS Code extensions
- ✅ Huge ecosystem
- ❌ Requires runtime
- ❌ Less suitable for system programming

## Decision
We chose **Go** because:
1. Goroutines naturally handle the blocking I/O problem that broke MCP
2. Single binary simplifies distribution
3. Accessible to broader contributor base
4. Strong ecosystem for network services (gRPC native)

## Consequences

### Positive
- No GIL deadlocks possible
- Easy cross-platform compilation
- Fast startup time
- Native gRPC support

### Negative
- Python tools need adapter layer (IPC overhead)
- Less library availability for ML/AI tasks
- Contributors need to learn Go if unfamiliar

## Trade-off Matrix

| Criterion | Weight | Go | Rust | Python | TS |
|-----------|--------|----|----|--------|-----|
| Concurrency | 0.3 | 9 | 10 | 5 | 7 |
| Simplicity | 0.25 | 9 | 5 | 9 | 8 |
| Distribution | 0.2 | 10 | 10 | 4 | 6 |
| Ecosystem | 0.15 | 8 | 7 | 10 | 9 |
| Safety | 0.1 | 7 | 10 | 5 | 6 |
| **Total** | | **8.55** | 8.05 | 6.35 | 7.25 |
