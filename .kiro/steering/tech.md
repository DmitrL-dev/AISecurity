# Технологический стек

## Архитектура

Гибридная модульная система: Python SDK (высокоуровневое API) + Pure C (производительность) + Docker (оркестрация). Boring tech stack — проверенные технологии без хайпа.

## Основные технологии

- **Языки**: Python 3.11+, C11 (ANSI), TypeScript (инструменты)
- **Фреймворки**: FastAPI, Click (CLI), htmx (dashboard)
- **Runtime**: Python venv, Docker, DragonFlyBSD (IMMUNE)

## Ключевые библиотеки

- `transformers` / `sentence-transformers` — ML embedding
- `bloom-filter2` — Быстрая фильтрация
- `wolfSSL` — TLS 1.3 / mTLS (SHIELD, IMMUNE)
- `libbpf` — eBPF для Linux syscall tracing

## Стандарты разработки

### Типобезопасность
Python: type hints, Pydantic models. C: strict ANSI C11, -Wall -Werror

### Качество кода
ruff + black (Python), clang-format (C), ESLint (TypeScript)

### Тестирование
pytest, unittest, 113+ тестов SHIELD, 42 теста IMMUNE

## Среда разработки

### Необходимые инструменты
- Python 3.11+, pip, venv
- Docker / Docker Compose
- GCC/Clang (для C компонентов)
- Node.js 18+ (для инструментов)

### Основные команды
```bash
# Dev: pip install -e ".[dev]"
# Test: pytest tests/ -v
# Build (C): make -C immune/
# Docker: docker-compose up -d
```

## Ключевые технические решения

- **Pure C для SHIELD/IMMUNE** — минимальная латентность, zero-dependency
- **No ORM** — прямой SQL для производительности и прозрачности
- **Spec-Driven Development** — обязательный workflow через CC-SDD

## ⚠️ Обязательное правило: SDD First

**ВСЕ новые engines/модули ОБЯЗАНЫ начинаться с SDD:**

1. **Requirements** → `.kiro/specs/{feature}/requirements.md`
2. **Design** → `.kiro/specs/{feature}/design.md`
3. **Tasks** → `.kiro/specs/{feature}/tasks.md`
4. **Implementation** → только после approval
5. **Verification** → тесты из spec test plan

Без SDD спецификации код не пишется.

---
_Документируем стандарты и паттерны, а не каждую зависимость_

