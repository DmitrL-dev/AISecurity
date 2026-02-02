# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-02-01

### Added

#### Core
- **Supervisor**: Worker management and tool call orchestration
- **Security**: Input validation, audit logging, rate limiting
- **Multi-tenancy**: Namespace isolation with quota management

#### Adapters
- **Stdio**: MCP v1 compatible JSON-RPC 2.0 adapter
- **gRPC**: Native GoMCP protocol server
- **HTTP Mode**: REST API for Docker/Kubernetes deployments

#### Enterprise Features
- **Batching API**: Parallel tool execution with concurrency control
- **Hot-reload**: Zero-downtime tool configuration updates
- **Health endpoints**: Kubernetes-ready liveness/readiness probes

#### SDKs
- **TypeScript SDK**: Type-safe client library with batch support

#### Infrastructure
- **CI/CD**: GitHub Actions workflows for test, lint, build, release
- **Docker**: Multi-stage builds, docker-compose with monitoring

### Security
- Input validation with dangerous pattern detection
- Rate limiting per client
- Structured audit logging
- Tenant-based tool access control

### Performance
- 100K+ tool calls/sec with supervisor
- 500K+ validations/sec
- Lock-free quota checks

## [0.1.0] - 2026-01-15

### Added
- Initial prototype
- Basic supervisor implementation
- MCP v1 adapter skeleton
