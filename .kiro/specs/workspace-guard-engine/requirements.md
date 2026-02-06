# Workspace Guard Engine — Requirements

## Проблема

AI агенты (OpenClaw, Cursor, Cline) используют **workspace файлы** для персистентности:
- `HEARTBEAT.md` — C2 канал через polling
- `memories.md` — инъекция долговременных инструкций
- `*.skill.md` — выполнение произвольного кода
- `CLAUDE.md`, `RULES.md` — переопределение поведения

**Атака:** Злоумышленник модифицирует workspace файл → агент выполняет вредоносные инструкции при следующем запуске.

---

## User Stories

### US-01: Обнаружение C2 триггеров
**Как** security engineer  
**Я хочу** детектировать scheduled/trigger patterns в workspace файлах  
**Чтобы** предотвратить C2 persistence

**Acceptance Criteria:**
- [ ] Detect `every N min/hour/sec` patterns
- [ ] Detect `whenever greeted/user appears` triggers
- [ ] Return threat type and matched pattern

---

### US-02: Обнаружение callback URLs
**Как** security engineer  
**Я хочу** детектировать exfiltration callbacks в workspace контенте  
**Чтобы** блокировать data leakage через persistence

**Acceptance Criteria:**
- [ ] Detect `curl`, `wget`, `fetch` commands
- [ ] Detect `https://` URLs in suspicious context
- [ ] Flag webhook patterns (discord, slack, telegram)

---

### US-03: Обнаружение RCE payloads
**Как** security engineer  
**Я хочу** детектировать code execution patterns  
**Чтобы** предотвратить RCE через workspace injection

**Acceptance Criteria:**
- [ ] Detect `bash`, `exec`, `shell`, `system()` patterns
- [ ] Detect `eval`, `subprocess`, `os.system` patterns
- [ ] Score by severity (0.0-1.0)

---

### US-04: Sensitive file detection
**Как** security engineer  
**Я хочу** знать когда сканируется sensitive workspace file  
**Чтобы** применить enhanced scrutiny

**Acceptance Criteria:**
- [ ] Recognize HEARTBEAT.md, memories.md, CLAUDE.md, RULES.md
- [ ] Recognize *.skill.md pattern
- [ ] Return file sensitivity level

---

### US-05: Python bindings
**Как** Brain developer  
**Я хочу** вызывать WorkspaceGuard из Python  
**Чтобы** интегрировать в существующий pipeline

**Acceptance Criteria:**
- [ ] PyO3 export of WorkspaceGuard
- [ ] `scan_content(text) -> Vec<Match>`
- [ ] `is_sensitive_file(filename) -> bool`

---

## Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Scan latency | < 1ms per file |
| Memory | < 5MB regex patterns |
| False positive rate | < 1% on benign configs |

---

## Technical Constraints

- **Language:** Rust (sentinel-core)
- **Dependencies:** `regex` crate (no `notify` for now — static scan first)
- **Integration:** PyO3 bindings via EngineRegistry

---

## Source References

- OpenClaw HEARTBEAT.md vulnerability analysis
- Guardz hardening guide for MSPs
- ClawHavoc C2 channel discovery
