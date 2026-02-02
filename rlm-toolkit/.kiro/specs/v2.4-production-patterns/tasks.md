# RLM v2.4 Production Patterns - Tasks

## Task Breakdown

### Phase 1: Core Autonomy & Resilience (P0)

#### Task 1.1: AutonomyLevel Enum (2h)

**Files:**
- `[MODIFY] rlm_toolkit/core/config.py` — добавить enum и параметр
- `[NEW] tests/test_autonomy.py` — unit tests

**Implementation:**
```python
class AutonomyLevel(IntEnum):
    HUMAN_ASSISTED = 1
    HUMAN_SUPERVISED = 2
    CONDITIONAL = 3
    HIGH_AUTONOMY = 4
    FULL_AUTONOMY = 5

@dataclass
class RLMConfig:
    autonomy_level: AutonomyLevel = AutonomyLevel.HUMAN_SUPERVISED
```

**Acceptance:**
- [ ] Enum создан
- [ ] RLMConfig принимает параметр
- [ ] Tests pass

---

#### Task 1.2: CircuitBreaker Class (4h)

**Files:**
- `[NEW] rlm_toolkit/providers/resilience.py`
- `[NEW] tests/test_circuit_breaker.py`

**Implementation:**
```python
class CircuitBreaker:
    def __init__(self, failure_threshold=5, reset_timeout=60):
        self.failures = 0
        self.state = CircuitState.CLOSED
        self.last_failure_time = None
    
    def call(self, func, *args, **kwargs):
        if self.state == CircuitState.OPEN:
            if self._should_try_half_open():
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitOpenError()
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise
```

**Acceptance:**
- [ ] State machine работает
- [ ] Raises CircuitOpenError when open
- [ ] Recovery to CLOSED после success в HALF_OPEN

---

#### Task 1.3: Provider Integration (2h)

**Files:**
- `[MODIFY] rlm_toolkit/providers/base.py`
- `[MODIFY] rlm_toolkit/providers/openai.py` (и другие)

**Acceptance:**
- [ ] BaseProvider использует CircuitBreaker
- [ ] Configurable через RLMConfig

---

### Phase 2: Middleware System (P1)

#### Task 2.1: Middleware Base (2h)

**Files:**
- `[NEW] rlm_toolkit/middleware/__init__.py`
- `[NEW] rlm_toolkit/middleware/base.py`

---

#### Task 2.2: MiddlewareChain (3h)

**Files:**
- `[NEW] rlm_toolkit/middleware/chain.py`

---

#### Task 2.3: Built-in Middlewares (4h)

**Files:**
- `[NEW] rlm_toolkit/middleware/builtin/logging.py`
- `[NEW] rlm_toolkit/middleware/builtin/metrics.py`
- `[NEW] rlm_toolkit/middleware/builtin/auth.py`
- `[NEW] rlm_toolkit/middleware/builtin/rate_limit.py`
- `[NEW] rlm_toolkit/middleware/builtin/error_handling.py`

---

### Phase 3: Reflection & Planning (P1)

#### Task 3.1: ReflectionCallback (4h)

**Files:**
- `[NEW] rlm_toolkit/callbacks/reflection.py`

---

#### Task 3.2: TaskPlanner (8h)

**Files:**
- `[NEW] rlm_toolkit/planning/__init__.py`
- `[NEW] rlm_toolkit/planning/planner.py`
- `[NEW] rlm_toolkit/planning/subtask.py`

---

#### Task 3.3: ExecutionDAG (6h)

**Files:**
- `[NEW] rlm_toolkit/planning/dag.py`
- `[NEW] rlm_toolkit/planning/executor.py`

---

## Verification Plan

### Automated Tests

```bash
# Full test suite
pytest tests/ -v

# P0 features
pytest tests/test_autonomy.py tests/test_circuit_breaker.py -v

# P1 features
pytest tests/test_middleware.py tests/test_planning.py -v
```

### Manual Verification

1. **CircuitBreaker:** Disable LLM API, verify circuit opens after N failures
2. **Middleware:** Check logs show correlation IDs
3. **TaskPlanner:** Complex goal → verify parallel execution

---

## Progress Tracking

| Task | Status | Notes |
|------|--------|-------|
| 1.1 AutonomyLevel | [ ] | |
| 1.2 CircuitBreaker | [ ] | |
| 1.3 Provider Integration | [ ] | |
| 2.1 Middleware Base | [ ] | |
| 2.2 MiddlewareChain | [ ] | |
| 2.3 Built-in Middlewares | [ ] | |
| 3.1 ReflectionCallback | [ ] | |
| 3.2 TaskPlanner | [ ] | |
| 3.3 ExecutionDAG | [ ] | |

---

*Created: 2026-02-02*
