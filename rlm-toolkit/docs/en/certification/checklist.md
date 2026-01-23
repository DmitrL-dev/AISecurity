# RLM-Toolkit Certification Checklist

![Version](https://img.shields.io/badge/version-2.1.0-blue)

> Skills verification for RLM-Toolkit practitioners

## Level 1: Fundamentals

### Installation & Setup
- [ ] Install `rlm-toolkit` via pip
- [ ] Configure API key for LLM provider
- [ ] Run first RLM query successfully

### Core Concepts
- [ ] Explain what RLM (Recursive Language Model) is
- [ ] Understand context window vs RLM infinite context
- [ ] Describe H-MEM 4-level architecture
- [ ] Explain Memory Bridge purpose (cross-session persistence)

### Basic Usage
- [ ] Create RLM instance with OpenAI/Ollama
- [ ] Use HierarchicalMemory for persistence
- [ ] Build simple RAG pipeline

---

## Level 2: Practitioner

### MCP Integration
- [ ] Configure MCP Server for IDE
- [ ] Use all 18 MCP tools (v2.1)
- [ ] Install and configure VS Code Extension v2.1.0
- [ ] Track token savings via session stats

### Memory Bridge v2.1
- [ ] Use `rlm_enterprise_context` for zero-config queries
- [ ] Explain L0-L3 Hierarchical Memory levels
- [ ] Run `rlm_discover_project` for cold start
- [ ] Install Git hooks for auto-extraction
- [ ] Understand 56x token compression mechanism

### C³ Crystal
- [ ] Explain Primitive types (FUNCTION, CLASS, etc.)
- [ ] Use HPEExtractor for code analysis
- [ ] Navigate CrystalIndexer search results
- [ ] Understand compression metrics

### Storage & Freshness
- [ ] Configure TTL for facts
- [ ] Use delta updates vs full reindex
- [ ] Validate index health via `rlm_health_check`
- [ ] Refresh stale facts via `rlm_refresh_fact`

---

## Level 3: Expert

### Security
- [ ] Configure SecureHierarchicalMemory
- [ ] Explain Trust Zones concept
- [ ] Set up AES-256-GCM encryption
- [ ] Implement rate limiting best practices

### Performance
- [ ] Optimize .rlmignore for large projects
- [ ] Tune parallel_workers for indexing
- [ ] Analyze cross-reference resolution rate
- [ ] Achieve sub-second cold start (< 0.1s for 100K LOC)

### Advanced Features
- [ ] Use InfiniRetri for 1M+ token docs
- [ ] Configure Self-Evolving LLMs
- [ ] Set up Multi-Agent P2P communication
- [ ] Implement DSPy-style optimization
- [ ] Use Causal Reasoning (`rlm_record_causal_decision`)

### Memory Bridge Enterprise
- [ ] Configure semantic routing with embeddings
- [ ] Use `rlm_get_causal_chain` for decision tracing
- [ ] Set up TTL policies for fact expiration
- [ ] Build custom fact extraction pipelines

---

## Practical Assessment

### Task 1: Setup (10 min)
1. Install RLM-Toolkit with MCP
2. Configure for VS Code with Extension v2.1.0
3. Run `rlm_discover_project` on sample project

### Task 2: Memory Bridge (15 min)
1. Add hierarchical facts at L1 and L2 levels
2. Use `rlm_enterprise_context` with semantic routing
3. Install Git hook and verify extraction on commit

### Task 3: Analysis (15 min)
1. Use `rlm_analyze` for `security_audit` goal
2. Check `rlm_health_check` status
3. Document findings with decisions via `rlm_record_causal_decision`

### Task 4: Integration (20 min)
1. Build RAG pipeline with Memory Bridge persistence
2. Track and report token savings (target: 50x+)
3. Validate index freshness via dashboard

---

## Passing Criteria

| Level | Required Score |
|-------|----------------|
| L1: Fundamentals | 80% |
| L2: Practitioner | 75% |
| L3: Expert | 70% |

---

## Resources

- [Quickstart](../quickstart.md)
- [Tutorial: MCP Server](../tutorials/10-mcp-server.md)
- [**Memory Bridge v2.1**](../../memory-bridge.md) — Enterprise memory
- [VS Code Extension](../../../rlm-vscode-extension/README.md)
- [Concept: Crystal](../concepts/crystal.md)
- [Concept: Security](../concepts/security.md)
- [API Reference](../../api_reference.md) — 18 MCP tools
