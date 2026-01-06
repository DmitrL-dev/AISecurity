# Changelog

All notable changes to SENTINEL Shield.

## [Dragon v4.1] - 2026-01-06

### 🎉 100% Production Ready Milestone

**Build:**
- 0 errors, 0 warnings (all 125 source files)
- Makefile-based build system (replaced CMake)
- Multi-stage Docker build
- GitHub Actions CI/CD (6 jobs)

**Testing:**
- 103 tests total (94 CLI + 9 LLM integration)
- Valgrind integration (0 memory leaks)
- AddressSanitizer support (Linux)

**Features:**
- Brain FFI with HTTP and gRPC clients
- TLS/OpenSSL integration
- Kubernetes manifests (5 files)
- 21 custom protocols
- 119 CLI command handlers
- 6 specialized guards

### Added
- `test_llm_integration.c` - 9 LLM integration tests
- `http_client.c` - HTTP client for Brain FFI (430 LOC)
- `grpc_client.c` - gRPC client for Brain FFI (280 LOC)
- `k8s/` - Kubernetes deployment manifests
- `.github/workflows/shield-ci.yml` - CI/CD pipeline
- EXFILTRATION engine in stub detector

### Changed
- Build system: CMake → Makefile
- Library name: libsentinel-shield → libshield
- Stub detect: case-insensitive matching
- All void handler returns → shield_err_t

### Fixed
- All compiler warnings resolved
- String safety audit completed
- Return statement coverage 100%

---

## [1.2.0] - 2026-01-03

### Added
- SLLM Protocol implementation (711 LOC)
- Post-Quantum Cryptography stubs
- eBPF XDP support stubs
- 60+ Academy modules (EN/RU)

---

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
