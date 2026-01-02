# SENTINEL Academy — Module 15

## Capstone Project

_SSE Level | Время: 8+ часов_

---

## Введение

Это финальный модуль SSE.

Ты применишь всё, что изучил, создав production-ready расширение для Shield.

---

## 15.1 Project Requirements

### Scope

Выбери ОДИН из проектов:

| Project | Описание                       | Complexity |
| ------- | ------------------------------ | ---------- |
| A       | Custom Guard                   | Medium     |
| B       | Custom Protocol                | Hard       |
| C       | Plugin System Extension        | Medium     |
| D       | Performance Optimization       | Hard       |
| E       | Integration с внешней системой | Medium     |

### Deliverables

1. **Код** — Production quality
2. **Тесты** — Unit + Integration
3. **Документация** — README + API docs
4. **Presentation** — 10-15 минут

---

## 15.2 Project A: Custom Guard

### Требования

Создай Guard для специфичного use case:

**Примеры:**

- Code Injection Guard (детекция code в промптах)
- Language Guard (принудительный язык ответа)
- Context Limit Guard (ограничение контекста)
- Compliance Guard (GDPR, HIPAA)

### Критерии

- [ ] Implements guard_vtable_t
- [ ] Configurable через JSON
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

### Требования

Создай новый протокол для Shield:

**Примеры:**

- Audit Protocol (аудит событий)
- Notification Protocol (alerts)
- Sync Protocol (alternative to SSRP)
- External Integration Protocol

### Критерии

- [ ] Binary или text protocol
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

### Требования

Расширь plugin system:

**Примеры:**

- Hot reload support
- Plugin dependencies
- Plugin marketplace client
- Plugin sandboxing
- Plugin versioning и updates

### Критерии

- [ ] Backwards compatible
- [ ] Safe (no crashes)
- [ ] CLI integration
- [ ] Documentation

---

## 15.5 Project D: Performance

### Требования

Улучши производительность Shield:

**Примеры:**

- SIMD pattern matching
- Better memory allocator
- Connection pooling
- Async evaluation pipeline

### Критерии

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

### Требования

Интегрируй Shield с внешней системой:

**Примеры:**

- OpenTelemetry integration
- Kafka event streaming
- Elasticsearch logging
- Cloud provider (AWS/GCP/Azure)

### Критерии

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

Изучи существующие реализации:

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

После успешного завершения Capstone Project ты станешь **SENTINEL Shield Expert (SSE)**.

### Что это значит

- Deep understanding of Shield internals
- Ability to extend and customize
- Production deployment expertise
- Performance engineering skills

### Что дальше

- Contribute to Shield
- Create plugins для community
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
