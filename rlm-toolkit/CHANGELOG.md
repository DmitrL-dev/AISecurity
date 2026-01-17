# Changelog

All notable changes to RLM-Toolkit will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Benchmarks page in documentation
- Video tutorials
- Case studies

---

## [1.0.0] - 2026-01-17

### 🚀 First Production Release

Major expansion with complete documentation, 900+ tests, and enterprise features.

### Added

#### RLM Academy Documentation
- **9 Tutorials** - From first app to multi-agent systems
- **8 Concept Pages** - Deep architecture documentation
- **6 How-to Guides** - Practical implementation guides
- **170+ Examples** - Basic and advanced production patterns
- **19 Enterprise Examples** - Research agents, multi-modal RAG, security patterns
- **Full API Reference** - All modules documented
- **50+ Integration Docs** - Provider-specific documentation
- **Interactive Glossary** - 20+ terms with hover tooltips
- **Troubleshooting Guide** - Common issues and solutions
- **Why RLM Page** - Honest comparison with LangChain
- **Migration Guide** - LangChain → RLM migration path
- **Bilingual** - Full EN/RU parity (~42,000 lines)

#### Extended Providers
- Groq, Together AI, Mistral, Anyscale providers
- 50+ provider integrations total

#### Extended Loaders
- 135+ document loaders
- Advanced PDF: PyMuPDF, Unstructured, Document Intelligence
- Web scraping, API loaders, database loaders

#### Extended Vector Stores
- 41 vector store integrations
- Chroma, Pinecone, Weaviate, FAISS, Milvus, Qdrant, PGVector

#### Extended Embeddings
- 34 embedding model integrations
- Jina AI, BGE, Instructor, Multilingual E5

#### Multi-Agent Systems
- Meta Matrix orchestration framework
- Collaborative, debate, and hierarchical modes

#### Advanced Memory
- HierarchicalMemory (H-MEM) - Working, Episodic, Semantic
- SecureMemory with encryption

#### Self-Evolving LLMs
- R-Zero Challenger-Solver pattern
- Automatic output improvement

#### DSPy-Style Optimization
- BootstrapFewShot optimizer
- Signature-based modules

### Changed
- Test suite expanded to 927 tests (99.6% pass rate)
- Documentation restructured to Diátaxis framework

---

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
- **InfiniRetri** - Unlimited context through dynamic retrieval

#### Security
- `SecureREPL` with CIRCLE-compliant sandboxing
- AST-based import blocking
- `VirtualFS` with quota enforcement
- `PlatformGuards` for resource limiting
- `IndirectAttackDetector` for obfuscation detection
- Prompt injection detection (multi-layer)
- Trust Zones for multi-tenant isolation
- Audit trail with hash chain

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

#### Agents
- `ReActAgent` framework
- Tool decorator for easy tool creation
- 35+ built-in tools

#### Evaluation
- `Evaluator` framework with `Benchmark` interface
- `OOLONGBenchmark` for long-context evaluation
- `CIRCLEBenchmark` for security testing
- Metrics: `ExactMatch`, `SemanticSimilarity`, `NumericMatch`

#### CLI
- `rlm run` for single queries
- `rlm repl` for interactive mode
- `rlm eval` for benchmarking
- `rlm trace` for observability

---

## Version Policy

### Semantic Versioning
- **MAJOR** (1.x.x): Breaking API changes
- **MINOR** (x.1.x): New features, backward compatible
- **PATCH** (x.x.1): Bug fixes, backward compatible

### Deprecation Policy
- Deprecated features marked with warnings for 2+ minor versions
- Breaking changes announced 1+ minor version ahead

### Support
- Major versions receive security updates for 12 months

---

## Links

- [Documentation](https://rlm-toolkit.readthedocs.io)
- [GitHub](https://github.com/sentinel-community/rlm-toolkit)
- [PyPI](https://pypi.org/project/rlm-toolkit)

[Unreleased]: https://github.com/sentinel-community/rlm-toolkit/compare/v1.0.0...HEAD
[1.0.0]: https://github.com/sentinel-community/rlm-toolkit/releases/tag/v1.0.0
[0.1.0]: https://github.com/sentinel-community/rlm-toolkit/releases/tag/v0.1.0
