# Universal Controller Refactor — Design

## Architecture Overview

```
strike/
├── universal_controller.py  # Thin entry (~500 LOC, was 2337)
├── orchestrator/
│   ├── __init__.py
│   ├── attacks.py           # Attack loading (~900 LOC)
│   ├── mutation.py          # Payload mutation (~200 LOC)
│   ├── defense.py           # Defense detection (~100 LOC)
│   └── engine.py            # Core run() logic (~400 LOC)
└── ctf/
    ├── __init__.py
    ├── gandalf.py           # Gandalf CTF (~50 LOC)
    └── crucible.py          # Crucible CTF (~200 LOC)
```

## Current Analysis

| Компонент | Строки | Назначение |
|-----------|--------|------------|
| Dataclasses | 20-49 | DefenseType, TargetProfile, AttackResult |
| UniversalController.__init__ | 156-512 | Init + config |
| _load_attacks | 514-1408 | Attack loading (894 LOC!) |
| probe/detect | 1410-1439 | Defense detection |
| _select/_get | 1441-1500 | Category selection |
| _mutate | 1502-1579 | Mutation (77 LOC) |
| _apply_bypass | 1581-1615 | Bypass (34 LOC) |
| _ai_analyze | 1623-1632 | AI analysis |
| _hydra_attack | 1659-1682 | Hydra integration |
| run() | 1684-1967 | Main loop (283 LOC) |
| crack_gandalf_all | 1970-1994 | Gandalf CTF |
| crack_crucible | 2092-2199 | Crucible CTF |
| crack_crucible_hydra | 2202-2328 | Crucible Hydra |

## Migration Strategy

### Phase 1: Extract Dataclasses
1. Create `orchestrator/models.py`
2. Move DefenseType, TargetProfile, AttackResult
3. Keep backwards compatibility imports

### Phase 2: Extract Attack Loading
1. Create `orchestrator/attacks.py`
2. Move _load_attacks() — biggest chunk (894 LOC)
3. Create AttackLibrary class

### Phase 3: Extract Mutation/Defense
1. Create `orchestrator/mutation.py`
2. Create `orchestrator/defense.py`
3. Move related methods

### Phase 4: Extract CTF Modules
1. Create `ctf/gandalf.py`
2. Create `ctf/crucible.py`
3. Move crack_* functions

### Phase 5: Cleanup
1. Thin UniversalController
2. Add re-exports
3. Verify all imports

---

**Created:** 2026-01-09
