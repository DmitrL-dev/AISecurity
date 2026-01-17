# Strike Console Refactor — Tasks

## Phase 1: Extract State Management

- [x] **Task 1.1**: Создать `strike/dashboard/state/__init__.py`

- [x] **Task 1.2**: Создать `strike/dashboard/state/logger.py`
  - Перенести класс AttackLogger (строки 153-212)
  - Добавить type hints
  - Добавить docstrings

- [x] **Task 1.3**: Создать `strike/dashboard/state/cache.py`
  - Перенести класс ReconCache (строки 223-258)
  - Добавить type hints

- [x] **Task 1.4**: Создать `strike/dashboard/state/manager.py`
  - Перенести глобальные переменные
  - attack_log, attack_running, attack_results
  - Инкапсулировать в класс StateManager

- [x] **Task 1.5**: Создать `strike/dashboard/__init__.py`
  - Превращает dashboard в Python package
  - Re-export ключевые компоненты

---

## Phase 2: Extract Attack Handlers

- [x] **Task 2.1**: Создать `strike/dashboard/handlers/__init__.py`

- [x] **Task 2.2**: Создать `handlers/attack_config.py`
  - AttackConfig dataclass
  - AttackMode enum
  - from_request() factory
  - validate() method

- [x] **Task 2.3**: Создать `handlers/session_handler.py`
  - AttackSession dataclass
  - SessionHandler class
  - start/stop/status methods

- [x] **Task 2.4**: Создать `handlers/hydra_handler.py`
  - HydraConfig dataclass
  - HydraHandler class  
  - AI Detection
  - LLM setup
  - Proxy support

---

## Phase 3: Extract UI Components

- [x] **Task 3.1**: Создать `strike/dashboard/ui/__init__.py`

- [x] **Task 3.2**: Создать `ui/components.py`
  - format_log_entry()
  - format_finding()
  - format_stats()
  - format_progress_bar()
  - format_attack_card()

- [x] **Task 3.3**: Создать `ui/themes.py`
  - Theme dataclass
  - THEMES dict (dark, hacker, cyberpunk)
  - get_theme()
  - LOG_CLASSES, SEVERITY_CLASSES

---

## Phase 4: Extract Reports

- [x] **Task 4.1**: Создать `strike/dashboard/reports/__init__.py`

- [x] **Task 4.2**: Создать `reports/generator.py`
  - ReportGenerator class
  - generate() method
  - generate_from_log() method
  - list_reports() method

- [x] **Task 4.3**: Создать `reports/templates.py`
  - report_template() — HTML
  - finding_template() — HTML finding
  - markdown_template() — Markdown

---

## Phase 5: Cleanup & Validation

- [x] **Task 5.1**: Создать dashboard/__init__.py
  - Re-export всех компонентов (22 экспорта)
  - Backwards compatibility

- [x] **Task 5.2**: Добавить backwards compatibility exports
  - AttackLogger, ReconCache, StateManager
  - AttackConfig, HydraHandler, SessionHandler
  - Theme, THEMES, format_* functions
  - ReportGenerator, generate_report

- [ ] **Task 5.3**: Unit тесты (optional)
  - test_state_manager.py
  - test_attack_handler.py
  - test_report_generator.py

- [ ] **Task 5.4**: Integration test (optional)
  - Full attack flow test

---

## Acceptance Criteria

| Критерий | Метрика |
|----------|---------|
| strike_console.py size | < 30KB (was 174KB) |
| Each module size | < 40KB |
| All endpoints working | 100% |
| Test coverage | > 60% new code |
| Zero breaking changes | Existing imports work |

---

**Created:** 2026-01-09
