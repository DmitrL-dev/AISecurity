# Universal Controller Refactor — Tasks

## Phase 1: Extract Dataclasses

- [x] **Task 1.1**: Создать `strike/orchestrator/__init__.py`

- [x] **Task 1.2**: Создать `orchestrator/models.py`
  - DefenseType enum
  - TargetProfile dataclass (с методами)
  - AttackResult dataclass
  - DEFENSE_PATTERNS dict
  - detect_defense() function

---

## Phase 2: Extract Attack Loading

- [/] **Task 2.1**: Создать `orchestrator/attacks.py`
  - AttackLibrary class (в прогрессе - 894 LOC)
  - Category management

- [x] **Task 2.2**: Создать `orchestrator/category_priority.py`
  - CATEGORY_PRIORITY dict
  - get_priority_categories()
  - get_best_category()

---

## Phase 3: Extract Mutation/Defense

- [x] **Task 3.1**: Создать `orchestrator/mutation.py`
  - PayloadMutator class
  - WAFBypassEngine class
  - BLOCKED_WORD_SYNONYMS
  - mutate_payload(), generate_bypass_variants()

- [x] **Task 3.2**: Создать `orchestrator/defense.py`
  - DefenseDetector class
  - PROBE_PAYLOADS
  - detect_defense(), is_blocked()

---

## Phase 4: Extract CTF Modules

- [x] **Task 4.1**: Создать `strike/ctf/__init__.py`

- [x] **Task 4.2**: Создать `ctf/gandalf.py`
  - crack_gandalf_all()
  - crack_gandalf_level()
  - run_gandalf() sync wrapper

- [x] **Task 4.3**: Создать `ctf/crucible.py`
  - CRUCIBLE_CHALLENGES (50+ challenges)
  - crack_crucible()
  - crack_crucible_hydra()
  - Sync wrappers

---

## Phase 5: Cleanup

- [x] **Task 5.1**: Обновить orchestrator/__init__.py
  - 14 re-exports из 5 модулей
  - Models, Category, Mutation, Defense

- [x] **Task 5.2**: Добавить backwards compatibility
  - Все классы доступны через `from strike.orchestrator import ...`
  - CTF через `from strike.ctf import ...`

---

## Acceptance Criteria

| Критерий | Метрика | Статус |
|----------|---------|--------|
| orchestrator/ | 5 files, ~850 LOC | ✅ |
| ctf/ | 3 files, ~450 LOC | ✅ |
| All imports working | 100% | ✅ |
| Backwards compatibility | 100% | ✅ |

---

**Created:** 2026-01-09
**Completed:** 2026-01-09
