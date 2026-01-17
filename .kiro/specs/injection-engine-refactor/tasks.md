# Injection Engine Refactor — Tasks

## Phase 1: Extract Models and Cache

- [x] **Task 1.1**: Создать `src/brain/engines/injection/__init__.py`

- [x] **Task 1.2**: Создать `injection/models.py`
  - Verdict enum
  - InjectionResult dataclass (с factory methods)

- [x] **Task 1.3**: Создать `injection/cache.py`
  - CacheLayer class (с stats())

---

## Phase 2: Extract Regex Patterns

- [x] **Task 2.1**: Создать `injection/patterns.py`
  - CLASSIC_PATTERNS (8 patterns)
  - NOVEL_2025_PATTERNS (6 patterns)
  - ENCODING_PATTERNS (5 patterns)
  - DANGEROUS_KEYWORDS dict

- [x] **Task 2.2**: Создать `injection/regex_layer.py`
  - RegexLayer class
  - scan(), quick_scan() methods

---

## Phase 3: Extract Semantic and Structural

- [x] **Task 3.1**: Создать `injection/semantic_layer.py`
  - SemanticLayer class
  - Embedding similarity detection
  - Default jailbreak patterns

- [x] **Task 3.2**: Создать `injection/structural_layer.py`
  - StructuralLayer class
  - Entropy analysis
  - Instruction pattern detection

---

## Phase 4: Main Engine

- [ ] **Task 4.1**: Создать `injection/engine.py` (optional)
  - InjectionEngine class (orchestration)

---

## Acceptance Criteria

| Критерий | Метрика | Статус |
|----------|---------|--------|
| injection/ | 7 files, ~900 LOC | ✅ |
| Each layer file | < 20KB | ✅ |
| All imports working | 100% | ✅ |

---

**Created:** 2026-01-09
**Completed:** 2026-01-09
