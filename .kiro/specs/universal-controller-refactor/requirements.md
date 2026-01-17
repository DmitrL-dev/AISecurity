# Universal Controller Refactor — Requirements

## FR-1: Модульная структура
**Как** разработчик  
**Хочу** чтобы UniversalController был разбит на логические модули  
**Чтобы** упростить поддержку, тестирование и расширение

### Acceptance Criteria
- [ ] AC-1.1: universal_controller.py < 25KB (с 86KB)
- [ ] AC-1.2: Каждый новый модуль < 30KB
- [ ] AC-1.3: Все импорты совместимы
- [ ] AC-1.4: Тесты проходят

---

## FR-2: Attack Loading extraction
**Как** разработчик атак  
**Хочу** отдельный модуль для загрузки атак  
**Чтобы** управлять атаками независимо

### Acceptance Criteria
- [ ] AC-2.1: Создан `orchestrator/attacks.py` — attack loading
- [ ] AC-2.2: _load_attacks() перенесён (900 LOC)

---

## FR-3: Payload Mutation extraction
**Как** security researcher  
**Хочу** отдельные модули для мутации payloads  
**Чтобы** легко добавлять новые техники

### Acceptance Criteria
- [ ] AC-3.1: Создан `orchestrator/mutation.py` — _mutate(), _apply_bypass()
- [ ] AC-3.2: Создан `orchestrator/defense.py` — defense detection

---

## FR-4: CTF Modules extraction
**Как** CTF player  
**Хочу** отдельные модули для CTF targets  
**Чтобы** легко добавлять новые CTF

### Acceptance Criteria
- [ ] AC-4.1: Создан `ctf/gandalf.py` — crack_gandalf_all()
- [ ] AC-4.2: Создан `ctf/crucible.py` — crack_crucible(), crack_crucible_hydra()

---

## NFR-1: Обратная совместимость
- Все существующие импорты работают

---

**Created:** 2026-01-09
