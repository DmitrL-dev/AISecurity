# ADR-002: Protocol Design and Backward Compatibility

## Status
**Accepted**

## Context
Existing MCP ecosystem has significant adoption:
- Claude Desktop
- VS Code extensions
- Cursor, Zed, Continue.dev

We need to either:
- Replace MCP entirely (breaking change)
- Extend MCP (compatibility)
- Create parallel protocol with adapters

## Options Considered

### Option 1: Breaking Replacement
- ✅ Clean slate, no legacy constraints
- ❌ Zero adoption on day 1
- ❌ Requires all clients to update

### Option 2: MCP v2 (Extend)
- ✅ Some backward compatibility
- ❌ Still requires client updates
- ❌ Constrained by MCP design

### Option 3: Hybrid (Native + Adapter)
- ✅ Day 1 compatibility via adapter
- ✅ New features for native clients
- ✅ Gradual migration path
- ❌ Two protocols to maintain
- ❌ Adapter adds latency

## Decision
We chose **Hybrid Architecture**:

```
GoMCP Server
├── MCP v1 Adapter (stdio/JSON-RPC)  ← backward compat
├── GoMCP Native (gRPC/Protobuf)     ← new clients
└── HTTP/SSE Mode                     ← web clients
```

## Consequences

### Positive
- Drop-in replacement from day 1
- Native protocol for performance-critical clients
- Gradual ecosystem migration

### Negative
- Must maintain adapter indefinitely
- Some feature parity challenges
- Testing complexity (3 modes)

## Implementation Notes
- Adapter: `pkg/adapter/mcpv1/`
- Native: `proto/gomcp.proto`
- HTTP: Future phase
