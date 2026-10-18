# SENTINEL Academy — Module 15

> **Historical course material.** There is no certification programme. No certificates, badges, levels or instructor credentials are issued or recognised, and completing this material proves nothing to a third party. Use it for self-study only.

## Capstone Project

_SSE Level | Duration: 8+ hours_

---

## Introduction

This is the final SSE module.

You will apply everything you've learned by creating a production-ready extension for Shield.

---

## 15.1 Project Requirements

### Scope

Choose ONE of the projects:

| Project | Description                        | Complexity |
| ------- | ---------------------------------- | ---------- |
| A       | Custom Guard                       | Medium     |
| B       | Custom Protocol                    | Hard       |
| C       | Plugin System Extension            | Medium     |
| D       | Performance Optimization           | Hard       |
| E       | Integration with external system   | Medium     |

### Deliverables

1. **Code** — Production quality
2. **Tests** — Unit + Integration
3. **Documentation** — README + API docs
4. **Presentation** — 10-15 minutes

---

## 15.2 Project A: Custom Guard

### Requirements

Create a Guard for a specific use case:

**Examples:**

- Code Injection Guard (detect code in prompts)
- Language Guard (enforce response language)
- Context Limit Guard (limit context size)
- Compliance Guard (GDPR, HIPAA)

### Criteria

- [ ] Implements guard_vtable_t
- [ ] Configurable via JSON
- [ ] Thread-safe
- [ ] < 1ms evaluation latency
- [ ] Unit tests (80%+ coverage)
- [ ] Documentation

### Template

```
project-a/
├── include/
│   └── my_guard.h
├── src/
│   └── my_guard.c
├── tests/
│   └── test_my_guard.c
├── CMakeLists.txt
├── README.md
└── config.example.json
```

---

## 15.3 Project B: Custom Protocol

### Requirements

Create a new protocol for Shield:

**Examples:**

- Audit Protocol (event auditing)
- Notification Protocol (alerts)
- Sync Protocol (alternative to SSRP)
- External Integration Protocol

### Criteria

- [ ] Binary or text protocol
- [ ] Message framing
- [ ] Error handling
- [ ] Reconnection logic
- [ ] Performance: > 10K msg/sec
- [ ] Documentation

### Template

```
project-b/
├── include/
│   └── my_protocol.h
├── src/
│   ├── my_protocol.c
│   ├── message.c
│   └── connection.c
├── tests/
│   ├── test_serialization.c
│   └── test_connection.c
├── tools/
│   └── protocol_client.c
├── CMakeLists.txt
└── PROTOCOL.md
```

---

## 15.4 Project C: Plugin Extension

### Requirements

Extend the plugin system:

**Examples:**

- Hot reload support
- Plugin dependencies
- Plugin marketplace client
- Plugin sandboxing
- Plugin versioning and updates

### Criteria

- [ ] Backwards compatible
- [ ] Safe (no crashes)
- [ ] CLI integration
- [ ] Documentation

---

## 15.5 Project D: Performance

### Requirements

Improve Shield performance:

**Examples:**

- SIMD pattern matching
- Better memory allocator
- Connection pooling
- Async evaluation pipeline

### Criteria

- [ ] Measurable improvement
- [ ] Benchmarks before/after
- [ ] No regression in functionality
- [ ] Documentation

### Expected Improvements

| Metric      | Minimum Improvement |
| ----------- | ------------------- |
| Latency P99 | 20% reduction       |
| Throughput  | 20% increase        |
| Memory      | 10% reduction       |

---

## 15.6 Project E: Integration

### Requirements

Integrate Shield with an external system:

**Examples:**

- OpenTelemetry integration
- Kafka event streaming
- Elasticsearch logging
- Cloud provider (AWS/GCP/Azure)

### Criteria

- [ ] Production-ready
- [ ] Configurable
- [ ] Error handling
- [ ] Retry logic
- [ ] Documentation

---

## 15.7 Evaluation Criteria

### Code Quality (40%)

| Criteria           | Points |
| ------------------ | ------ |
| Clean architecture | 10     |
| Error handling     | 10     |
| Thread safety      | 10     |
| No memory leaks    | 10     |

### Testing (20%)

| Criteria                 | Points |
| ------------------------ | ------ |
| Unit test coverage > 80% | 10     |
| Integration tests        | 5      |
| Edge case handling       | 5      |

### Documentation (20%)

| Criteria             | Points |
| -------------------- | ------ |
| README with examples | 10     |
| API documentation    | 5      |
| Configuration guide  | 5      |

### Performance (10%)

| Criteria                   | Points |
| -------------------------- | ------ |
| Meets latency requirements | 5      |
| No performance regressions | 5      |

### Presentation (10%)

| Criteria          | Points |
| ----------------- | ------ |
| Clear explanation | 5      |
| Demo              | 5      |

### Total: 100 points

**Pass: 70+**
**Distinction: 90+**

---

## 15.8 Timeline

| Week | Milestone                 |
| ---- | ------------------------- |
| 1    | Project selection, design |
| 2    | Core implementation       |
| 3    | Testing, documentation    |
| 4    | Polish, presentation prep |

---

## 15.9 Submission

### Required Files

```
submission/
├── src/                    # Source code
├── include/                # Headers
├── tests/                  # Tests
├── docs/
│   ├── README.md          # Overview
│   ├── API.md             # API documentation
│   └── DESIGN.md          # Design decisions
├── CMakeLists.txt
└── PRESENTATION.pdf       # Slides
```

### Submission Checklist

- [ ] Code compiles without warnings
- [ ] All tests pass
- [ ] No memory leaks (valgrind clean)
- [ ] Documentation complete
- [ ] Presentation prepared

---

## 15.10 Resources

### Shield Source Code

Study existing implementations:

- `src/guards/` — Guard implementations
- `src/protocols/` — Protocol implementations
- `src/core/` — Core utilities

### Reference Materials

- Module 11: Internals
- Module 12: Custom Guards
- Module 13: Plugin System
- Module 14: Performance

### Support

- GitHub Discussions
- Office hours (if available)
- Peer review

---

## 🎉 Congratulations!

Upon successful completion of the Capstone Project, you will become a **SENTINEL Shield Expert (SSE)**.

### What This Means

- Deep understanding of Shield internals
- Ability to extend and customize
- Production deployment expertise
- Performance engineering skills

### What's Next

- Contribute to Shield
- Create plugins for the community
- Help others learn
- Advance the field of AI Security

---

## Certificate

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║                    SENTINEL ACADEMY                          ║
║                                                              ║
║                        certifies                             ║
║                                                              ║
║                    [YOUR NAME]                               ║
║                                                              ║
║            as a SENTINEL Shield Expert (SSE)                 ║
║                                                              ║
║         Having completed all modules and the                 ║
║              Capstone Project with distinction               ║
║                                                              ║
║         Date: ____________    Score: _____/100              ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
```

---

_"The journey of a thousand miles begins with a single step. You've taken all the steps. Now lead others."_

_— SENTINEL Academy_
