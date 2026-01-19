# Changelog

All notable changes to RLM-Toolkit will be documented in this file.

## [1.2.1] - 2026-01-19

### Security
- **Removed XOR cipher dead code** - Eliminates AV heuristic triggers
- **Fail-closed encryption** - `create_encryption()` now requires AES
- **Rate limiting** - MCP reindex limited to 1 per 60s

### Changed
- Cleaned unused imports in `secure.py` and `crypto.py`

## [1.2.0] - 2026-01-19

### Added
- **VS Code Extension** with Activity Bar sidebar dashboard
- **Session Stats** - Real-time token savings tracking
- **9 MCP Tools** including `rlm_session_stats`
- **Call Graph Extraction** - 17,095 call relations
- **Cross-Reference Validation** - 2,359 symbols indexed
- **Antigravity IDE Installer** - one-click MCP integration

### Changed
- Security: AES-256-GCM fail-closed (removed XOR fallback)
- Storage: SQLite for persistent session stats
- Compression: 56x verified on SENTINEL codebase

### Fixed
- Extension timeout removed for large projects
- Session stats persistence across calls

## [1.1.0] - 2026-01-15

### Added
- H-MEM Secure Memory with encryption
- Cross-reference validation
- Staleness detection

## [1.0.0] - 2026-01-10

### Added
- Initial release
- C³ Crystal Compression
- AST-based extraction
- SQLite storage
- MCP Server (8 tools)
