# Strike Console Refactor — Requirements

## FR-1: Модульная структура
**Как** разработчик  
**Хочу** чтобы strike_console.py был разбит на логические модули  
**Чтобы** упростить поддержку, тестирование и навигацию по коду

### Acceptance Criteria
- [ ] AC-1.1: strike_console.py < 30KB (с 174KB)
- [ ] AC-1.2: Каждый новый модуль < 40KB
- [ ] AC-1.3: Все существующие Flask routes работают
- [ ] AC-1.4: Все импорты корректны

---

## FR-2: UI Components extraction
**Как** frontend разработчик  
**Хочу** иметь отдельный модуль для UI компонентов  
**Чтобы** легко изменять интерфейс независимо от логики

### Acceptance Criteria
- [ ] AC-2.1: Создан `ui/components.py` — HTML generators, formatters
- [ ] AC-2.2: Создан `ui/themes.py` — цветовые схемы, стили
- [ ] AC-2.3: Все UI элементы импортируются из ui/

---

## FR-3: Attack Handlers extraction
**Как** pentest разработчик  
**Хочу** иметь отдельные модули для обработчиков атак  
**Чтобы** добавлять новые типы атак независимо

### Acceptance Criteria
- [ ] AC-3.1: Создан `handlers/attack_handler.py` — основная логика атак
- [ ] AC-3.2: Создан `handlers/hydra_handler.py` — HYDRA multi-head атаки
- [ ] AC-3.3: Создан `handlers/session_handler.py` — управление сессиями

---

## FR-4: State and Cache extraction
**Как** backend разработчик  
**Хочу** централизованное управление состоянием  
**Чтобы** избежать глобальных переменных

### Acceptance Criteria
- [ ] AC-4.1: Создан `state/manager.py` — глобальное состояние
- [ ] AC-4.2: Создан `state/cache.py` — ReconCache перенесён
- [ ] AC-4.3: Создан `state/logger.py` — AttackLogger перенесён

---

## FR-5: Report Generation extraction
**Как** пользователь  
**Хочу** генерировать профессиональные отчёты  
**Чтобы** предоставлять клиентам результаты

### Acceptance Criteria
- [ ] AC-5.1: Создан `reports/generator.py` — генерация отчётов
- [ ] AC-5.2: Создан `reports/templates.py` — шаблоны HTML/PDF
- [ ] AC-5.3: /generate-report endpoint работает

---

## NFR-1: Обратная совместимость
- Все существующие API endpoints работают без изменений
- Все CLI вызовы работают без изменений
- Docker образ собирается без изменений

## NFR-2: Тестируемость
- Каждый новый модуль имеет unit тесты
- pytest coverage > 60% для новых модулей

---

**Created:** 2026-01-09
