# Requirements: GoMCP OAuth Hardening

## Background
Current MCP implementations suffer from a "Shared Client ID" vulnerability where multiple MCP servers appear as the same OAuth client to identity providers. This allows malicious servers to reuse user consent granted to legitimate servers, leading to potential account takeovers.

## Success Metrics
- [ ] GoMCP server rejects connection attempts with duplicate or blacklisted Client IDs
- [ ] OAuth flow requires unique, verified Client ID per tenant/tool
- [ ] Hardcoded paths in `main.go` are replaced with configuration-driven discovery

## Functional Requirements
1. **WHEN** an MCP client connects, **THEN** the server MUST validate the `client_id` parameter in the initialization handshake.
2. **WHEN** a `client_id` is missing or belongs to a known shared/compromised list, **THEN** the connection MUST be rejected with a security error.
3. **WHEN** `gomcp-server` starts, **THEN** it MUST load configuration (worker path, project root) from flags or env vars, falling back to heuristics only if explicitly allowed.
4. **WHEN** a tool requires OAuth Scope, **THEN** the server MUST verify that the specific `client_id` has been granted that scope (Dynamic Client Registration emulation).

## Non-Functional Requirements
1. **Latency**: Validation must add < 5ms overhead to handshake.
2. **Compatibility**: Must maintain backward compatibility with MCP v1 clients that do not send `client_id` (configurable "strict mode").
3. **Concurrency**: Validation logic must be thread-safe.

## Constraints
- Must use standard Go library where possible.
- No breaking changes to the core MCP protocol implementation in `pkg/stdio`.
