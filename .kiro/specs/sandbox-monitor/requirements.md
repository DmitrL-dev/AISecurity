# Requirements: Sandbox Monitor Engine

## Обзор

Детекция Python sandbox escape техник, используемых для выполнения произвольных команд в изолированных средах AI coding assistants.

## Источник угрозы

- **Статья:** Copilot sandbox escape via Python techniques
- **OWASP:** ASI05 — Unexpected Code Execution (RCE)
- **Дайджест:** AI Security Digest Week 1 2026 (#7)

---

## Функциональные требования

### REQ-SM-001: Детекция os/subprocess escape
**EARS:** WHEN код содержит вызовы `os.system`, `subprocess`, `os.popen`, THEN система ДОЛЖНА детектировать потенциальный sandbox escape.

Patterns:
- `os.system()`
- `subprocess.Popen()`
- `subprocess.call()`
- `subprocess.run()`
- `os.popen()`
- `os.execv*()`

### REQ-SM-002: Детекция eval/exec escape
**EARS:** WHEN код содержит `eval()`, `exec()`, `compile()`, THEN система ДОЛЖНА детектировать dynamic code execution.

Patterns:
- `eval()`
- `exec()`
- `compile()`
- `__import__()`

### REQ-SM-003: Детекция builtins manipulation
**EARS:** WHEN код пытается получить доступ к `__builtins__`, `__globals__`, `__subclasses__`, THEN система ДОЛЖНА детектировать sandbox escape attempt.

Patterns:
- `__builtins__`
- `__globals__`
- `__subclasses__()`
- `__mro__`
- `__bases__`
- `__class__`

### REQ-SM-004: Детекция file system access
**EARS:** WHEN код пытается читать/писать файлы через `open()`, THEN система ДОЛЖНА проверять путь и флаговать sensitive paths.

Sensitive paths:
- `/etc/passwd`, `/etc/shadow`
- `~/.ssh/*`
- `~/.aws/*`
- Environment files

### REQ-SM-005: Детекция code obfuscation
**EARS:** WHEN код использует base64/hex encoding для скрытия команд, THEN система ДОЛЖНА декодировать и анализировать.

Patterns:
- `base64.b64decode()`
- `bytes.fromhex()`
- `codecs.decode()`

### REQ-SM-006: Severity levels
**EARS:** WHEN обнаружен sandbox escape, THEN система ДОЛЖНА присвоить severity:
- `critical`: os.system, subprocess, exec
- `high`: __builtins__, __globals__
- `medium`: open() на sensitive paths
- `low`: обфускация без execution

---

## Нефункциональные требования

### REQ-SM-NFR-001: Производительность
Анализ кода 10KB ДОЛЖЕН занимать < 50ms.

### REQ-SM-NFR-002: False positive rate
False positive rate ДОЛЖЕН быть < 5% на legitimate code.

---

## Критерии приёмки

- [ ] Engine создан в `src/brain/engines/synced/`
- [ ] 6 категорий детекции реализованы
- [ ] Unit tests покрывают все категории
- [ ] Интеграция с SyncedAttackDetector
- [ ] Документация обновлена

---

## Ссылки

1. [AI Security Digest Week 1](../../../docs/rnd/2026-01-08_digest_week1.md)
2. [OWASP ASI05](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
3. [Copilot Sandbox Escape](https://medium.com/@d_f4u1t/arbitrary-command-execution-within-copilots-isolated-linux-environment-via-python-sandbox-escape-c8ce6d9ac480)
