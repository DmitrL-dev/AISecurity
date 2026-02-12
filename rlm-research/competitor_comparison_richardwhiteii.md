# RLM Implementation Comparison

## richardwhiteii/rlm vs RLM-Toolkit

| Aspect | richardwhiteii/rlm | RLM-Toolkit |
|--------|-------------------|-------------|
| **Type** | MCP Server | Python Library (pip) |
| **Target** | Claude Code only | Any LLM provider |
| **Paper** | arxiv:2512.24601v1 | Same paper |
| **Stars** | New (few) | 200+ downloads |

### Features Comparison

| Feature | richardwhiteii | RLM-Toolkit |
|---------|---------------|-------------|
| Basic RLM Loop | ✅ | ✅ |
| InfiniRetri | ❌ | ✅ |
| H-MEM (Hierarchical Memory) | ❌ | ✅ |
| R-Zero (Self-Evolving) | ❌ | ✅ |
| Security Sandbox | Basic subprocess | CIRCLE-compliant |
| Blocked modules | ? | 28+ |
| Multiple providers | Haiku + Ollama | OpenAI, Anthropic, Google, Ollama |
| Install | Manual MCP config | `pip install rlm-toolkit` |

### Architecture

**richardwhiteii/rlm:**
```
Claude Code → MCP Server → Sub-LLM
```

**RLM-Toolkit:**
```
Any App → RLM Library → Any Provider
         ├── InfiniRetri (attention-based retrieval)
         ├── H-MEM (cognitive memory)
         ├── R-Zero (self-evolution)
         └── Security Suite (CIRCLE)
```

### Verdict

- **richardwhiteii**: Good for Claude Code users who want quick integration
- **RLM-Toolkit**: Full-featured library with security, memory, retrieval

---

## Reddit Comment Draft

Great implementation! Same paper (arxiv:2512.24601v1), different approach.

If you want more features:
- **InfiniRetri** — attention-based retrieval (100% NIAH @ 1M tokens)
- **H-MEM** — cognitive hierarchical memory
- **Security sandbox** — CIRCLE-compliant (28 blocked modules)
- **Multiple providers** — OpenAI, Anthropic, Google, Ollama

Search for: **"RLM-Toolkit infinite context"** or **"rlm-toolkit pip"**

Also works as Python library, not just MCP:
```python
pip install rlm-toolkit
```

Keep up the good work! 🚀
