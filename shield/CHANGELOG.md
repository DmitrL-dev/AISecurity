# Changelog

All notable changes to SENTINEL Shield.

## [1.0.0] - 2026-01-01

### Added

- Initial release
- Core security engine (Zone, Rule, Guard)
- 6 Security Guards: LLM, RAG, Agent, Tool, MCP, API
- 3 Protocols: STP, SBP, ZDP
- Cisco-style CLI with 15+ commands
- REST API with 5 endpoints
- Rate limiting (token bucket)
- Blocklist manager
- Session tracking
- Canary token detection
- Metrics (Prometheus export)
- Python bindings
- Go bindings
- Node.js bindings
- Docker support
- Cross-platform (Linux, macOS, Windows)

### Security

- Prompt injection detection
- Jailbreak pattern matching
- High-entropy payload detection
- SQL injection protection (RAG)
- Command injection protection (Tool)
- SSRF protection (API)
- Credential exposure detection
- Canary token tracking

### Documentation

- Quick Start guide
- Architecture overview
- CLI reference
- Protocol specifications
- REST API reference
