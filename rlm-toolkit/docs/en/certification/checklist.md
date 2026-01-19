# RLM-Toolkit Certification Checklist

![Version](https://img.shields.io/badge/version-1.2.1-blue)

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

### Basic Usage
- [ ] Create RLM instance with OpenAI/Ollama
- [ ] Use HierarchicalMemory for persistence
- [ ] Build simple RAG pipeline

---

## Level 2: Practitioner

### MCP Integration
- [ ] Configure MCP Server for IDE
- [ ] Use all 10 MCP tools
- [ ] Install and configure VS Code Extension
- [ ] Track token savings via session stats

### C³ Crystal
- [ ] Explain Primitive types (FUNCTION, CLASS, etc.)
- [ ] Use HPEExtractor for code analysis
- [ ] Navigate CrystalIndexer search results
- [ ] Understand compression metrics (56x)

### Storage & Freshness
- [ ] Configure TTL for crystals
- [ ] Use delta updates vs full reindex
- [ ] Validate index health via rlm_validate

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

### Advanced Features
- [ ] Use InfiniRetri for 1M+ token docs
- [ ] Configure Self-Evolving LLMs
- [ ] Set up Multi-Agent P2P communication
- [ ] Implement DSPy-style optimization

---

## Practical Assessment

### Task 1: Setup (10 min)
1. Install RLM-Toolkit with MCP
2. Configure for VS Code
3. Index a sample project

### Task 2: Analysis (15 min)
1. Use rlm_analyze for security_audit
2. Identify potential issues
3. Document findings

### Task 3: Integration (20 min)
1. Build RAG pipeline with H-MEM
2. Track and report token savings
3. Validate index freshness

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
- [Concept: Crystal](../concepts/crystal.md)
- [Concept: Security](../concepts/security.md)
