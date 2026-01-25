# Swarm Mode Integration — Design

## Архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentOrchestrator                        │
│                    (The Conductor)                          │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ TaskCreate  │  │ TaskList    │  │ ModelRouter │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                          │                                  │
│                          ▼                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │              SwarmSpawner                             │  │
│  │   spawnParallel() | spawnPipeline() | spawnMapReduce │  │
│  └──────────────────────────────────────────────────────┘  │
│                          │                                  │
│            ┌─────────────┼─────────────┐                   │
│            ▼             ▼             ▼                    │
│      ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│      │ Worker 1 │  │ Worker 2 │  │ Worker N │              │
│      │ (haiku)  │  │ (sonnet) │  │ (opus)   │              │
│      └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────────┘
```

---

## Компоненты

### 1. ModelRouter

**Файл:** `src/agents/ModelRouter.ts`

```typescript
export class ModelRouter {
    private readonly modelMatrix: Record<AgentType, ClaudeModel> = {
        'researcher': 'haiku',
        'planner': 'sonnet',
        'tester': 'sonnet',
        'coder': 'sonnet',
        'security': 'opus',
        'reviewer': 'opus',
        'fixer': 'sonnet',
        'integrator': 'sonnet'
    };

    getModel(agentType: AgentType, taskComplexity?: 'low' | 'medium' | 'high'): ClaudeModel {
        // Override to opus for high complexity
        if (taskComplexity === 'high') return 'opus';
        return this.modelMatrix[agentType];
    }
}
```

---

### 2. WorkerPreamble

**Файл:** `src/agents/WorkerPreamble.ts`

```typescript
export class WorkerPreamble {
    static generate(taskDescription: string): string {
        return `CONTEXT: You are a WORKER agent, not an orchestrator.

RULES:
- Complete ONLY the task described below
- Use tools directly (Read, Write, Edit, Bash, etc.)
- Do NOT spawn sub-agents
- Do NOT call TaskCreate or TaskUpdate
- Report your results with absolute file paths

TASK:
${taskDescription}`;
    }
}
```

---

### 3. SwarmSpawner

**Файл:** `src/agents/SwarmSpawner.ts`

```typescript
export interface SwarmTask {
    id: string;
    agentType: AgentType;
    description: string;
    blockedBy?: string[];  // dependency tracking
}

export class SwarmSpawner {
    constructor(
        private orchestrator: AgentOrchestrator,
        private modelRouter: ModelRouter,
        private claude: ClaudeAPIClient
    ) {}

    // Fan-out: parallel independent tasks
    async spawnParallel(tasks: SwarmTask[]): Promise<Map<string, AgentResult>> {
        const promises = tasks
            .filter(t => !t.blockedBy?.length)
            .map(t => this.spawnWorker(t));
        
        const results = await Promise.all(promises);
        return new Map(results.map((r, i) => [tasks[i].id, r]));
    }

    // Pipeline: sequential with dependencies
    async spawnPipeline(tasks: SwarmTask[]): Promise<Map<string, AgentResult>> {
        const results = new Map<string, AgentResult>();
        const pending = [...tasks];
        
        while (pending.length > 0) {
            const ready = pending.filter(t => 
                !t.blockedBy?.some(dep => !results.has(dep))
            );
            
            if (ready.length === 0) throw new Error('Circular dependency');
            
            const batchResults = await this.spawnParallel(ready);
            batchResults.forEach((v, k) => results.set(k, v));
            
            ready.forEach(t => pending.splice(pending.indexOf(t), 1));
        }
        
        return results;
    }

    private async spawnWorker(task: SwarmTask): Promise<AgentResult> {
        const model = this.modelRouter.getModel(task.agentType);
        const prompt = WorkerPreamble.generate(task.description);
        
        return await this.claude.chat(prompt, { model });
    }
}
```

---

### 4. AgentOrchestrator Updates

**Файл:** `src/agents/AgentOrchestrator.ts` (модификация)

```typescript
// Добавить в конструктор
private swarmSpawner: SwarmSpawner;
private modelRouter: ModelRouter;

// Новый метод
async executeSwarm(globalTask: string): Promise<OrchestratorResult> {
    // Phase 1: Decompose
    const tasks = await this.decompose(globalTask);
    
    // Phase 2: Set dependencies
    this.setDependencies(tasks);
    
    // Phase 3: Spawn with appropriate models
    const results = await this.swarmSpawner.spawnPipeline(tasks);
    
    // Phase 4: Synthesize
    return this.synthesize(results);
}

// Scaling heuristic
estimateSwarmSize(task: string): number {
    if (task.includes('security') || task.includes('audit')) return 10;
    if (task.includes('feature') || task.includes('implement')) return 4;
    if (task.includes('fix') || task.includes('bug')) return 2;
    return 2; // default
}
```

---

## Data Flow

```
1. User Request
        │
        ▼
2. Orchestrator.decompose() → SwarmTask[]
        │
        ▼
3. ModelRouter.getModel() → claude model per task
        │
        ▼
4. SwarmSpawner.spawnPipeline() 
        │
        ├─── ready tasks → Promise.all (parallel)
        │         │
        │         ▼
        │    ClaudeAPI.chat(model, WorkerPreamble)
        │         │
        │         ▼
        │    Worker executes (Read/Write/Edit/Bash)
        │         │
        │         ▼
        │    Result collected
        │
        ▼
5. Orchestrator.synthesize() → final answer
```

---

## Изменения в ClaudeAPIClient

```typescript
interface ChatOptions {
    model?: 'haiku' | 'sonnet' | 'opus';  // NEW
    maxTokens?: number;
    temperature?: number;
}

async chat(prompt: string, options: ChatOptions = {}): Promise<string> {
    const model = options.model || 'sonnet';
    const modelId = this.getModelId(model);  // claude-3-haiku, etc.
    // ...
}
```

---

## Зависимости

```
AgentOrchestrator
    ├── ModelRouter (new)
    ├── WorkerPreamble (new)
    ├── SwarmSpawner (new)
    └── ClaudeAPIClient (updated)
```

---

## Миграция

1. Создать `ModelRouter.ts`, `WorkerPreamble.ts`, `SwarmSpawner.ts`
2. Обновить `ClaudeAPIClient.ts` — добавить model parameter
3. Обновить `AgentOrchestrator.ts` — использовать SwarmSpawner
4. Добавить unit tests для каждого компонента
5. Update RLM с swarm L0 facts
