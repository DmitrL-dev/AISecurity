# Swarm Mode Integration — Requirements

## Обзор
Интеграция паттернов Claude Swarm Mode в SENTINEL AgentOrchestrator для параллельного выполнения задач с динамическим выбором моделей.

## Источник паттернов
`c:\AISecurity\research\claude-sneakpeek` — исследование swarm архитектуры.

---

## FR-1: Iron Law — Orchestrator vs Worker Separation

### Описание
Orchestrator ТОЛЬКО координирует, НИКОГДА не выполняет непосредственно. Workers получают чёткий preamble с правилами.

### Acceptance Criteria
- [ ] Orchestrator не вызывает execution tools напрямую (Write, Edit, Bash)
- [ ] Workers получают стандартный preamble: "Do NOT spawn sub-agents"
- [ ] Все spawn вызовы с `run_in_background=True`

---

## FR-2: Dynamic Model Selection

### Описание
Разные типы агентов используют разные модели Claude в зависимости от сложности задачи.

### Model Matrix
| Agent Type | Model | Rationale |
|------------|-------|-----------|
| Researcher | haiku | Fast parallel exploration |
| Planner | sonnet | Decomposition + structure |
| Tester | sonnet | Test generation |
| Coder | sonnet | Implementation |
| SecurityScanner | **opus** | Critical thinking, vulnerability analysis |
| Reviewer | opus | Deep code review |
| Fixer | sonnet | Bug fixes |
| Integrator | sonnet | Synthesis |

### Acceptance Criteria
- [ ] `AgentOrchestrator.getModelForAgent(agentType): string`
- [ ] `ClaudeAPIClient.chat()` принимает `model` parameter
- [ ] SecurityScanner/Reviewer используют opus model
- [ ] Haiku для parallel exploration (5-10 concurrent)

---

## FR-3: Worker Preamble Template

### Описание
Стандартный промпт для порождённых workers.

### Template
```
CONTEXT: You are a WORKER agent, not an orchestrator.

RULES:
- Complete ONLY the task described below
- Use tools directly (Read, Write, Edit, Bash, etc.)
- Do NOT spawn sub-agents
- Do NOT call TaskCreate or TaskUpdate
- Report your results with absolute file paths

TASK:
{task_description}
```

### Acceptance Criteria
- [ ] `WorkerPreamble.ts` — генерация preamble
- [ ] Все agent prompts включают preamble
- [ ] Clear boundary между orchestrator и worker

---

## FR-4: Parallel Swarm Execution

### Описание
Background spawn для всех workers с non-blocking orchestration.

### Patterns
1. **Fan-Out**: Независимые задачи параллельно
2. **Pipeline**: Зависимости через blockedBy
3. **Map-Reduce**: Collect → Process → Merge

### Acceptance Criteria
- [ ] `AgentOrchestrator.spawnParallel(agents: AgentTask[])`
- [ ] Async/await с Promise.all для fan-out
- [ ] Dependency tracking: blockedBy/blocks в checkpoints
- [ ] Non-blocking: orchestrator продолжает работу пока agents execute

---

## FR-5: Swarm Scaling

### Описание
Динамическое масштабирование количества workers.

### Rules
| Task Complexity | Agents |
|-----------------|--------|
| Simple fix | 1-2 |
| Multi-file change | 2-3 |
| Feature implementation | 4+ |
| Security audit | 5-10 haiku + 1 opus |

### Acceptance Criteria
- [ ] `estimateSwarmSize(task): number`
- [ ] Throttling для rate limits
- [ ] Resource-aware scaling

---

## NFR-1: RLM Integration

### Описание
Swarm patterns сохраняются в RLM как L0 facts.

### Acceptance Criteria
- [ ] Iron Law в L0 methodology domain
- [ ] Model selection matrix в RLM
- [ ] `rlm_route_context("swarm")` возвращает patterns

---

## Out of Scope
- UI для swarm visualization (Phase 4)
- Multi-provider support (Gemini, etc.) 
- Distributed execution across machines
