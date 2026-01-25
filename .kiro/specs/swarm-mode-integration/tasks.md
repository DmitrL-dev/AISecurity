# Swarm Mode Integration — Tasks

## Phase 1: Core Components 🔧 ✅

### 1.1 ModelRouter
- [x] Create `src/agents/ModelRouter.ts`
- [x] Implement model matrix (haiku/sonnet/opus per agent type)
- [x] Add complexity override (high → opus)
- [x] Unit tests: `swarm-mode.test.ts`

### 1.2 WorkerPreamble  
- [x] Create `src/agents/WorkerPreamble.ts`
- [x] Implement preamble template generator
- [x] Unit tests: `swarm-mode.test.ts`

### 1.3 SwarmSpawner
- [x] Create `src/agents/SwarmSpawner.ts`
- [x] Implement `spawnParallel()` — fan-out pattern
- [x] Implement `spawnPipeline()` — dependency resolution
- [x] Unit tests: `swarm-mode.test.ts`


---

## Phase 2: Integration 🔗 ✅

### 2.1 ClaudeAPIClient Update
- [x] Add `model` parameter to `ChatOptions`
- [x] Add opus to ClaudeModel type
- [x] Add SWARM_MODEL_MAP for aliases
- [x] Implement `chat()` method
- [x] Implement `resolveModel()` — alias → full model ID

### 2.2 AgentOrchestrator Update
- [ ] Inject ModelRouter, SwarmSpawner
- [ ] Add `executeSwarm()` method
- [ ] Add `estimateSwarmSize()` heuristic
- [ ] Update existing runPipeline to use swarm


---

## Phase 3: RLM & Memory 🧠

### 3.1 RLM Facts
- [ ] Add Iron Law L0 fact
- [ ] Add model selection matrix L1 fact
- [ ] Verify `rlm_route_context("swarm")` returns patterns

### 3.2 Steering Update
- [ ] Update `.kiro/steering/tech.md` with swarm architecture
- [ ] Add orchestrator guidelines to steering

---

## Phase 4: Verification ✅

### 4.1 Unit Tests
- [ ] All new components have tests
- [ ] Coverage > 80%

### 4.2 Integration Test
- [ ] Test parallel spawn (3+ workers)
- [ ] Test pipeline with dependencies
- [ ] Test model routing per agent type

### 4.3 E2E Demo
- [ ] Simple task → 1-2 agents
- [ ] Feature task → 4+ swarm
- [ ] Security audit → haiku swarm + opus synthesis

---

## Acceptance Criteria Summary

| Requirement | Test |
|-------------|------|
| FR-1 Iron Law | Orchestrator never calls Write/Edit/Bash |
| FR-2 Model Selection | SecurityScanner uses opus |
| FR-3 Worker Preamble | All spawned agents get preamble |
| FR-4 Parallel Spawn | Promise.all for independent tasks |
| FR-5 Swarm Scaling | estimateSwarmSize returns appropriate count |
| NFR-1 RLM | route_context("swarm") returns L0 facts |
