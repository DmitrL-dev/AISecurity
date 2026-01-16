# Changelog

All notable changes to RLM-Toolkit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-01-16

### Added

#### Core Engine
- `RLM` class with recursive REPL loop
- `RLMConfig` with full configuration options
- `RLMResult` with trace_id and cost tracking
- Factory methods: `from_ollama`, `from_openai`, `from_anthropic`, `from_google`
- `LazyContext` for memory-efficient large document handling
- Streaming support with `RLMStreamEvent`
- Error recovery with `RecoveryConfig`

#### Security
- `SecureREPL` with CIRCLE-compliant sandboxing
- AST-based import blocking
- `VirtualFS` with quota enforcement
- `PlatformGuards` for resource limiting
- `IndirectAttackDetector` for obfuscation detection

#### Providers
- `LLMProvider` abstract base class
- `OllamaProvider` for local models
- `OpenAIProvider` for GPT models
- `AnthropicProvider` for Claude models
- `GeminiProvider` for Google models
- `RetryConfig` with exponential backoff
- `RateLimiter` with token bucket algorithm

#### Observability
- `Tracer` with OpenTelemetry-compatible spans
- `CostTracker` with budget enforcement
- `ConsoleExporter`, `LangfuseExporter`, `LangSmithExporter`

#### Memory
- `BufferMemory` for simple FIFO storage
- `EpisodicMemory` with similarity and contiguity retrieval

#### Evaluation
- `Evaluator` framework with `Benchmark` interface
- `OOLONGBenchmark` for long-context evaluation
- `CIRCLEBenchmark` for security testing
- Metrics: `ExactMatch`, `SemanticSimilarity`, `NumericMatch`

#### Agentic
- `RewardTracker` with reward signals
- `ReasoningChain` for structured reasoning
- `StructuredReasoner` for chain-of-thought

#### CLI
- `rlm run` for single queries
- `rlm repl` for interactive mode
- `rlm eval` for benchmarking
- `rlm trace` for observability

#### Testing
- `MockProvider` and `SequenceProvider`
- Test fixtures and sample contexts
- 45+ unit tests

#### Documentation
- README with quick start and examples
- Getting started guide
- Example scripts

### Security
- Blocked 50+ dangerous imports
- AST analysis for nested attacks
- Virtual filesystem isolation
- Platform-specific resource guards

[Unreleased]: https://github.com/sentinel-community/rlm-toolkit/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/sentinel-community/rlm-toolkit/releases/tag/v0.1.0
