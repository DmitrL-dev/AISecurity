# IMMUNE Pattern Safety — Specification

> **Version:** 1.0  
> **Author:** SENTINEL Team  
> **Date:** 2026-01-08  
> **Status:** Draft

---

## 1. Overview

### 1.1 Purpose

Protect IMMUNE kernel module from ReDoS (Regular Expression Denial of Service) attacks via malicious patterns. Ensure pattern matching completes in bounded time.

### 1.2 Problem Statement

From architecture critique (S4):
- Malicious patterns with nested quantifiers can block Kmod
- No timeout mechanism for pattern matching
- Patterns can be injected via Herd network

### 1.3 Scope

| In Scope | Out of Scope |
|----------|--------------|
| Pattern validation before loading | Full RE2 library port |
| Complexity scoring | PCRE2 support |
| Kernel timeout mechanism | JIT compilation |
| Safe regex subset definition | Lookahead/backreferences |

### 1.4 References

- [RE2 Design](https://github.com/google/re2/wiki/WhyRE2)
- [ReDoS Attacks](https://owasp.org/www-community/attacks/Regular_expression_Denial_of_Service_-_ReDoS)
- IMMUNE Architecture Critique (S4)

---

## 2. Requirements

### 2.1 Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | Validate patterns before loading into Kmod | P0 |
| FR-02 | Reject patterns with nested quantifiers | P0 |
| FR-03 | Calculate complexity score for each pattern | P0 |
| FR-04 | Enforce maximum complexity threshold | P0 |
| FR-05 | Timeout pattern matching in kernel | P0 |
| FR-06 | Log rejected patterns with reason | P1 |
| FR-07 | Whitelist known-safe patterns | P2 |

### 2.2 Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-01 | Validation latency | < 1ms per pattern |
| NFR-02 | Memory per pattern | < 4KB |
| NFR-03 | Kernel timeout | 10ms default |
| NFR-04 | False positive rate | < 1% on legit patterns |

### 2.3 Security Requirements

| ID | Requirement |
|----|-------------|
| SR-01 | Never load unvalidated pattern into Kmod |
| SR-02 | Kernel must remain responsive during matching |
| SR-03 | Failed validation = pattern rejection (fail-close) |

---

## 3. Architecture

### 3.1 Pattern Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    PATTERN LOADING FLOW                      │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  New Pattern ───► [VALIDATOR] ───► [COMPILER] ───► Kmod    │
│       │                │                                     │
│       │                ▼                                     │
│       │         ┌──────────────┐                            │
│       │         │ REJECT       │                            │
│       │         │ + Log reason │                            │
│       │         └──────────────┘                            │
│       │                                                      │
│       ▼                                                      │
│  Validation Steps:                                           │
│  1. Syntax check (valid regex?)                             │
│  2. Dangerous construct detection                           │
│  3. Complexity scoring                                      │
│  4. Threshold check                                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Dangerous Constructs

| Pattern | Risk | Example |
|---------|------|---------|
| `(a+)+` | Exponential backtracking | `aaaa...X` |
| `(a|a)+` | Alternation explosion | Same input |
| `(.*.*)+` | Quadratic matching | Long strings |
| `\d+\d+` | Overlapping quantifiers | Numeric DoS |
| `(.+)+` | Super-linear | Many inputs |

### 3.3 Complexity Scoring

```
Complexity = Base + Σ(Construct_Weight × Count)

Base = len(pattern) / 10

Construct Weights:
  - Simple char class:     1
  - Quantifier (*, +, ?):  5
  - Alternation (|):      10
  - Group ():             15
  - Nested quantifier:   100 (REJECT)
  - Backreference:       100 (REJECT)

Threshold: 50 (configurable)
```

---

## 4. API Design

### 4.1 Data Types

```c
/* Pattern safety levels */
typedef enum {
    PATTERN_SAFE,       /* Can be loaded */
    PATTERN_COMPLEX,    /* Needs review */
    PATTERN_DANGEROUS,  /* REJECT - ReDoS risk */
    PATTERN_INVALID     /* Syntax error */
} pattern_safety_t;

/* Validation result */
typedef struct {
    pattern_safety_t safety;
    int              complexity;
    const char      *reason;
    int              position;  /* Error position if invalid */
} pattern_result_t;

/* Validator configuration */
typedef struct {
    int  max_complexity;        /* Default: 50 */
    int  max_length;            /* Default: 1024 */
    bool allow_backrefs;        /* Default: false */
    bool allow_lookahead;       /* Default: false */
    int  timeout_ms;            /* Kernel timeout, default: 10 */
} pattern_config_t;
```

### 4.2 Functions

| Function | Description |
|----------|-------------|
| `pattern_config_init(config)` | Set defaults |
| `pattern_validate(pattern, config, result)` | Validate pattern |
| `pattern_is_safe(pattern)` | Quick safe check |
| `pattern_complexity(pattern)` | Get complexity score |
| `pattern_compile(pattern, compiled)` | Compile if safe |
| `pattern_match_timeout(compiled, input, timeout)` | Match with timeout |

---

## 5. Implementation Plan

### Phase 1: Validator (1 day)
- [x] pattern_safety.h header
- [ ] pattern_validator.c implementation
- [ ] Dangerous construct detection
- [ ] Complexity scoring

### Phase 2: Kernel Integration (1 day)
- [ ] Timeout mechanism for BSD
- [ ] Pattern reload with validation
- [ ] Atomic pattern swap

### Phase 3: Testing (0.5 day)
- [ ] Unit tests with ReDoS patterns
- [ ] Performance benchmarks
- [ ] Integration with Hive

---

## 6. Test Plan

### 6.1 Unit Tests

| Test | Input | Expected |
|------|-------|----------|
| `test_simple_safe` | `^hello$` | SAFE |
| `test_char_class` | `[a-z]+` | SAFE |
| `test_nested_quant` | `(a+)+` | DANGEROUS |
| `test_alternation_exp` | `(a|a)+` | DANGEROUS |
| `test_overlapping` | `\d+\d+` | COMPLEX |
| `test_super_linear` | `(.+)+` | DANGEROUS |
| `test_backref` | `(a)\1` | DANGEROUS |
| `test_complexity_threshold` | Long pattern | COMPLEX |
| `test_invalid_syntax` | `[a-` | INVALID |

### 6.2 ReDoS Attack Patterns

```
# Known ReDoS patterns (must be rejected)
(a+)+$
(a|aa)+$
(.*a){x} for x > 10
([a-zA-Z]+)*$
^(a+)+$
```

### 6.3 Performance Tests

| Test | Target |
|------|--------|
| Validate 1000 patterns | < 1 second |
| Match with 10ms timeout | Always returns |
| Memory per compiled pattern | < 4KB |

---

## 7. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| False positives on legit patterns | Usability | Whitelist mechanism |
| New ReDoS techniques | Security | Configurable threshold |
| Kernel timeout overhead | Performance | Lazy timeout setup |

---

## 8. Acceptance Criteria

- [ ] All nested quantifier patterns rejected
- [ ] Complexity > 50 patterns marked COMPLEX
- [ ] Kernel matching always completes in < timeout
- [ ] All unit tests pass
- [ ] No regression in pattern matching speed

---

*Document ready for implementation*
